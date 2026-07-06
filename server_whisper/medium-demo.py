import os
import numpy as np
import librosa
import threading
import sys
import time
import socket
import queue
from collections import deque
from faster_whisper import WhisperModel
import soundfile as sf

# ================== 音频参数（与发送端一致） ==================
SOURCE_SAMPLE_RATE = 44100          # 必须与发送端一致
CHANNELS = 2
CHUNK = 1024                        # 每包帧数
FORMAT = 'int16'                    # 发送端使用 int16

# ================== 音频输入 faster-whisper 模型参数 ==================
TARGET_SAMPLE_RATE = 16000

# ================== UDP 接收配置 ==================
UDP_PORT = 52210                        # 与发送端目标端口一致
READABLE_BUFFER_SIZE = 1024 * 1024 * 7  # 7M 缓存

# ================== 识别模型配置 ==================
# 模型实际路径
MODEL_PATH = os.path.expanduser("~/LocalASR/server_whisper/models/faster-whisper-small")
LANG = "en"          # 不指定 None，

# ================== 推理参数 ==================
# 推理间隔 (秒)
TIME_INFERENCE_INTERVAL = 1
# 静音判定阈值
SILENCE_THRESHOLD = 0.01
# 最大音频缓冲时间（累计判断是一句话未中断或持续无声音）
MAX_SEGMENT_DURATION = 36.0
MAX_SEGMENT_DURATION_SIZE = MAX_SEGMENT_DURATION * TARGET_SAMPLE_RATE


'''
模型层参数
faster-whisper 的 VAD 滤波器用于判断音频人声片段

VAD_THRESHOLD = 0.5
语音检测的敏感度。值越高（越接近 1），只有非常像人声的才会保留；值越低，越容易把噪音当人声
如果识别结果里经常出现噪音被翻译成奇怪英文，可以提到 `0.6~0.7`
默认值：0.5

VAD_MIN_SPEECH_MS = 150
认为“人声”的最短持续时间是 150 毫秒。短于这个的统统忽略
默认值：250

VAD_MIN_SILENCE_MS = 300
在 Whisper 内部判断，如果这一段话里静音超过 300 毫秒，就强行把句子切开（生成多个 `seg`）
默认值：100

VAD_SPEECH_PAD_MS = 200
在检测到的人声片段前后，**额外保留 200 毫秒**的音频
防止 VAD 切得太干净，把字头字尾的轻微爆破音（如 p、t、k）给切丢了，导致识别缺字。保留一点上下文能让识别更准
默认值：400
'''

VAD_THRESHOLD = 0.5
VAD_MIN_SPEECH_MS = 150
VAD_MIN_SILENCE_MS = 300
VAD_SPEECH_PAD_MS = 600

# ================== 模型路径 ==================
print(f"加载识别模型: {MODEL_PATH}")
model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")

# ================== 全局音频缓冲区参数 ==================

buffer_lock = threading.Lock()
audio_buffer = np.empty((0,), dtype=np.float32)   # 音频块 float32
audio_buffer_time_ms = 0
silence_counter = 0.0
speech_length = 0.0
# 音量探测
volume_detected = False


# ================== 句子队列 ==================
translation_queue = queue.Queue(maxsize=50)



# ================== 结果 Class ==================
class TranResult:
    """
    存储单段语音识别结果，包含时间信息、原文及译文。

    该类主要用于在识别流水线中传递数据，便于后续的翻译或日志记录。

    Attributes:
        start:       语音的标准时间（毫秒）
        duration:    语音段落的时长（秒）
        original:    识别出的原始英文文本
        translation: 对应的中文翻译文本
        final:       该结果是否为最终信息
    """
    def __init__(self, start=0, duration="", original="", translation="", final=False):
        self.start = start
        self.duration = duration
        self.original = original
        self.translation = translation
        self.final = final




