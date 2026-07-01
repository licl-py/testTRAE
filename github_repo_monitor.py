#!/usr/bin/env python3
import os
import subprocess
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
LAST_COMMIT_FILE = ROOT / ".github" / "agents" / "last_monitored_commit.txt"
DEFAULT_EMAIL_TO = "licl45@lenovo.com"


def run_git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_current_branch() -> str:
    return os.environ.get("GITHUB_BRANCH") or run_git("rev-parse", "--abbrev-ref", "HEAD")


def get_remote_branch_ref(branch: str) -> str:
    return f"origin/{branch}"


def get_remote_commit(branch_ref: str) -> Optional[str]:
    try:
        return run_git("rev-parse", branch_ref)
    except subprocess.CalledProcessError:
        return None


def read_last_commit() -> Optional[str]:
    if LAST_COMMIT_FILE.exists():
        return LAST_COMMIT_FILE.read_text(encoding="utf-8").strip() or None
    return None


def write_last_commit(commit_sha: str) -> None:
    LAST_COMMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_COMMIT_FILE.write_text(commit_sha + "\n", encoding="utf-8")


def collect_commit_list(last: str, current: str) -> List[str]:
    if last == current:
        return []
    output = run_git("log", f"{last}..{current}", "--pretty=format:%h|%an|%s", "--reverse")
    return [line for line in output.splitlines() if line]


def collect_file_changes(last: str, current: str) -> List[str]:
    output = run_git("diff", "--name-status", f"{last}..{current}")
    return [line for line in output.splitlines() if line]


def collect_diff_stat(last: str, current: str) -> List[str]:
    output = run_git("diff", "--stat", f"{last}..{current}")
    return [line for line in output.splitlines() if line]


def collect_numstat(last: str, current: str) -> List[str]:
    output = run_git("diff", "--numstat", f"{last}..{current}")
    return [line for line in output.splitlines() if line]


def build_report(
    repo_url: str,
    branch: str,
    last_commit: str,
    current_commit: str,
    commits: List[str],
    file_changes: List[str],
    diff_stat: List[str],
    numstat: List[str],
) -> str:
    lines = [
        f"GitHub Repository Monitor Report",
        f"Repository: {repo_url}",
        f"Branch: {branch}",
        f"Remote commit: {current_commit}",
        f"Previous stored commit: {last_commit}",
        "",
    ]

    if commits:
        lines.append("Commits included:")
        for commit in commits:
            sha, author, message = commit.split("|", 2)
            lines.append(f"- {sha} | {author} | {message}")
        lines.append("")

    added, modified, deleted = [], [], []
    for line in file_changes:
        status, path = line.split("\t", 1)
        if status == "A":
            added.append(path)
        elif status == "M":
            modified.append(path)
        elif status == "D":
            deleted.append(path)
        else:
            modified.append(path)

    if added:
        lines.append("Added files:")
        lines.extend([f"- {item}" for item in added])
        lines.append("")
    if modified:
        lines.append("Modified files:")
        lines.extend([f"- {item}" for item in modified])
        lines.append("")
    if deleted:
        lines.append("Deleted files:")
        lines.extend([f"- {item}" for item in deleted])
        lines.append("")

    if diff_stat:
        lines.append("Diff summary:")
        lines.extend([f"  {line}" for line in diff_stat])
        lines.append("")

    if numstat:
        lines.append("Per-file line changes:")
        for line in numstat:
            added_count, removed_count, path = line.split("\t")
            lines.append(f"- {path}: +{added_count} -{removed_count}")
        lines.append("")

    lines.append("Note: Deleted files are excluded from code recommendation suggestions.")
    return "\n".join(lines)


def send_email(subject: str, body: str, to_address: str, from_address: str) -> None:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() not in ("false", "0", "no")

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError(
            "SMTP_HOST, SMTP_USER, and SMTP_PASS must be configured as environment variables to send email."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.set_content(body)

    if use_tls:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)

    try:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    finally:
        server.quit()


def get_repo_url() -> str:
    try:
        origin = run_git("remote", "get-url", "origin")
        return origin
    except subprocess.CalledProcessError:
        return "unknown"


def main() -> int:
    branch = get_current_branch()
    branch_ref = get_remote_branch_ref(branch)
    repo_url = get_repo_url()

    print(f"Monitoring remote repository {repo_url} on branch {branch_ref}...")
    run_git("fetch", "origin")

    current_commit = get_remote_commit(branch_ref)
    if not current_commit:
        print(f"Remote branch {branch_ref} not found.")
        return 1

    last_commit = read_last_commit()
    if not last_commit:
        print("No previous commit recorded. Storing current remote commit as baseline.")
        write_last_commit(current_commit)
        return 0

    if current_commit == last_commit:
        print("No new commits detected.")
        return 0

    commits = collect_commit_list(last_commit, current_commit)
    file_changes = collect_file_changes(last_commit, current_commit)
    diff_stat = collect_diff_stat(last_commit, current_commit)
    numstat = collect_numstat(last_commit, current_commit)

    report = build_report(
        repo_url=repo_url,
        branch=branch,
        last_commit=last_commit,
        current_commit=current_commit,
        commits=commits,
        file_changes=file_changes,
        diff_stat=diff_stat,
        numstat=numstat,
    )

    to_address = os.environ.get("MONITOR_EMAIL_TO", DEFAULT_EMAIL_TO)
    from_address = os.environ.get("MONITOR_EMAIL_FROM", smtp_user := os.environ.get("SMTP_USER", "noreply@local"))
    subject = f"[GitHub Monitor] Updates in {repo_url} ({branch})"

    print("Sending email report to", to_address)
    send_email(subject=subject, body=report, to_address=to_address, from_address=from_address)
    write_last_commit(current_commit)

    print("Email report sent and baseline updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
