import alsaaudio
import socket
import sys

CHUNK = 1024
CHANNELS = 2
RATE = 44100
PORT = 12345

def main():
    # 打开 ALSA 默认播放设备
    # 格式：S16_LE 对应 signed 16-bit little endian
    out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device='default')
    out.setchannels(CHANNELS)
    out.setrate(RATE)
    out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    out.setperiodsize(CHUNK)  # 每次处理 1024 帧，与发送端匹配

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

    print(f"✅ Linux ALSA 接收端启动，监听 {PORT} 端口...")
    print("按 Ctrl+C 停止")

    try:
        while True:
            data, addr = sock.recvfrom(CHUNK * 4)
            # 写入 ALSA 设备，返回实际写入的字节数
            out.write(data)
    except KeyboardInterrupt:
        print("\n🛑 停止播放")
    finally:
        sock.close()

if __name__ == "__main__":
    main()