
## 使用

```shell
cd ~/LocalASR/server_funasr
source ./venv/bin/activate
```




## 部署

### 部署 Python 环境

安装 python3.12

```shell
cd ~/LocalASR/server_funasr

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

# 安装 FunASR
pip install git+https://github.com/modelscope/FunASR.git@f9937385517cccaa8cd780b61c8b404c701c1d44

# 安装必要库
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 其他工具
pip install modelscope requests -i https://pypi.tuna.tsinghua.edu.cn/simple
```



