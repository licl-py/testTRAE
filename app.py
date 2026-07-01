import json
import os
import re
import smtplib
import threading
import time
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, render_template, request, Response, stream_with_context

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "monitor_config.json"
STATE_FILE = ROOT / "monitor_state.json"
MAIL_LOG_FILE = ROOT / "mail_log.json"
ENV_FILE = ROOT / ".env"
EXAMPLE_ENV_FILE = ROOT / "monitor_env.example"
EVENTS: List[Dict[str, Any]] = []
EVENT_LOCK = threading.Lock()
MONITOR_THREAD_STARTED = False
MONITOR_THREAD_LOCK = threading.Lock()
DEFAULT_CHECK_INTERVAL = 60
DEFAULT_EMAIL_TO = "licl45@lenovo.com"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value


def ensure_env_loaded() -> None:
    if ENV_FILE.exists():
        load_env_file(ENV_FILE)
    elif EXAMPLE_ENV_FILE.exists():
        load_env_file(EXAMPLE_ENV_FILE)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_files() -> None:
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, {"projects": []})
    if not STATE_FILE.exists():
        save_json(STATE_FILE, {"projects": {}})
    if not MAIL_LOG_FILE.exists():
        save_json(MAIL_LOG_FILE, {"logs": []})


def push_event(event_type: str, payload: Dict[str, Any]) -> None:
    with EVENT_LOCK:
        EVENTS.append({"type": event_type, "time": datetime.now(timezone.utc).isoformat(), "payload": payload})
        if len(EVENTS) > 200:
            EVENTS.pop(0)


def parse_github_repo(repo_url: str) -> Optional[tuple]:
    match = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if not match:
        return None
    return match.group(1), match.group(2)


