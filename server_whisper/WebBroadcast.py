import asyncio
import json
import threading
import logging
from typing import List, Set, Optional
import copy
from dataclasses import dataclass, asdict
import websockets


# 你的数据类（可替换）
@dataclass
class TranResult:
    start: int
    duration: float
    original: str
    translation: str
    final: bool


logger = logging.getLogger(__name__)


class WebBroadcast:
    """
    WebSocket 字幕广播服务。

    :param port: 监听端口
    :param max_queue_size: 发送队列最大长度，超出时新消息会被丢弃
    :param max_clients: 允许的最大客户端连接数，超出时新连接将被拒绝
    """

    def __init__(self, port: int = 8765, max_queue_size: int = 20, max_clients: int = 10):
        self.port = port
        self.max_queue_size = max_queue_size
        self.max_clients = max_clients

        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.send_queue: Optional[asyncio.Queue] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._server = None

    # ---------- 对外接口 ----------
    def start(self) -> None:
        """启动后台 WebSocket 服务（非阻塞）。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止服务，关闭所有连接。"""
        if not self._running:
            return
        self._running = False
        if self.loop:
            # 优雅关闭服务器和事件循环
            async def shutdown():
                if self._server:
                    self._server.close()
                    await self._server.wait_closed()
                # 取消所有任务（可选）
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
            asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("广播服务已停止")

    # 整合列表功能未完善
    def send(self, results: List[TranResult]) -> None:
        """
        发送一条或多条字幕消息（批量推送）。

        :param results: TranResult 对象的列表（至少一个元素）
        """
        if not self._running:
            raise RuntimeError("广播服务尚未启动，请先调用 start()")
        if not isinstance(results, list):
            results = list(results)  # 兼容传入单个对象

        # 将对象异步放入队列（线程安全）
        asyncio.run_coroutine_threadsafe(
            self._put_to_queue(copy.deepcopy(results)),
            self.loop
        )

    # ---------- 内部异步逻辑 ----------
    def _run_loop(self) -> None:
        """在独立线程中运行事件循环。"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_server())
        self.loop.run_forever()

    async def _start_server(self) -> None:
        """初始化队列、广播任务和 WebSocket 服务器。"""
        self.send_queue = asyncio.Queue(maxsize=self.max_queue_size)
        asyncio.create_task(self._broadcast_worker())
        self._server = await websockets.serve(
            self._handle_client,
            "0.0.0.0",
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        logger.info(
            f"WebSocket 广播服务已启动，端口 {self.port}，最大队列 {self.max_queue_size}，最大客户端 {self.max_clients}")

    async def _handle_client(self, websocket, path):
        """处理新客户端连接。"""
        if len(self.clients) >= self.max_clients:
            await websocket.close(code=1008, reason="Too many clients")
            return
        self.clients.add(websocket)
        logger.info(f"客户端连接，当前在线: {len(self.clients)}")
        try:
            # 保持连接活跃，接收客户端消息（本场景忽略）
            async for _ in websocket:
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"客户端断开，当前在线: {len(self.clients)}")

    async def _broadcast_worker(self):
        """后台消费者：从队列取消息并广播。"""
        while self._running:
            try:
                results = await self.send_queue.get()
                # 序列化为 JSON
                try:
                    message = json.dumps(asdict(results), ensure_ascii=False)
                except Exception as e:
                    logger.error(f"序列化失败: {e}")
                    continue

                if not self.clients:
                    continue

                # 并发广播给所有在线客户端
                current_clients = list(self.clients)
                await asyncio.gather(
                    *[self._send_to_client(c, message)
                      for c in current_clients],
                    return_exceptions=True
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"广播工作异常: {e}")

    async def _send_to_client(self, client, message):
        """向单个客户端发送消息，失败时自动移除。"""
        try:
            await client.send(message)
        except (websockets.ConnectionClosed, websockets.WebSocketException):
            self.clients.discard(client)

    async def _put_to_queue(self, results):
        """将结果放入队列（队列满时丢弃）。"""
        try:
            self.send_queue.put_nowait(results)
        except asyncio.QueueFull:
            logger.warning("发送队列已满，丢弃一条消息")
