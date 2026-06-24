## 环境部署

### 安装 BlackHole
BlackHole 在旧系统无法完成编译只能直接安装 BlackHole2ch-0.6.1.pkg
安装包在官网的引导下去 Discord 下载
> ./BlackHole/BlackHole2ch-0.6.1.pkg 内可以直接安装


### 安装 SDL2

```shell
mkdir build
cd build
../configure
make -j
sudo make install
```

### 部署 python

```shell
cd source_macos_intel

# 建立一个专门存放环境的目录
mkdir -p venv

# 在那里创建你的 llama 环境
python3 -m venv ./venv
```



## 系统配置

### 创建多输出设备
直接在系统“声音”输出里选 **BlackHole 2ch** 会导致你自己听不到声音，因为声音全部被导入虚拟通道了。解决方法是创建一个“多输出设备”，让音频同时发送到你的**内置扬声器**和 **BlackHole 2ch**。

**操作步骤：**
1.  打开 **“音频 MIDI 设置”** (Audio MIDI Setup)。（在“应用程序/实用工具”里）
2.  点击左下角的 **“+”** 号 → 选择 **“创建多输出设备”**。
3.  在新建的设备上，**同时勾选** “**内置扬声器**（或你正在使用的输出设备）”和 “**BlackHole 2ch**”。
4.  在左侧设备列表里，右键点击这个新创建的“多输出设备”，选择“**将此设备用于声音输出**”，或者去“系统设置 → 声音 → 输出”里手动选中它。

现在，你的会议声音会同时传给你和 BlackHole。



## 使用

```shell
cd source_macos_intel
source ./venv/bin/activate
```

```shell
python 
```