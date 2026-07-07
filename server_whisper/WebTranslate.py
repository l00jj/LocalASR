import sys
import requests
import multiprocessing
from typing import Optional, Callable, Tuple

# ---------- 翻译函数（在子进程中执行） ----------


def translate_text(source_text: str, to_lang: str, server: str) -> Tuple[bool, str]:
    """
    调用翻译 API，返回翻译结果（字符串）。
    （逻辑直接来自原 translate.py 的 translate_text 函数）
    """
    print("_translate_text", source_text, to_lang, server)
    prompt = f"将以下文本翻译为{to_lang}，注意只需要输出翻译后的结果，不要额外解释：\n{source_text}"
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 0.6,
        "top_k": 20,
        "repetition_penalty": 1.05,
    }

    # 规范化服务器地址
    if not server.startswith(("http://", "https://")):
        server = f"http://{server}"
    api_url = f"{server}/v1/chat/completions"

    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            tran_test = result["choices"][0]["message"]["content"].strip()
            return (True, tran_test)
        else:
            print(f"[翻译环节] 服务器状态: {resp.text}", file=sys.stderr)
            return (False, resp.text)
    except Exception as e:
        print(f"[翻译环节] 请求失败: {e}", file=sys.stderr)
        return (False, e)

# ================== 翻译服务类 ==================


class TranslationService:
    """
    异步翻译服务，使用进程池隔离翻译任务，避免 GIL 影响。

    :param server: 翻译 API 服务器地址（例如 "127.0.0.1:52208"）
    :param pool_processes: 并发翻译的进程数
    :param max_size: 最大翻译队列上限
    """

    def __init__(self, server: str = "127.0.0.1:52208", pool_processes: int = 3, max_size: int = 20):
        self.server = server
        # 这里的 processes 是指处理并发量非队列上限，multiprocessing 自身没有控制队列上限
        self.pool = multiprocessing.Pool(processes=pool_processes)

    # ---------- 对外接口 ----------
    def translate(self, text: str, to_lang: str = "中文", callback: Optional[Callable[[bool, str], None]] = None) -> None:
        """
        提交一个翻译任务（非阻塞）。

        :param text:       待翻译的原始文本
        :param to_lang:    目标语言（目前仅支持中文，保留用于未来扩展）
        :param callback:   回调函数，接收一个字符串参数（翻译结果），
                           若翻译失败，回调参数为报错字串
        """
        # 定义任务完成后的回调（在父进程中执行）
        def done_callback(task_result: Tuple[bool, str]) -> None:
            is_ok, result = task_result
            if callback:
                callback(is_ok, result)

        # 异步提交任务到进程池
        # self.pool.apply_async(
        #     self._translate_text,
        #     args=(text, to_lang, self.server),
        #     callback=done_callback
        # )
        self.pool.apply_async(
            translate_text,
            args=(text, to_lang, self.server),
            callback=done_callback
        )

    def close(self) -> None:
        """关闭进程池，等待所有任务完成（优雅退出）。"""
        self.pool.close()
        self.pool.join()

    # 支持上下文管理器（with 语法）
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ================== 测试 / 直接运行 ==================
if __name__ == "__main__":
    # 示例：定义回调函数
    def print_result(translated: str):
        print(f"✅ 翻译结果: {translated}")

    # 创建服务实例（进程池大小 2）
    service = TranslationService(server="127.0.0.1:52208", max_workers=2)

    # 提交多个翻译任务（非阻塞）
    service.translate("Hello, how are you?", callback=print_result)
    service.translate("The weather is nice today.", callback=print_result)

    # 等待足够时间让任务完成（生产环境不用 sleep，可通过回调或队列同步）
    import time
    time.sleep(5)

    # 关闭服务（等待所有任务结束）
    service.close()
