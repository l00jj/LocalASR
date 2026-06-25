
### 部署 python

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
```



## 使用

```shell
cd server_linux
source ./venv/bin/activate
```
