from funasr import AutoModel

model = AutoModel(
    model="FunAudioLLM/Fun-ASR-Nano-2512",
    trust_remote_code=True,
    remote_code="./model.py",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    # device="cuda:0",
    device="cpu",
    hub="ms",
)

res = model.generate(input=["test.mp3"],
                    cache={}, batch_size=1,
                    hotwords=["keyword"], language="中文")
print(res)
print(res[0]["text"])        # recognized text with punctuation
print(res[0]["timestamps"])  # [{"token":"开","start_time":0.42,"end_time":0.48}, ...]