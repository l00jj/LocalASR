import sounddevice as sd
import socket
import numpy as np

# 音频参数（和接收端保持一致）
SAMPLE_RATE = 44100   # 采样率
CHANNELS = 2          # 立体声
CHUNK = 1024          # 每次读取的帧数（块大小）
FORMAT = 'int16'      # 16-bit PCM（与 pyaudio.paInt16 等价）

# 接收端 UDP 配置
TARGET_IP = "192.168.0.113"   # 替换为接收端 IP
TARGET_PORT = 52210

def find_blackhole_device():
    """查找 BlackHole 输入设备的索引（设备 ID）"""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'BlackHole' in dev['name'] and dev['max_input_channels'] > 0:
            print(f"使用输入设备: {dev['name']} (ID={i})")
            return i
    raise RuntimeError("未找到 BlackHole 输入设备，请确保已安装并加载 BlackHole")

# 获取 BlackHole 设备 ID
device_id = find_blackhole_device()

# 创建 UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def audio_callback(indata, frames, time, status):
    """
    回调函数：当音频数据可用时，通过 UDP 发送
    indata: numpy 数组，shape=(frames, channels)，dtype=int16
    """
    if status:
        print(f"音频状态: {status}", flush=True)
    # 将音频数据转为 bytes 并发送
    # indata 是 int16 类型，直接 tobytes() 即可
    sock.sendto(indata.tobytes(), (TARGET_IP, TARGET_PORT))

# 打开音频输入流（使用回调模式）
stream = sd.InputStream(
    device=device_id,
    channels=CHANNELS,
    samplerate=SAMPLE_RATE,
    dtype=FORMAT,
    blocksize=CHUNK,
    callback=audio_callback
)

print(f"开始推流到 {TARGET_IP}:{TARGET_PORT} ... (按 Ctrl+C 停止)")
try:
    with stream:
        # 保持流打开，直到用户中断
        while True:
            sd.sleep(1000)  # 简单休眠，让回调持续运行
except KeyboardInterrupt:
    print("\n推流已停止")
    sock.close()