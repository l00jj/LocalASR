
### 部署 Python 环境

安装 python3.12

```shell
cd server_linux

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

pip install pyalsaaudio modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
```


### 下载模型


```shell
# 模型列表路径
tmp_path=~/LocalASR/server_linux/models

modelscope download --model 'Systran/faster-whisper-tiny.en' --local_dir "$tmp_path/faster-whisper-tiny.en"
```


### 使用

```shell
cd server_linux
source ./venv/bin/activate
```
