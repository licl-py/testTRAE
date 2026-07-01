import json
from flask import Flask, render_template, request, Response, jsonify, stream_with_context
from ollama import Client

app = Flask(__name__)

DEFAULT_HOST = 'http://10.245.100.186:12434'
DEFAULT_MODEL = 'qwen3.5:27b'


def create_translation_prompt(text: str) -> str:
    return f"""你是一个翻译工具，要做中英互译。请检测以下文本的语言：
{text}

如果文本是中文，请翻译成英文；如果是英文，请翻译成中文。你的回答只能包含翻译结果，不能包含其他任何内容。"""


def translate_stream(client: Client, text: str, model: str):
    prompt = create_translation_prompt(text)
    messages = [
        {"role": "system", "content": "你是一个专业的中英互译助手。"},
        {"role": "user", "content": prompt}
    ]

    try:
        stream = client.chat(
            model=model,
            stream=True,
            messages=messages,
            options={
                'temperature': 0.1,
                'num_predict': 8192,
                'top_p': 0.9,
                'presence_penalty': 0.1,
                'frequency_penalty': 0.1,
                'num_ctx': 32768
            },
            keep_alive=-1
        )

        for chunk in stream:
            content = chunk['message']['content']
            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text', '').strip()
    host = data.get('host', DEFAULT_HOST)
    model = data.get('model', DEFAULT_MODEL)

    if not text:
        return jsonify({'error': '请输入要翻译的文本'}), 400

    client = Client(host=host)
    return Response(
        stream_with_context(translate_stream(client, text, model)),
        mimetype='text/event-stream'
    )


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)