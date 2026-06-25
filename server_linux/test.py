import os
import numpy as np
import threading
import tempfile
import sys
import time
import socket
import struct
from faster_whisper import WhisperModel
import soundfile as sf

# ================== 音频参数（与发送端一致） ==================
SAMPLE_RATE = 44100          # 必须与发送端一致
CHANNELS = 2
CHUNK = 1024                 # 每包帧数
FORMAT = 'int16'             # 发送端使用 int16

# ================== UDP 接收配置 ==================
UDP_PORT = 52210             # 与发送端目标端口一致

# ================== 识别模型配置 ==================
# 模型实际路径
MODEL_PATH = os.path.expanduser("~/LocalASR/server_linux/models/faster-whisper-tiny.en")
LANG = "en"

# 低延迟断句参数（与原代码相同）
SILENCE_THRESHOLD = 0.01
MIN_SILENCE_DURATION = 0.4
MAX_SEGMENT_DURATION = 8.0
MIN_SPEECH_DURATION = 0.3

VAD_THRESHOLD = 0.5
VAD_MIN_SPEECH_MS = 150
VAD_MIN_SILENCE_MS = 300
VAD_SPEECH_PAD_MS = 200

# ================== 加载模型 ==================
print(f"加载识别模型: {MODEL_PATH}")
model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")

# ================== 全局音频缓冲区 ==================
audio_buffer = np.empty((0,), dtype=np.float32)   # mono float32
buffer_lock = threading.Lock()
silence_counter = 0.0
speech_detected = False
speech_length = 0.0

# ================== UDP 接收线程 ==================
def udp_receiver():
    """持续接收 UDP 音频流，转换为 mono float32 并追加到 buffer"""
    global audio_buffer, silence_counter, speech_detected, speech_length

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    # 加大接收缓冲区，防止丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    print(f"UDP 接收端启动，监听端口 {UDP_PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(CHUNK * CHANNELS * 2)  # 1024*2*2 = 4096 字节
        except Exception as e:
            print(f"UDP 接收错误: {e}", file=sys.stderr)
            continue

        # 将 bytes 转为 int16 numpy 数组 (shape: (CHUNK*CHANNELS,))
        audio_int16 = np.frombuffer(data, dtype=np.int16)
        # 重塑为 (frames, channels)
        audio_int16 = audio_int16.reshape(-1, CHANNELS)
        # 转为 float32 并归一化到 [-1, 1]
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        # 取平均转为单声道
        mono = np.mean(audio_float32, axis=1)

        # ---- 以下逻辑与原 audio_callback 完全相同 ----
        with buffer_lock:
            audio_buffer = np.concatenate([audio_buffer, mono])
            # 检测是否有声音
            if np.max(np.abs(mono)) > SILENCE_THRESHOLD:
                silence_counter = 0.0
                speech_detected = True
                speech_length += len(mono) / SAMPLE_RATE
            elif speech_detected:
                silence_counter += len(mono) / SAMPLE_RATE

# ================== 识别工作线程（与原代码完全相同） ==================
def recognition_worker():
    global audio_buffer, silence_counter, speech_detected, speech_length
    while True:
        time.sleep(0.05)
        with buffer_lock:
            # 条件1：连续静音达到阈值，且语音长度足够
            if (speech_detected and
                silence_counter >= MIN_SILENCE_DURATION and
                speech_length >= MIN_SPEECH_DURATION and
                len(audio_buffer) >= SAMPLE_RATE * MIN_SPEECH_DURATION):
                segment = audio_buffer.copy()
                audio_buffer = np.empty((0,), dtype=np.float32)
                silence_counter = 0.0
                speech_detected = False
                speech_length = 0.0
            # 条件2：强制切断（避免等太久）
            elif len(audio_buffer) >= MAX_SEGMENT_DURATION * SAMPLE_RATE:
                segment = audio_buffer.copy()
                audio_buffer = np.empty((0,), dtype=np.float32)
                silence_counter = 0.0
                speech_detected = False
                speech_length = 0.0
            else:
                continue

        # 保存临时 WAV 文件并识别
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        sf.write(temp_path, segment, SAMPLE_RATE)
        try:
            segments, _ = model.transcribe(
                temp_path,
                language=LANG,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    threshold=VAD_THRESHOLD,
                    min_speech_duration_ms=VAD_MIN_SPEECH_MS,
                    min_silence_duration_ms=VAD_MIN_SILENCE_MS,
                    speech_pad_ms=VAD_SPEECH_PAD_MS
                ),
                condition_on_previous_text=False
            )
            for seg in segments:
                text = seg.text.strip()
                if text:
                    print(f"[识别] {text}")
        except Exception as e:
            print(f"[识别错误] {e}", file=sys.stderr)
        finally:
            os.unlink(temp_path)

# ================== 启动线程 ==================
udp_thread = threading.Thread(target=udp_receiver, daemon=True)
udp_thread.start()

recog_thread = threading.Thread(target=recognition_worker, daemon=True)
recog_thread.start()

print("实时语音识别已启动（从 UDP 接收音频流），按 Ctrl+C 停止...")
try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\n停止识别")