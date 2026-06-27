`Segment` 是一个数据类，包含以下字段： [1](#0-0) 

## Segment 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 段的唯一标识符 |
| `seek` | int | 在音频特征中的搜索位置 |
| `start` | float | 段的开始时间（秒） |
| `end` | float | 段的结束时间（秒） |
| `text` | str | 转录的文本内容 |
| `tokens` | List[int] | 对应的 token ID 列表 |
| `avg_logprob` | float | 平均对数概率（置信度指标） |
| `compression_ratio` | float | 压缩比（用于检测重复输出） |
| `no_speech_prob` | float | 无语音概率 |
| `words` | Optional[List[Word]] | 词级时间戳列表（当 `word_timestamps=True` 时） |
| `temperature` | Optional[float] | 生成时使用的温度值 |

## 使用示例

```python
segments, info = model.transcribe("audio.mp3", word_timestamps=True)

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    print(f"  Confidence: {segment.avg_logprob}")
    if segment.words:
        for word in segment.words:
            print(f"  [{word.start:.2f}s -> {word.end:.2f}s] {word.word}")
```

## Notes

- `words` 字段仅在启用 `word_timestamps=True` 时才有值，否则为 `None`
- `temperature` 字段在 `WhisperModel` 中会记录实际使用的温度值，而在 `BatchedInferencePipeline` 中固定为第一个温度值
- `Segment` 对象由 `generate_segments()` 方法在 `WhisperModel` 中生成，或由 `_batched_segments_generator()` 在 `BatchedInferencePipeline` 中生成

Wiki pages you might want to explore:
- [WhisperModel (SYSTRAN/faster-whisper)](/wiki/SYSTRAN/faster-whisper#4.1)

### Citations

**File:** faster_whisper/transcribe.py (L47-60)
```python
@dataclass
class Segment:
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: List[int]
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: Optional[List[Word]]
    temperature: Optional[float]

```
