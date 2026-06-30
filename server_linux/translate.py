import argparse
import requests
import sys

# ================== 翻译 API 配置 ==================
# 默认服务器地址（仅主机:端口），也可传入完整 base URL
DEFAULT_SERVER = "127.0.0.1:52208"

def translate_text(source_text, server=None):

    prompt = f"将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n{source_text}"
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 0.6,
        "top_k": 20,                     # llama.cpp 扩展参数，可直接放顶层
        "repetition_penalty": 1.05,      # 同上
    }

    # 处理 server 参数
    if server is None:
        server = DEFAULT_SERVER
    # 如果未包含协议，自动添加 http://
    if not server.startswith(("http://", "https://")):
        server = f"http://{server}"
    # 拼接完整的 API 端点
    api_url = f"{server}/v1/chat/completions"

    try:
        resp = requests.post(api_url, json=payload, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            # print(result)
            zh = result["choices"][0]["message"]["content"].strip()
            return zh
        else:
            print(f"[翻译] 服务错误: {resp.text}", file=sys.stderr)
            return ""
    except Exception as e:
        print(f"[翻译] 请求失败: {e}", file=sys.stderr)
        return ""

# 若此文件被直接运行，可测试（可选）
if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(description="截获参数的示例")
    
    # 定义截获的参数
    parser.add_argument("--server", type=str, required=True, help="服务器地址")
    parser.add_argument("--c", type=str, required=True, help="需要的翻译内容")
    args = parser.parse_args()
    
    # 需要翻译的内容
    translate_content = args.c

    # 解析 server
    target_server = args.server
    target_ip, port_str = target_server.rsplit(':', 1)
    target_port = int(port_str)

    print(translate_text(translate_content, target_server))


'''
python3 /Volumes/Room/app-git/LocalASR/server_linux/translate.py --c "Use this reference to look up OpenAI API endpoints, request and response schemas, streaming events, client library methods, and shared behavior such as authentication, errors, rate limits, and request IDs." --server 192.168.0.118:52208

python3 ~/LocalASR/server_linux/translate.py --c "Use this reference to look up OpenAI API endpoints, request and response schemas, streaming events, client library methods, and shared behavior such as authentication, errors, rate limits, and request IDs." --server 127.0.0.1:52208
'''
