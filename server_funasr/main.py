import os
import numpy as np
import librosa
import threading
import sys
import time
import socket
import queue
from funasr import AutoModel
# import soundfile as sf

# ================== 音频参数（与发送端一致） ==================
SOURCE_SAMPLE_RATE = 44100          # 必须与发送端一致
CHANNELS = 2
CHUNK = 1024                        # 每包帧数
FORMAT = 'int16'                    # 发送端使用 int16


# ================== 音频输入 FunASR 模型参数 ==================
TARGET_SAMPLE_RATE = 16000


# ================== UDP 接收配置 ==================
UDP_PORT = 52210                    # 与发送端目标端口一致
READABLE_BUFFER_SIZE = 5 * 1024 * 1024  # 5M 缓存


# ================== 推理参数 ==================
TIME_INFERENCE_INTERVAL = 1           # 推理间隔 (秒)
SILENCE_THRESHOLD = 0.01              # 静音判定阈值
# 最大音频缓冲时间（累计判断是一句话未中断或持续无声音）
MAX_SEGMENT_DURATION = 36.0
MAX_SEGMENT_DURATION_SIZE = MAX_SEGMENT_DURATION * TARGET_SAMPLE_RATE


# ================== 全局音频缓冲区参数 ==================
audio_buffer = np.empty((0,), dtype=np.float32)   # mono float32
buffer_lock = threading.Lock()
silence_counter = 0.0
speech_length = 0.0
# 音量探测
volume_detected = False


END_PUNCTUATION = {'。', '！', '？', '.', '!', '?'}


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
    def __init__(self, duration=0, original="", translation="", final=False):
        self.start = 0
        self.duration = duration
        self.original = original
        self.translation = translation
        self.final = final



# ================== UDP 接收线程 ==================
def udp_receiver():
    """持续接收 UDP 音频流，转换为 mono float32 并追加到 buffer"""
    global audio_buffer, silence_counter, volume_detected, speech_length

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    # 加大接收缓冲区，防止丢包
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, READABLE_BUFFER_SIZE)
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
            if np.max(np.abs(target_rate_mono)) > SILENCE_THRESHOLD:
                volume_detected = True

# ================== 识别工作线程 ==================
def recognition_worker():
    global audio_buffer, silence_counter, volume_detected, speech_length

    model = AutoModel(
        model="./models/Fun-ASR-Nano-2512",
        trust_remote_code=True,
        remote_code="./Fun-ASR/model.py",
        vad_model="./models/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        vad_kwargs={ "max_single_segment_time": 30000 },
        log_level="WARNING",              # 只显示警告和错误信息
        ncpu=8,                           # 设置使用线程，默认是 4
        device="cpu"
    )


    while True:
        time.sleep(TIME_INFERENCE_INTERVAL)

        # ======= 提取当前缓存的音频数据 =======
        current_audio_buffer = None
        with buffer_lock:
            if volume_detected:
                current_audio_buffer = audio_buffer.copy()
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
            segments = model.generate(input=[current_audio_buffer],
                    cache={}, batch_size=1,
                    hotwords=["keyword"], language="auto")
        except Exception as e:
            print(f"[识别错误] {e}", file=sys.stderr)

        print(segments)
        if "timestamps" in segments[0]:

            ishead = True
            start_time = 0
            end_time = 0
            tranResult = TranResult()
            for item in segments[0]["timestamps"]:
                token = item["token"]

                # 定义句子节点初始信息
                if ishead:
                    ishead = False
                    start_time = item["start_time"]
                    tranResult.duration = 0
                    tranResult.original = ""
                    
                # 累计句子信息
                end_time = item["end_time"]
                tranResult.duration = end_time - start_time
                tranResult.original += token

                # 判断句子是否结尾
                if token.rstrip()[-1] in END_PUNCTUATION:
                    tranResult.final = True
                    # 提交翻译
                    try:
                        translation_queue.put_nowait(tranResult)
                    except queue.Full:
                        print("队列满了！")
                    # 重置节点
                    ishead = True
                    tranResult = TranResult()

            # 如果最后一段是超长句则执行强制截断（直接结束抛弃缓存）
            # if i == segments_endi and tranResult.duration < MAX_SEGMENT_DURATION:
            if not ishead:
                print(tranResult.original)
                # 如果最后一段存在前置无效音（前面有至少 1 秒），则进行剪裁
                if start_time > 1:
                    start_index = int(start_time * TARGET_SAMPLE_RATE)
                    current_audio_buffer = current_audio_buffer[start_index:]
                # 如果最后句子尾部离音频结束小于 2 秒，则定为不完整句式 final=False，回存到缓存头部
                # 反之则可以认为是完全句式，尾部存在无可检测音频则可以抛弃当前数据，记录为正式句子
                if timer_audio_duration - end_time < 2:
                    volume_detected = True
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
def translation_worker():
    """从队列取出 TranResult 对象，调用翻译 API 并更新 translation 字段"""
    while True:
        try:
            item: TranResult = translation_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        try:
            print(f"[原文] {item.original}")
        #     translated = translate_text(item.original, "127.0.0.1:52208")
        #     item.translation = translated
        #     if translated:
        #         # 你可以在这里打印或通过其他方式输出译文
        #         print(f" - - - - - - ")
        #         print(f"[原文] {item.original}")
        #         print(f"[译文] {translated}")
        #         print(f" - - - - - - ")
        #     else:
        #         # 可打印警告
        #         print(f"[译文] 翻译失败: {item.original}")
        except Exception as e:
            print(f"[翻译线程] 异常: {e}", file=sys.stderr)
        finally:
            translation_queue.task_done()


# ================== 启动线程 ==================
udp_thread = threading.Thread(target=udp_receiver, daemon=True)
udp_thread.start()

recog_thread = threading.Thread(target=recognition_worker, daemon=True)
recog_thread.start()

trans_thread = threading.Thread(target=translation_worker, daemon=True)
trans_thread.start()

print("实时语音识别已启动（从 UDP 接收音频流），按 Ctrl+C 停止...")
try:
    while True:
        time.sleep(0.5)
    # threading.Event().wait()
except KeyboardInterrupt:
    print("\n停止识别")