def github_api_get(path: str, token: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    response = requests.get(f"https://api.github.com{path}", headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def get_remote_commit_sha(owner: str, repo: str, branch: str, token: Optional[str] = None) -> Optional[str]:
    payload = github_api_get(f"/repos/{owner}/{repo}/commits/{branch}", token)
    return payload.get("sha")


def compare_commits(owner: str, repo: str, base: str, head: str, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if base == head:
        return None
    return github_api_get(f"/repos/{owner}/{repo}/compare/{base}...{head}", token)


def send_email(subject: str, content: str, recipients: List[str], from_address: Optional[str] = None) -> None:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() not in ("false", "0", "no")
    use_ssl = os.environ.get("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes") or smtp_port == 465

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP_HOST, SMTP_USER, and SMTP_PASS must be configured to send email.")

    sender = from_address or os.environ.get("MONITOR_EMAIL_FROM", smtp_user)
    recipients = recipients if isinstance(recipients, list) else [recipients]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(content)

    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)
    server.quit()


def send_sms(message: str, phones: List[str]) -> None:
    gateway = os.environ.get("SMS_GATEWAY_URL")
    api_key = os.environ.get("SMS_API_KEY")
    if not gateway or not api_key or not phones:
        return
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for phone in phones:
        try:
            requests.post(gateway, json={"to": phone, "message": message}, headers=headers, timeout=15)
        except Exception:
            pass


def build_report(project: Dict[str, Any], comparison: Dict[str, Any], last_sha: str, current_sha: str) -> str:
    files = comparison.get("files", [])
    commits = comparison.get("commits", [])
    added = [f["filename"] for f in files if f.get("status") == "added"]
    modified = [f["filename"] for f in files if f.get("status") == "modified"]
    deleted = [f["filename"] for f in files if f.get("status") == "removed"]

    lines = [
        f"Project: {project.get('name')}",
        f"Repository: {project.get('repo_url')}",
        f"Branch: {project.get('branch')}",
        f"Previous commit: {last_sha}",
        f"Current commit: {current_sha}",
        "",
    ]

    if commits:
        lines.append("Commits:")
        for commit in commits:
            author = commit.get("commit", {}).get("author", {}).get("name", "unknown")
            message = commit.get("commit", {}).get("message", "").splitlines()[0]
            lines.append(f"- {commit.get('sha')[:7]} | {author} | {message}")
        lines.append("")

    if added:
        lines.append("Added files:")
        lines.extend([f"- {path}" for path in added])
        lines.append("")
    if modified:
        lines.append("Modified files:")
        lines.extend([f"- {path}" for path in modified])
        lines.append("")
    if deleted:
        lines.append("Deleted files:")
        lines.extend([f"- {path}" for path in deleted])
        lines.append("")

    lines.append("Note: deleted files are tracked and included in alerts, but they are not suggested for restoration unless required.")
    return "\n".join(lines)


def evaluate_alert(project: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
    thresholds = project.get("alert_thresholds", {})
    if metrics["new_commits"] >= thresholds.get("new_commits", 1):
        return True
    if metrics["added_files"] >= thresholds.get("added_files", 0):
        return True
    if metrics["modified_files"] >= thresholds.get("modified_files", 0):
        return True
    if metrics["deleted_files"] >= thresholds.get("deleted_files", 0):
        return True
    return False


def log_mail(recipient_list: List[str], subject: str, body: str, status: str, error: Optional[str] = None) -> None:
    log = load_json(MAIL_LOG_FILE, {"logs": []})
    log_entry = {
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "recipients": recipient_list,
        "subject": subject,
        "body": body,
        "status": status,
        "error": error,
    }
    log["logs"].insert(0, log_entry)
    save_json(MAIL_LOG_FILE, log)


def check_project(project: Dict[str, Any], project_state: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "unknown",
        "last_check": datetime.now(timezone.utc).isoformat(),
        "monitor_enabled": project.get("monitor_enabled", True),
    }

    if not project.get("monitor_enabled", True):
        result["status"] = "paused"
        return result

    repo_info = parse_github_repo(project.get("repo_url", ""))
    if not repo_info:
        result["status"] = "invalid_repo"
        result["error"] = "Unsupported repo URL"
        return result

    owner, repo = repo_info
    branch = project.get("branch", "master")
    current_sha = get_remote_commit_sha(owner, repo, branch, token=token)
    if not current_sha:
        result["status"] = "commit_not_found"
        result["error"] = "Failed to read remote commit"
        return result

    last_sha = project_state.get("last_commit")
    result["last_commit"] = current_sha
    result["new_commits"] = 0
    result["added_files"] = 0
    result["modified_files"] = 0
    result["deleted_files"] = 0
    result["files"] = {"added": [], "modified": [], "deleted": []}
    result["alert_sent"] = False

    if not last_sha:
        result["status"] = "baseline_initialized"
        return result

    if last_sha == current_sha:
        result["status"] = "no_changes"
        return result

    comparison = compare_commits(owner, repo, last_sha, current_sha, token=token)
    if not comparison:
        result["status"] = "compare_failed"
        result["error"] = "Comparison request failed"
        return result

    files = comparison.get("files", [])
    result["new_commits"] = len(comparison.get("commits", []))
    result["added_files"] = len([f for f in files if f.get("status") == "added"])
    result["modified_files"] = len([f for f in files if f.get("status") == "modified"])
    result["deleted_files"] = len([f for f in files if f.get("status") == "removed"])
    result["files"] = {
        "added": [f["filename"] for f in files if f.get("status") == "added"],
        "modified": [f["filename"] for f in files if f.get("status") == "modified"],
        "deleted": [f["filename"] for f in files if f.get("status") == "removed"],
    }
    result["status"] = "changed"

    if evaluate_alert(project, result):
        report = build_report(project, comparison, last_sha, current_sha)
        subject = f"[Monitor Alert] {project.get('name')} {branch} changed"
        recipients = project.get("email_recipients") or [os.environ.get("MONITOR_EMAIL_TO", DEFAULT_EMAIL_TO)]
        if isinstance(recipients, str):
            recipients = [recipients]
        try:
            send_email(subject, report, recipients)
            sms_recipients = project.get("sms_recipients", [])
            if sms_recipients:
                send_sms(report, sms_recipients)
            result["alert_sent"] = True
            log_mail(recipients, subject, report, "sent")
        except Exception as exc:
            result["alert_error"] = str(exc)
            log_mail(recipients, subject, report, "failed", str(exc))
    else:
        log_mail([os.environ.get("MONITOR_EMAIL_TO", DEFAULT_EMAIL_TO)], f"[Monitor Notice] {project.get('name')} {branch} check completed", "No email sent because no change was detected.", "skipped")

    return result


def start_monitor_thread() -> None:
    global MONITOR_THREAD_STARTED
    with MONITOR_THREAD_LOCK:
        if MONITOR_THREAD_STARTED:
            return
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        MONITOR_THREAD_STARTED = True


def monitor_loop() -> None:
    while True:
        ensure_files()
        config = load_json(CONFIG_FILE, {"projects": []})
        state = load_json(STATE_FILE, {"projects": {}})
        token = os.environ.get("GITHUB_TOKEN")
        now = datetime.now(timezone.utc).timestamp()
        updated = False

        for project in config.get("projects", []):
            project_id = project.get("id")
            if not project_id:
                continue
            interval = int(project.get("check_interval", DEFAULT_CHECK_INTERVAL))
            project_state = state.get("projects", {}).get(project_id, {})
            last_check = project_state.get("last_check")
            if last_check:
                elapsed = now - datetime.fromisoformat(last_check.replace("Z", "+00:00")).timestamp()
            else:
                elapsed = interval + 1
            if elapsed < interval:
                continue

            result = check_project(project, project_state, token=token)
            state.setdefault("projects", {})[project_id] = {**project_state, **result}
            save_json(STATE_FILE, state)
            push_event("project_update", {"project_id": project_id, "result": result})
            updated = True

        time.sleep(5 if not updated else 2)


@app.route("/")
def index() -> str:
    start_monitor_thread()
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


@app.route("/api/projects", methods=["GET", "POST"])
def api_projects() -> Any:
    ensure_files()
    config = load_json(CONFIG_FILE, {"projects": []})
    if request.method == "POST":
        project = request.get_json() or {}
        if not project.get("id"):
            return jsonify({"error": "Project id is required"}), 400
        project["monitor_enabled"] = project.get("monitor_enabled", True)
        project["check_interval"] = int(project.get("check_interval", DEFAULT_CHECK_INTERVAL))
        projects = [p for p in config.get("projects", []) if p.get("id") != project["id"]]
        projects.append(project)
        config["projects"] = projects
        save_json(CONFIG_FILE, config)
        push_event("config_change", {"project_id": project["id"], "action": "saved"})
        return jsonify(project), 201
    return jsonify(config.get("projects", []))


@app.route("/api/projects/<project_id>", methods=["PUT", "DELETE"])
def api_project_detail(project_id: str) -> Any:
    ensure_files()
    config = load_json(CONFIG_FILE, {"projects": []})
    projects = [p for p in config.get("projects", []) if p.get("id") != project_id]
    if request.method == "DELETE":
        config["projects"] = projects
        save_json(CONFIG_FILE, config)
        push_event("config_change", {"project_id": project_id, "action": "deleted"})
        return jsonify({"status": "deleted"})

    project = request.get_json() or {}
    project["id"] = project_id
    project["monitor_enabled"] = project.get("monitor_enabled", True)
    project["check_interval"] = int(project.get("check_interval", DEFAULT_CHECK_INTERVAL))
    projects.append(project)
    config["projects"] = projects
    save_json(CONFIG_FILE, config)
    push_event("config_change", {"project_id": project_id, "action": "updated"})
    return jsonify(project)


@app.route("/api/state", methods=["GET"])
def api_state() -> Any:
    ensure_files()
    state = load_json(STATE_FILE, {"projects": {}})
    return jsonify(state.get("projects", {}))


@app.route("/api/mail_logs", methods=["GET", "DELETE"])
def api_mail_logs() -> Any:
    ensure_files()
    mail_log = load_json(MAIL_LOG_FILE, {"logs": []})
    if request.method == "DELETE":
        save_json(MAIL_LOG_FILE, {"logs": []})
        push_event("mail_logs_cleared", {})
        return jsonify({"status": "cleared"})
    return jsonify(mail_log.get("logs", []))


@app.route("/api/mail_logs/<log_id>", methods=["DELETE"])
def api_mail_log_detail(log_id: str) -> Any:
    ensure_files()
    mail_log = load_json(MAIL_LOG_FILE, {"logs": []})
    logs = [entry for entry in mail_log.get("logs", []) if entry.get("id") != log_id]
    save_json(MAIL_LOG_FILE, {"logs": logs})
    push_event("mail_log_deleted", {"log_id": log_id})
    return jsonify({"status": "deleted"})


@app.route("/api/check/<project_id>", methods=["POST"])
def api_check_project(project_id: str) -> Any:
    ensure_files()
    config = load_json(CONFIG_FILE, {"projects": []})
    project = next((p for p in config.get("projects", []) if p.get("id") == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    state = load_json(STATE_FILE, {"projects": {}})
    project_state = state.get("projects", {}).get(project_id, {})
    result = check_project(project, project_state, token=os.environ.get("GITHUB_TOKEN"))
    state.setdefault("projects", {})[project_id] = {**project_state, **result}
    save_json(STATE_FILE, state)
    push_event("project_update", {"project_id": project_id, "result": result})
    return jsonify(result)


@app.route("/api/events")
def api_events() -> Response:
    def event_stream():
        last = 0
        while True:
            with EVENT_LOCK:
                events = EVENTS[last:]
                last = len(EVENTS)
            for event in events:
                yield f"event: update\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            time.sleep(1)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


if __name__ == "__main__":
    ensure_env_loaded()
    ensure_files()
    start_monitor_thread()
    app.run(host="0.0.0.0", port=5000)

