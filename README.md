### 网络配置

```shell
git config --global http.proxy http://127.0.0.1:7897 && git config --global https.proxy http://127.0.0.1:7897
```

```shell
git remote -v
git remote set-url origin https://github.com/l00jj/LocalASR.git
```

```shell
# 账号密码缓存一天
git config --global credential.helper 'cache --timeout=86400'

# 取消代理
git config --global --unset http.proxy && git config --global --unset https.proxy
```



## 资料



### ASR FunAudioLLM/Fun-ASR-Nano-2512
https://www.modelscope.cn/models/FunAudioLLM/Fun-ASR-Nano-2512
轻量多语言 ASR，31 languages

### ASR Qwen/Qwen3-ASR-1.7B
https://www.modelscope.cn/models/Qwen/Qwen3-ASR-1.7B
当前效果最佳的 ASR

### 翻译模型 Hy-MT2-1.8B
https://www.modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-GGUF/files

### 字幕时间轴对齐模型 Qwen3-ForcedAligner-0.6B
https://www.modelscope.cn/models/Qwen/Qwen3-ForcedAligner-0.6B
将音频与文字一并输入，返回文字对齐到音频的时间轴