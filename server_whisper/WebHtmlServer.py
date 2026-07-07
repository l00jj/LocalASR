#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
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
    简单的静态文件 HTTP 服务器，提供 ./webui 目录下的文件。
    默认首页为 index.html。
    """

    def __init__(self, port: int = 8080):
        """
        :param port: 监听端口
        """
        self.port = port
        self.server = None
        self._running = False

    def start(self):
        """启动 HTTP 服务器（阻塞）"""
        # 确定 webui 目录路径（相对于当前工作目录）
        web_dir = os.path.join(os.getcwd(), 'webui')
        if not os.path.isdir(web_dir):
            raise FileNotFoundError(f"静态目录 'webui' 不存在于 {web_dir}")

        # 自定义 Handler，指定根目录
        class Handler(SimpleHTTPRequestHandler):
            directory = web_dir   # Python 3.7+ 支持

        self.server = HTTPServer(('0.0.0.0', self.port), Handler)
        self._running = True

        # 打印访问地址
        print(f"✅ Web 服务已启动")
        print(f"   根目录: {web_dir}")
        for item in get_all_local_ips():
            print(f"   web: http://{item}:{self.port}")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.stop()
        finally:
            self._running = False

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🛑 Web 服务已停止")


# ---------- 测试入口 ----------
if __name__ == '__main__':
    # 导入 WebBroadcast（假设与当前文件同目录）
    from WebBroadcast import WebBroadcast
    import time
    import threading

    # 1. 启动 WebSocket 广播服务
    broadcast = WebBroadcast(port=52218, max_queue_size=20, max_clients=10)
    broadcast.start()
    print("WebSocket 广播服务已启动")

    # 2. 启动 Web 服务器（在独立线程中，避免阻塞主线程）
    html_server = WebHtmlServer(port=52280)
    server_thread = threading.Thread(target=html_server.start, daemon=True)
    server_thread.start()

    # 3. 主线程持续发送测试消息
    count = 0
    try:
        while True:
            time.sleep(2)
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
        html_server.stop()