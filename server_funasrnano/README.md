
## 使用

内存需求
Fun-ASR-Nano-2512 | 10G

```shell
cd ~/LocalASR/server_funasrnano
source ./venv/bin/activate
```




## 部署

### 部署 Python 环境

安装 python3.12

```shell
cd ~/LocalASR/server_funasrnano

# 建立一个专门存放环境的目录
mkdir -p venv

# 在那里创建你的 llama 环境
python3 -m venv ./venv

source ./venv/bin/activate
```

### 安装组件

```shell
sudo apt update
# sudo apt install -y libasound2-dev
sudo apt install -y ffmpeg

# 安装 FunASR
pip install git+https://github.com/modelscope/FunASR.git@f9937385517cccaa8cd780b61c8b404c701c1d44

git clone https://github.com/FunAudioLLM/Fun-ASR.git@4492da201a440131104b6290ba094b87489dda6a

# 安装必要库
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 其他工具
pip install modelscope requests -i https://pypi.tuna.tsinghua.edu.cn/simple

```





### 下载模型

```shell
# 模型列表路径
tmp_path=~/LocalASR/server_funasr/models

modelscope download --model 'FunAudioLLM/Fun-ASR-Nano-2512' --local_dir "$tmp_path/Fun-ASR-Nano-2512"

modelscope download --model 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch' --local_dir "$tmp_path/speech_fsmn_vad_zh-cn-16k-common-pytorch"

modelscope download --model 'Tencent-Hunyuan/Hy-MT2-1.8B-GGUF' --include '*Q4_K_M*' --local_dir "$tmp_path/Hy-MT2-1.8B-GGUF"
```