# ================== UDP 接收线程 ==================
def udp_receiver():
    """持续接收 UDP 音频流，转换为 mono float32 并追加到 buffer"""
    global audio_buffer, audio_buffer_time_ms, silence_counter, volume_detected, speech_length

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    # 加大接收缓冲区，防止丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, READABLE_BUFFER_SIZE)
    print(f"UDP 接收端启动，监听端口 {UDP_PORT}...")

    while True:
        try:
            # [0:8] 数据头部 8 字节为时间戳
            # [8:] CHUNK * CHANNELS * FORMAT （帧数块 * 通道数 * 采样点占用字节数）
            data, addr = sock.recvfrom(8 + CHUNK * CHANNELS * 2)
        except Exception as e:
            print(f"UDP 接收错误: {e}", file=sys.stderr)
            continue
        
        # 时间戳数据
        time_data = data[:8]
        timestamp_ms = int.from_bytes(time_data, 'big')

        # 音频数据
        audio_data = data[8:]
        # 将 bytes 转为 int16 numpy 数组 (shape: (CHUNK*CHANNELS,))
        audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
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
            duration_ms = int(len(audio_buffer) * 1000 // TARGET_SAMPLE_RATE)
            audio_buffer_time_ms = duration_ms + timestamp_ms
            audio_buffer = np.concatenate([audio_buffer, target_rate_mono])
            # 检测是否有声音
            if np.max(np.abs(target_rate_mono)) > SILENCE_THRESHOLD:
                volume_detected = True




# ================== 识别工作线程 ==================
def recognition_worker():
    global audio_buffer, audio_buffer_time_ms, silence_counter, volume_detected, speech_length
    while True:
        time.sleep(TIME_INFERENCE_INTERVAL)

        # ======= 提取当前缓存的音频数据 =======
        current_audio_buffer = None
        current_audio_buffer_timestamp_ms = 0
        with buffer_lock:
            if audio_buffer_time_ms == 0:
                continue
            if volume_detected:
                current_audio_buffer = audio_buffer.copy()
                current_audio_buffer_timestamp_ms = audio_buffer_time_ms
                audio_buffer_time_ms = 0
                audio_buffer = np.empty((0,), dtype=np.float32)
                volume_detected = False
            elif len(audio_buffer) >= MAX_SEGMENT_DURATION_SIZE:
                audio_buffer = np.empty((0,), dtype=np.float32)
        # 如果没有数据则跳过
        if current_audio_buffer is None:
            continue

        # ======= 推理提取的音频数据 =======

        # 记录音频实际时长（秒）
        timer_audio_duration = len(current_audio_buffer) / TARGET_SAMPLE_RATE
        
        # [计时器] 开始计时
        timer_start_time = time.perf_counter()

        # 推理
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
        except Exception as e:
            print(f"[识别错误] {e}", file=sys.stderr)
        
        # 整理推理结果
        segments_list = list(segments)
        segments_endi = len(segments_list) - 1
        split_time = -1
        for i, seg in enumerate(segments_list):
            text = seg.text.strip()
            
            if not text:
                continue

            # 如果句子结束离音频结束大于 2 秒才算正式句子
            tranResult = TranResult(
                start=current_audio_buffer_timestamp_ms + int(seg.start * 1000),
                duration = seg.end - seg.start,
                original = text,
                final = timer_audio_duration - seg.end > 2
            )

            print(f"{"●" if tranResult.final else "○"} No.{str(i+1)} | {seg.start:.2f}s -> {seg.end:.2f}s")
            print(f"[en] {tranResult.original}")

            if not tranResult.final and split_time == -1:
                split_time = seg.start

            # 提交翻译
            try:
                if tranResult.final:
                    translation_queue.put_nowait(tranResult)
            except queue.Full:
                print("队列满了！")

        
        ################ 如果最后一段是超长句则执行强制截断（直接结束抛弃缓存）
        # if i == segments_endi and tranResult.duration < MAX_SEGMENT_DURATION:

        if split_time != -1:
            # 如果非正式段存在前置无效音（前面有至少 1 秒），则进行剪裁  
            print(split_time)
            if split_time > 1:
                start_index = int(split_time * TARGET_SAMPLE_RATE)
                current_audio_buffer = current_audio_buffer[start_index:]

            with buffer_lock:
                audio_buffer = np.concatenate([current_audio_buffer, audio_buffer])
            

        # [计时器] 结束计时
        timer_end_time = time.perf_counter()
        timer_process_time = timer_end_time - timer_start_time
        rtf = timer_process_time / timer_audio_duration
        print(f"[性能] 音频长度: {timer_audio_duration:.2f}s | "
                f"推理耗时: {timer_process_time:.3f}s | RTF: {rtf:.2f} | "
                f"{'✅ 实时' if timer_process_time < TIME_INFERENCE_INTERVAL else '❌ 超时'}")




# ================== 翻译工作线程 ==================
# from translate import translate_text
# def translation_worker():
#     """从队列取出 TranResult 对象，调用翻译 API 并更新 translation 字段"""
#     while True:
#         try:
#             item: TranResult = translation_queue.get(timeout=1.0)
#         except queue.Empty:
#             continue

#         try:
#             translated = translate_text(item.original, "127.0.0.1:52208")
#             item.translation = translated
#             if translated:
#                 # 你可以在这里打印或通过其他方式输出译文
#                 print(f" - - - - - - ")
#                 print(f"[原文] {item.original}")
#                 print(f"[译文] {translated}")
#                 print(f" - - - - - - ")
#             else:
#                 # 可打印警告
#                 print(f"[译文] 翻译失败: {item.original}")
#         except Exception as e:
#             print(f"[翻译线程] 异常: {e}", file=sys.stderr)
#         finally:
#             translation_queue.task_done()


# ================== 启动线程 ==================
udp_thread = threading.Thread(target=udp_receiver, daemon=True)
udp_thread.start()

recog_thread = threading.Thread(target=recognition_worker, daemon=True)
recog_thread.start()

# trans_thread = threading.Thread(target=translation_worker, daemon=True)
# trans_thread.start()

print("实时语音识别已启动（从 UDP 接收音频流），按 Ctrl+C 停止...")
try:
    while True:
        time.sleep(0.5)
    # threading.Event().wait()
except KeyboardInterrupt:
    print("\n停止识别")
