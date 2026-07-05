import time
from funasr import AutoModel

model = AutoModel(
    model="./models/Fun-ASR-Nano-2512",
    trust_remote_code=True,
    remote_code="./Fun-ASR/model.py",
    vad_model="./models/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    vad_kwargs={
        "max_single_segment_time": 30000,
    },
    device="cpu"
)

# [计时器] 开始计时
timer_start_time = time.perf_counter()

res = model.generate(input=["test.mp3"],
                    cache={}, batch_size=1,
                    hotwords=["keyword"], language="auto")
# print(res)
print(res[0]["text"])        # recognized text with punctuation
print(res[0]["timestamps"])  # [{"token":"开","start_time":0.42,"end_time":0.48}, ...]

timer_end_time = time.perf_counter()
timer_process_time = timer_end_time - timer_start_time
# rtf = timer_process_time / timer_audio_duration
print(f"推理耗时: {timer_process_time:.3f}s")