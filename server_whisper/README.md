
## 使用

```shell
cd ~/LocalASR/server_whisper
source ./venv/bin/activate
```

```shell
tmux new-session -d -s llm '~/LocalASR/server_whisper/translator/llama_vulkan/llama-server -m ~/LocalASR/server_whisper/models/Qwen3-0.6B-GGUF/Qwen3-0.6B-Q4_K_M.gguf --host 0.0.0.0 --port 52208  -t 4 -ngl -1 --ctx-size 512 -lv 4'
```

```shell
~/LocalASR/server_whisper/translator/llama_vulkan/llama-server -m ~/LocalASR/server_whisper/models/Hy-MT2-1.8B-GGUF/Hy-MT2-1.8B-Q4_K_M.gguf --host 0.0.0.0 --port 52208 -t 4 -ngl -1 --ctx-size 512 -lv 4
```



## 部署

### 部署 Python 环境

安装 python3.12

```shell
cd ~/LocalASR/server_whisper

# 建立一个专门存放环境的目录
mkdir -p venv

# 在那里创建你的 llama 环境
python3 -m venv ./venv

source ./venv/bin/activate
```

### 安装组件

```shell
sudo apt update
sudo apt install -y libasound2-dev

pip install faster-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple

pip install pyalsaaudio modelscope soundfile librosa requests -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 部署 llama.cpp

```shell
mkdir -p ~/LocalASR/server_whisper/translator
```

```shell
cd ~/LocalASR/server_whisper/translator && wget https://github.com/ggml-org/llama.cpp/releases/download/b9843/llama-b9843-bin-ubuntu-vulkan-x64.tar.gz && tar -xzvf llama-b9843-bin-ubuntu-vulkan-x64.tar.gz && mv llama-b9843 llama_vulkan
```



### 下载模型

```shell
# 模型列表路径
tmp_path=~/LocalASR/server_whisper/models

modelscope download --model 'Systran/faster-whisper-medium' --local_dir "$tmp_path/faster-whisper-medium"

modelscope download --model 'Tencent-Hunyuan/Hy-MT2-1.8B-GGUF' --include '*Q4_K_M*' --local_dir "$tmp_path/Hy-MT2-1.8B-GGUF"
```

## 资料

### faster-whisper

https://github.com/SYSTRAN/faster-whisper

### 模型列表

https://www.modelscope.cn/collections/himyworld/faster-whisper

Size	Parameters	English-only	Multilingual
tiny	39 M	✓	✓
base	74 M	✓	✓
small	244 M	✓	✓
medium	769 M	✓	✓
large	1550 M	x	✓
large-v2	1550 M	x	✓

modelscope download --model 'Systran/faster-whisper-tiny.en' --local_dir "$tmp_path/faster-whisper-tiny.en"

modelscope download --model 'Systran/faster-whisper-base.en' --local_dir "$tmp_path/faster-whisper-base.en"


### 翻译模型

Tencent-Hunyuan/Hy-MT2-1.8B-GGUF
https://www.modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-GGUF/files

Tencent-Hunyuan/Hy-MT2-1.8B-1.25Bit-GGUF
暂不支持 vulkan 推理
https://www.modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-1.25Bit-GGUF/files

Tencent-Hunyuan/Hy-MT2-1.8B-2Bit-GGUF
暂不支持 vulkan 推理
https://www.modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-2Bit-GGUF

关键词使用参考：
https://www.modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-2Bit-GGUF