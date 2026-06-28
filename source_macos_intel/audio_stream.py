import argparse
import sounddevice as sd
import socket
import numpy as np
import sys

# 音频参数（和接收端保持一致）
SAMPLE_RATE = 44100   # 采样率
CHANNELS = 2          # 立体声
CHUNK = 1024          # 每次读取的帧数（块大小）
FORMAT = 'int16'      # 16-bit PCM（与 pyaudio.paInt16 等价）

# 接收端 UDP 配置
target_server = ""            # 接收端 Server (192.168.0.118:52210)
target_ip = "192.168.0.113"   # 接收端 IP (192.168.0.118)
target_port = 52210           # 接收端 PORT (52210)

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
    sock.sendto(indata.tobytes(), (target_ip, target_port))

# 打开音频输入流（使用回调模式）
stream = sd.InputStream(
    device=device_id,
    channels=CHANNELS,
    samplerate=SAMPLE_RATE,
    dtype=FORMAT,
    blocksize=CHUNK,
    callback=audio_callback
)


def main():
    global target_server, target_ip, target_port
    # 创建解析器
    parser = argparse.ArgumentParser(description="截获参数的示例")
    
    # 定义你想要截获的参数
    parser.add_argument("--server", type=str, required=True, help="服务器地址")
    args = parser.parse_args()
    
    # 解析 server
    target_server = args.server
    target_ip, port_str = target_server.rsplit(':', 1)
    target_port = int(port_str)
    
    # --- 启动前先测试 UDP 连通性 ---
    print(f"推理服务器入口: {target_server}")
    # try:
    #     test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     test_sock.settimeout(2)  # 设置超时
    #     test_sock.sendto(b'test', (target_ip, target_port))
    #     # 如果 sendto 不抛异常，就认为本地网络正常
    #     test_sock.close()
    # except Exception as e:
    #     print(f"目标地址不可达或网络错误: {e}")
    #     sys.exit(1)

    print(f"开始推流到 {target_ip}:{target_port} ... (按 Ctrl+C 停止)")
    try:
        with stream:
            # 保持流打开，直到用户中断
            while True:
                sd.sleep(1000)  # 简单休眠，让回调持续运行
    except KeyboardInterrupt:
        print("\n推流已停止")
        sock.close()


if __name__ == '__main__':
    main()
