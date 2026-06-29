import os
import numpy as np
import librosa
import threading
import tempfile
import sys
import time
import socket
import struct
from faster_whisper import WhisperModel
import soundfile as sf

# ================== 音频参数（与发送端一致） ==================
SOURCE_SAMPLE_RATE = 44100          # 必须与发送端一致
CHANNELS = 2
CHUNK = 1024                 # 每包帧数
FORMAT = 'int16'             # 发送端使用 int16

# ================== 音频输入 faster-whisper 模型参数 ==================
TARGET_SAMPLE_RATE = 16000

# ================== UDP 接收配置 ==================
UDP_PORT = 52210             # 与发送端目标端口一致

# ================== 识别模型配置 ==================
# 模型实际路径
MODEL_PATH = os.path.expanduser("~/LocalASR/server_linux/models/faster-whisper-base.en")
LANG = "en"


# 低延迟断句参数

'''
#### A. 业务层参数（你在 `recognition_worker` 中控制切分音频块的）

- **`SILENCE_THRESHOLD = 0.01`**
  - **作用**：音量阈值。当音频数据的振幅绝对值超过 `0.01` 时，认为“有声音”；低于它且持续一段时间，认为“进入了静音”。
  - **调优**：如果背景有底噪，调高到 `0.02~0.03` 防止误触发。

- **`MIN_SILENCE_DURATION = 0.4`**
  - **作用**：**断句的“刹车”**。当检测到连续静音达到 0.4 秒时，立即把这一段音频打包送去识别。
  - **含义**：这是你整条链路**延迟和准确性的核心开关**。0.4 秒能保证说话停顿后快速出字（低延迟），但如果说话语速慢、换气长，可能造成句子被切断。

- **`MIN_SPEECH_DURATION = 0.3`**
  - **作用**：**防抖过滤**。只有语音持续超过 0.3 秒，才会被送去识别。
  - **含义**：用来过滤掉“咔哒”声、键盘敲击声等瞬态噪音，避免空转 CPU。

'''

SILENCE_THRESHOLD = 0.01
MIN_SILENCE_DURATION = 0.4
MIN_SPEECH_DURATION = 0.3
# 最大音频缓冲时间（累计判断是一句话未中断或持续无声音）
MAX_SEGMENT_DURATION = 16.0


'''
#### B. 模型层参数（传给 `model.transcribe` 的 `vad_parameters`）

这是 `faster-whisper` **内部自带的 VAD 滤波器**，作用是在你切好的 `segment` 里，**把两头多余的静音再“修剪”掉**，并判断中间哪些片段确实是人声。

- **`VAD_THRESHOLD = 0.5`**
  - **作用**：语音检测的敏感度。值越高（越接近 1），只有非常像人声的才会保留；值越低，越容易把噪音当人声。
  - **调优**：如果识别结果里经常出现噪音被翻译成奇怪英文，可以提到 `0.6~0.7`。
  - 默认值：0.5

- **`VAD_MIN_SPEECH_MS = 150`**
  - **作用**：认为“人声”的最短持续时间是 150 毫秒。短于这个的统统忽略。
  - 默认值：250

- **`VAD_MIN_SILENCE_MS = 300`**
  - **作用**：在 Whisper 内部判断，如果这一段话里静音超过 300 毫秒，就强行把句子切开（生成多个 `seg`）。
  - **注意**：**这里有个叠加效应！** 你的业务逻辑已经用 0.4 秒（400ms）切了一次，这里又用 300ms 切一次。好处是，即使你业务逻辑没切（比如因为 `MAX_SEGMENT_DURATION` 强制切了超大段），Whisper 内部也会帮你把这句话里因换气造成的停顿拆开，输出更流畅的短句。
  - 默认值：100

- **`VAD_SPEECH_PAD_MS = 200`**
  - **作用**：在检测到的人声片段前后，**额外保留 200 毫秒**的音频。
  - **含义**：防止 VAD 切得太干净，把字头字尾的轻微爆破音（如 p、t、k）给切丢了，导致识别缺字。保留一点上下文能让识别更准。
  - 默认值：400
'''

VAD_THRESHOLD = 0.5
VAD_MIN_SPEECH_MS = 150
VAD_MIN_SILENCE_MS = 100
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

        # 重采样到目标码率
        target_rate_mono = librosa.resample(mono, orig_sr=SOURCE_SAMPLE_RATE, target_sr=TARGET_SAMPLE_RATE) if SOURCE_SAMPLE_RATE != TARGET_SAMPLE_RATE else mono

        # 追加至缓冲区
        with buffer_lock:
            audio_buffer = np.concatenate([audio_buffer, target_rate_mono])
            # 检测是否有声音
            if np.max(np.abs(target_rate_mono)) > SILENCE_THRESHOLD: speech_detected = True

# ================== 识别工作线程（与原代码完全相同） ==================
def recognition_worker():
    global audio_buffer, silence_counter, speech_detected, speech_length
    while True:
        time.sleep(1)
        with buffer_lock:
            # 条件1：连续静音达到阈值，且语音长度足够
            # if (speech_detected and
            #     silence_counter >= MIN_SILENCE_DURATION and
            #     speech_length >= MIN_SPEECH_DURATION and
            #     len(audio_buffer) >= SAMPLE_RATE * MIN_SPEECH_DURATION):
            #     segment = audio_buffer.copy()
            #     audio_buffer = np.empty((0,), dtype=np.float32)
            #     silence_counter = 0.0
            #     speech_detected = False
            #     speech_length = 0.0
            # # 条件2：强制切断（避免等太久）
            # elif len(audio_buffer) >= MAX_SEGMENT_DURATION * TARGET_SAMPLE_RATE:
            #     segment = audio_buffer.copy()
            #     audio_buffer = np.empty((0,), dtype=np.float32)
            #     silence_counter = 0.0
            #     speech_detected = False
            #     speech_length = 0.0
            if speech_detected:
                current_audio_buffer = audio_buffer.copy()
                speech_detected = False
            elif len(audio_buffer) >= MAX_SEGMENT_DURATION * TARGET_SAMPLE_RATE:
                current_audio_buffer = audio_buffer.copy()
                audio_buffer = np.empty((0,), dtype=np.float32)
                speech_detected = False
            else:
                continue
        
        # 直接处理音频数据
        

        # ======= 处理计时 =======
        # 记录音频实际时长（秒）
        timer_audio_duration = len(current_audio_buffer) / TARGET_SAMPLE_RATE
        # 开始计时
        timer_start_time = time.perf_counter()


        try:
            segments, _ = model.transcribe(
                current_audio_buffer,
                language=LANG,
                beam_size=5,                                     # 搜索宽度，结果前 N 候选
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
                    print(f"[{seg.start:.2f}s -> {seg.end:.2f}s]")
                    print(f"[识别] {text}")

            # ======= 处理计时 =======
            # 结束计时
            timer_end_time = time.perf_counter()
            timer_process_time = timer_end_time - timer_start_time
            rtf = timer_process_time / timer_audio_duration
            print(f"[性能] 音频长度: {timer_audio_duration:.2f}s | "
                  f"推理耗时: {timer_process_time:.3f}s | "
                  f"RTF: {rtf:.2f} {'✅ 实时' if rtf < 1.0 else '❌ 超时'}")
            
        except Exception as e:
            print(f"[识别错误] {e}", file=sys.stderr)

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