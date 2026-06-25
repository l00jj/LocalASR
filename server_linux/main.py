import alsaaudio
import socket
import sys


# 音频参数（两端保持一致）
SAMPLE_RATE = 44100   # 采样率
CHANNELS = 2          # 立体声
CHUNK = 1024          # 每次读取的帧数（块大小）
FORMAT = 'int16'      # 16-bit PCM（与 pyaudio.paInt16 等价）
PORT = 52210

def main():
    # 打开 ALSA 默认播放设备
    # 格式：S16_LE 对应 signed 16-bit little endian
    out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device='default')
    out.setchannels(CHANNELS)
    out.setrate(SAMPLE_RATE)
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