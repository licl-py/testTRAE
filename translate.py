import argparse
import sys
from ollama import Client


def create_translation_prompt(text: str) -> str:
    return f"""你是一个翻译工具，要做中英互译。请检测以下文本的语言：
{text}

如果文本是中文，请翻译成英文；如果是英文，请翻译成中文。你的回答只能包含翻译结果，不能包含其他任何内容。"""


def translate_text(client: Client, text: str, model: str = "qwen3.5:27b") -> str:
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
        
        result = ""
        for chunk in stream:
            content = chunk['message']['content']
            result += content
            print(content, end='', flush=True)
        
        return result.strip()
    
    except Exception as e:
        print(f"\n翻译出错: {str(e)}", file=sys.stderr)
        raise


def main():
    # 创建命令行参数解析器，用于解析用户传入的参数
    parser = argparse.ArgumentParser(description='中英互译工具 - 使用Ollama API')
    # --host: Ollama服务的地址，默认使用内网地址
    parser.add_argument('--host', default='http://10.245.100.186:12434', 
                        help='Ollama服务地址')
    # --model: 指定要使用的翻译模型，默认使用qwen3.5:27b
    parser.add_argument('--model', default='qwen3.5:27b', 
                        help='使用的模型名称')
    # --text: 必填参数，需要翻译的原始文本
    parser.add_argument('--text', required=True, 
                        help='要翻译的文本')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    try:
        # 根据指定的host地址创建Ollama客户端连接
        client = Client(host=args.host)
        # 打印当前使用的服务和模型信息
        print(f"已连接到Ollama服务: {args.host}")
        print(f"使用模型: {args.model}")
        print(f"待翻译文本: {args.text}")
        print("=" * 50)
        print("翻译结果: ", end='')
        
        # 调用翻译函数，使用流式输出逐字打印翻译结果
        translate_text(client, args.text, args.model)
        print("\n" + "=" * 50)
        
    except Exception as e:
        # 捕获所有异常，输出错误信息到标准错误流并以非零状态码退出
        print(f"\n错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()