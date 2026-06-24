### 安装 BlackHole
BlackHole 在旧系统无法完成编译只能直接安装 BlackHole2ch-0.6.1.pkg
安装包在官网的引导下去 Discord 下载


### 安装 SDL2

```shell
mkdir build
cd build
../configure
make -j
sudo make install
```


### 安装 whisper.cpp

旧 macbook BigSur 环境下无法编译 Metal 需要 OFF 掉
（可选）需要 SDL2 的声音流支持 cmake -B build -DWHISPER_SDL2=ON

```shell
cd /Volumes/Room/rtt-app/whisper.cpp/whisper.cpp-master
rm -rf build
cmake -B build -DGGML_METAL=OFF &&
cmake --build build --config Release
```



### python

```shell
cd /Volumes/Room/rtt-app

# 创建虚拟环境目录
python3 -m venv python_env

# 激活虚拟环境
source python_env/bin/activate

# 安装依赖（只需 sounddevice）
pip install faster-whisper argostranslate sounddevice soundfile scipy numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

pip install sentencepiece --no-binary sentencepiece -i https://pypi.tuna.tsinghua.edu.cn/simple


python -m argostranslate.package install-package translate-en_zh
```


```shell
python3 run_live.py
```


modelscope download \
	--model "unsloth/Qwen3-0.6B-GGUF" \
	--include "*IQ4_NL*" \
	--local_dir ~/Qwen3-0.6B-GGUF

llama.cpp  Qwen3-0.6B-GGUF  unsloth-Qwen3-VL-4B-Instruct-GGUF  venv
(llm-env) root@localhost:~# ls Qwen3-0.6B-GGUF
Qwen3-0.6B-IQ4_NL.gguf

llama-server \
  -m ~/Qwen3-0.6B-GGUF/Qwen3-0.6B-IQ4_NL.gguf \
  --host 127.0.0.1 --port 8080 \
  -ngl 0 -t 2 \
  --ctx-size 512


### ⚙️ 关键的下一步：创建“多输出设备”
直接在系统“声音”输出里选 **BlackHole 2ch** 会导致你自己听不到声音，因为声音全部被导入虚拟通道了。解决方法是创建一个“多输出设备”，让音频同时发送到你的**内置扬声器**和 **BlackHole 2ch**。

**操作步骤：**
1.  打开 **“音频 MIDI 设置”** (Audio MIDI Setup)。（在“应用程序/实用工具”里）
2.  点击左下角的 **“+”** 号 → 选择 **“创建多输出设备”**。
3.  在新建的设备上，**同时勾选** “**内置扬声器**（或你正在使用的输出设备）”和 “**BlackHole 2ch**”。
4.  在左侧设备列表里，右键点击这个新创建的“多输出设备”，选择“**将此设备用于声音输出**”，或者去“系统设置 → 声音 → 输出”里手动选中它。

现在，你的会议声音会同时传给你和 BlackHole。

### 🎤 在 whisper.cpp 中使用 BlackHole
配置好后，你的实时转录工具就可以从 BlackHole 捕获音频了。你只需在运行命令时指定这个虚拟设备。

首先查找 BlackHole 的设备编号：
```bash
./stream -l en --list-devices
```
你会看到设备列表，找到类似 `BlackHole 2ch` 的设备，记下它前面的编号（比如 `2`）。

然后运行实时识别命令，**加上 `-c` 参数来指定设备编号**：
```bash
./stream -m ./models/ggml-tiny.en-q8_0.bin -t 4 -l en -c 2
```
（将 `-c 2` 替换成你查到的真实编号）

### 🔍 如何验证？
随便在电脑上播放一个英文视频或音频，终端里应该会**实时滚动**出识别的英文文本。如果你同时能听到声音，就说明一切配置正确。

### 💡 万一听不到声音？
*   **检查主音频输出**：确认“系统设置 → 声音 → 输出”中选中的是“多输出设备”。
*   **检查采样率**：在“音频 MIDI 设置”中，确保“内置扬声器”和“BlackHole 2ch”的**采样率设置一致**（通常都设为 48kHz）。

这样，你的旧款 Mac 就完美变身成了一台本地离线会议翻译机。如果后续想加入翻译环节，可以随时再问我～