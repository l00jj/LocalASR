import alsaaudio
import socket
import queue
import threading
import time

# 音频参数（两端保持一致）
SAMPLE_RATE = 44100   # 采样率
CHANNELS = 2          # 立体声
CHUNK = 1024          # 每次读取的帧数（块大小）
FORMAT = 'int16'      # 16-bit PCM（与 pyaudio.paInt16 等价）
PORT = 52210

# 缓冲大小：建议 8~16。数值越大，抗网络抖动能力越强，但延迟越大。
# 8 * 1024 / 44100 ≈ 186ms 延迟（对于语音转译完全可接受）
BUFFER_CHUNKS = 12    # 推荐 12 或 16，基本能完美抗住 WiFi 波动

# =========================
audio_queue = queue.Queue(maxsize=BUFFER_CHUNKS)

def udp_listener():
    """线程1：极速接收 UDP 数据，只负责往队列里塞"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    # 加大系统 Socket 接收缓冲区，防止内核层丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    print(f"📡 UDP 监听线程启动，缓冲队列大小: {BUFFER_CHUNKS} 个包")

    while True:
        try:
            data, addr = sock.recvfrom(4096)  # 接收数据
            # 如果队列满了，扔掉最旧的数据（保持实时性，防止内存爆炸）
            if audio_queue.full():
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    pass
            audio_queue.put_nowait(data)
        except Exception as e:
            print(f"UDP 接收错误: {e}")
            break

def audio_player():
    """线程2：从队列取数据播放，队列空了就补静音，绝不让声卡饿死"""
    out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device='default')
    out.setchannels(CHANNELS)
    out.setrate(SAMPLE_RATE)
    out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    out.setperiodsize(CHUNK)

    print("🔊 音频播放线程启动，开始平滑输出...")
    # 先等待队列攒够一半数据再开始播，建立缓冲
    while audio_queue.qsize() < BUFFER_CHUNKS // 2:
        print(f"⏳ 缓冲中... {audio_queue.qsize()}/{BUFFER_CHUNKS}")
        time.sleep(0.02)

    while True:
        try:
            # 从队列取数据，超时 0.5 秒
            data = audio_queue.get(timeout=0.1)
            out.write(data)
        except queue.Empty:
            # 如果网络断流超过 0.5 秒，播放静音防止声卡报错退出
            silence = b'\x00' * (CHUNK * 4)
            out.write(silence)
            # print("⚠️ 网络断流，插入静音补丁")
        except Exception as e:
            print(f"播放错误: {e}")

if __name__ == "__main__":
    # 启动两个线程
    t1 = threading.Thread(target=udp_listener, daemon=True)
    t2 = threading.Thread(target=audio_player, daemon=True)
    t1.start()
    t2.start()

    print("✅ 稳健接收端已启动，按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 停止接收")