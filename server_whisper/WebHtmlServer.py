#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import http.server
import urllib.parse
import threading
import time
import netifaces


def get_all_local_ips():
    ips = []
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        ipv4 = addrs.get(netifaces.AF_INET, [])
        for addr in ipv4:
            ip = addr['addr']
            if ip != '127.0.0.1' and not ip.startswith('169.254'):  # 过滤掉链路本地地址
                ips.append(ip)
    return ips


class WebHtmlServer:
    """
    安全的静态文件 HTTP 服务器，只服务于指定目录（默认为 ./webui）。
    特性：
        - 仅允许访问目录内的文件（禁止路径遍历）
        - 自动返回 index.html 作为默认页面
        - 禁止目录列表（访问目录返回 404）
        - 启动时打印本地和局域网访问地址
    """

    def __init__(self, port: int = 8080, web_dir: str = 'webui'):
        """
        :param port:     监听端口
        :param web_dir:  静态文件根目录（相对于当前工作目录）
        """
        self.port = port
        self.web_dir = os.path.abspath(web_dir)
        if not os.path.isdir(self.web_dir):
            raise FileNotFoundError(f"静态目录不存在: {self.web_dir}")
        self._server = None
        self._running = False

    def start(self):
        """启动 HTTP 服务（阻塞）"""
        # 捕获 web_dir 供 Handler 使用
        web_dir = self.web_dir

        # 自定义请求处理器
        class SecureHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=web_dir, **kwargs)

            def translate_path(self, path):
                path = urllib.parse.urlparse(path).path
                if path.startswith('/'):
                    path = path[1:]
                full_path = os.path.join(self.directory, path)
                full_path = os.path.realpath(full_path)
                real_dir = os.path.realpath(self.directory)
                # 允许路径等于根目录，或以根目录+斜杠开头
                if not (full_path == real_dir or full_path.startswith(real_dir + os.sep)):
                    # 越界访问，返回不存在的路径
                    return os.path.join(self.directory, 'FORBIDDEN')
                return full_path

            def send_head(self):
                path = self.translate_path(self.path)
                if os.path.isdir(path):
                    index_path = os.path.join(path, 'index.html')
                    if os.path.exists(index_path):
                        self.path = self.path.rstrip('/') + '/index.html'
                        return super().send_head()
                    else:
                        self.send_error(404, "Not Found")
                        return None
                else:
                    return super().send_head()

        # 创建服务器
        self._server = http.server.HTTPServer(
            ('0.0.0.0', self.port), SecureHandler)
        self._running = True

        # 获取局域网地址
        # 打印访问地址
        print(f"✅ Web 服务已启动")
        print(f"   根目录: {web_dir}")
        for item in get_all_local_ips():
            print(f"   web: http://{item}:{self.port}")

        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            self.stop()
        finally:
            self._running = False

    def stop(self):
        """停止服务器"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            print("🛑 Web 服务已停止")


# ---------- 独立测试入口 ----------
if __name__ == '__main__':
    from WebBroadcast import WebBroadcast   # 假设同目录存在

    # 1. 启动 WebSocket 广播服务（测试用）
    broadcast = WebBroadcast(port=52218, max_queue_size=20, max_clients=10)
    broadcast.start()
    print("WebSocket 广播服务已启动")

    # 2. 启动 Web 服务器（在独立线程中运行）
    web_server = WebHtmlServer(port=52280, web_dir='webui')   # 使用与之前一致的端口
    server_thread = threading.Thread(target=web_server.start, daemon=True)
    server_thread.start()

    # 3. 主线程持续发送测试消息
    count = 0
    try:
        while True:
            time.sleep(3)
            count += 1
            test_data = [{
                "start": count * 1000,
                "duration": 2.5,
                "original": f"Test message {count}",
                "translation": f"测试消息 {count}",
                "final": bool(count & 1)
            }]
            broadcast.send(test_data)
            print(f"📨 发送广播 #{count}")
    except KeyboardInterrupt:
        print("\n🛑 停止测试...")
    finally:
        broadcast.stop()
        web_server.stop()
