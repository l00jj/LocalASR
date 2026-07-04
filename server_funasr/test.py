from funasr import AutoModel

model = AutoModel(
    model="./models/Fun-ASR-Nano-2512",
    trust_remote_code=True,
    remote_code="./model.py",
    vad_model="fsmn-vad",
    vad_kwargs={
        "max_single_segment_time": 30000,
    },
    # device="cuda:0",
    # punc_model="ct-punc",              # 没有用
    device="cpu",
    hub="ms",
)

res = model.generate(input=["test.mp3"],
                    cache={}, batch_size=1,
                    hotwords=["keyword"], language="auto")
# print(res)
print(res[0]["text"])        # recognized text with punctuation
print(res[0]["timestamps"])  # [{"token":"开","start_time":0.42,"end_time":0.48}, ...]