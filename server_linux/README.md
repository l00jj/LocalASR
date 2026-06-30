
## 使用

```shell
cd ~/LocalASR/server_linux
source ./venv/bin/activate
```

```shell
tmux new-session -d -s llm '~/LocalASR/server_linux/translator/llama_vulkan/llama-server -m ~/LocalASR/server_linux/models/Qwen3-0.6B-GGUF/Qwen3-0.6B-Q4_K_M.gguf --host 0.0.0.0 --port 52208  -t 4 -ngl -1 --ctx-size 512 -lv 4'
```




## 部署

### 部署 Python 环境

安装 python3.12

```shell
cd ~/LocalASR/server_linux

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

pip install pyalsaaudio modelscope soundfile librosa requests -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 部署 llama.cpp

```shell
mkdir -p ~/LocalASR/server_linux/translator
```

```shell
cd ~/LocalASR/server_linux/translator && wget https://github.com/ggml-org/llama.cpp/releases/download/b9843/llama-b9843-bin-ubuntu-vulkan-x64.tar.gz && tar -xzvf llama-b9843-bin-ubuntu-vulkan-x64.tar.gz && mv llama-b9843 llama_vulkan
```



### 下载模型

```shell
# 模型列表路径
tmp_path=~/LocalASR/server_linux/models

modelscope download --model 'Systran/faster-whisper-tiny.en' --local_dir "$tmp_path/faster-whisper-tiny.en"

modelscope download --model 'Systran/faster-whisper-base.en' --local_dir "$tmp_path/faster-whisper-base.en"

modelscope download --model 'unsloth/Qwen3-0.6B-GGUF' --include '*Q4_K_M*' --local_dir "$tmp_path/Qwen3-0.6B-GGUF"
```

