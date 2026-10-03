# lecturedub

把一节英文课做成时间轴对齐的中文配音视频。识别、翻译、配音都在你自己的电脑上完成，视频不会上传。

Apple Silicon 用 MLX。Windows 和 Linux 用 NVIDIA 显卡的 CUDA。

Drop in an English lecture, or paste a link. The picture stays as it was. The English soundtrack is replaced with Chinese speech that follows the original timestamps, and the file gets Chinese and English subtitles.

## 做完你会拿到什么

一节课会得到三个文件：

- 一个 MP4。画面是原来的，没有重新压缩。音轨换成中文。
- 一条软字幕，播放器里打开就能看到。每一条上面是中文，下面是英文。
- 旁边两个字幕文件：`.zh.srt` 和 `.en.srt`。

原视频有多长，新视频就有多长。句子按原来的时间点开始。两句之间的空隙保持安静。如果中文比这个空隙长，最多加速到 1.16 倍，再长的部分会被截掉，所以翻译时会尽量把句子写成塞得进这个空隙的长度。

## 哪些电脑能跑

可以：

- 2020 年及以后的 Apple Silicon Mac（M1、M2、M3、M4）。终端里 `uname -m` 应显示 `arm64`。
- Windows 10/11，带 NVIDIA 显卡，驱动是新的。
- Linux，带 NVIDIA 显卡，驱动是新的。

不可以：

- Intel Mac。MLX 不用 Intel 核显，这台机器上也没有 CUDA。
- 只有 AMD 显卡、核显，或者没有独显的 Windows / Linux。这个项目的 NVIDIA 路径只认 CUDA。

内存建议 16 GB 或更多。16 GB 的机器一次只配一节，不要同时再开别的大模型。NVIDIA 显存不到 18 GB 时，翻译模型会自动用 4-bit，安装包里已经带了 `bitsandbytes`。

磁盘请至少留出 25 GB。模型第一次运行才下载，识别、翻译、配音三个模型加起来大约是这个量级，成片本身还要另占空间。

## 开始之前

三样东西：Python 3.11 或更新、ffmpeg、以及上面说的 GPU。

### Mac

1. 安装 [Homebrew](https://brew.sh)。
2. 安装依赖：

```bash
brew install python@3.12 ffmpeg
```

3. 确认芯片：

```bash
uname -m
python3 --version
ffmpeg -version
```

`uname -m` 必须是 `arm64`。`python3 --version` 必须是 3.11 或更高。

### Windows

1. 从 [python.org](https://www.python.org/downloads/windows/) 安装 Python 3.11 或 3.12。安装时勾选 **Add python.exe to PATH**。
2. 安装 ffmpeg。在 PowerShell 里：

```powershell
winget install Gyan.FFmpeg
```

装完后关掉终端再开一个，让 PATH 生效。然后：

```powershell
python --version
ffmpeg -version
nvidia-smi
```

`nvidia-smi` 能打出显卡名字和驱动版本，才说明 NVIDIA 驱动是好的。看不到这个命令，就先去 NVIDIA 官网装当前的 Game Ready 或 Studio 驱动，不要只装 CUDA Toolkit 而没有驱动。

PyTorch 的 CUDA 版本会在后面的 `pip install` 里装上，一般不用单独装 CUDA Toolkit。

### Linux

Debian / Ubuntu：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
python3 --version
ffmpeg -version
nvidia-smi
```

`nvidia-smi` 必须能看到显卡。看不到就先装 NVIDIA 驱动，再继续。

## 安装

```bash
git clone https://github.com/asher0913/lecturedub.git
cd lecturedub
```

Mac 和 Linux：

```bash
./install.sh
```

Windows PowerShell，在克隆下来的目录里：

```powershell
.\install.ps1
```

脚本会做这些事：

1. 检查系统和 Python 版本。
2. 检查 ffmpeg 在不在。
3. 在项目里建一个 `.venv`。
4. Apple Silicon 安装 MLX 那一套，并在“应用程序”里放一个 **LectureDub**。
5. Windows 和 Linux 安装 NVIDIA 那一套。
6. 跑一遍 `lecturedub doctor`，把结果打印出来。

不想用脚本时，自己装：

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip

# 三选一
pip install -e ".[apple,desktop]"    # Apple Silicon
pip install -e ".[nvidia,desktop]"   # Windows / Linux + NVIDIA

lecturedub doctor
```

Mac 上还可以把图标装进应用程序文件夹：

```bash
lecturedub install-app
```

只想用浏览器、不装桌面窗口时，把上面的 `desktop` 去掉。之后用 `lecturedub app --browser`。

从 GitHub 直接装、不克隆仓库：

```bash
pip install "lecturedub[apple,desktop] @ git+https://github.com/asher0913/lecturedub.git"
# 或者
pip install "lecturedub[nvidia,desktop] @ git+https://github.com/asher0913/lecturedub.git"
```

## 确认装好了

```bash
lecturedub doctor
```

正常的 Mac 会看到类似：

```text
models: Apple Silicon, MLX
ffmpeg: /opt/homebrew/bin/ffmpeg
window: pywebview ...
```

正常的 NVIDIA 机器会看到显卡名字，例如 `models: NVIDIA GeForce RTX 4070`。

下面任何一行出现，就先别开始配音：

| 打印出来的话 | 怎么处理 |
| --- | --- |
| `ffmpeg: missing` | 按上面的办法安装 ffmpeg，重开终端，再跑 doctor |
| `NVIDIA extra is missing` | `pip install -e ".[nvidia,desktop]"` |
| `no NVIDIA GPU with CUDA` | 驱动没装好，或装成了 CPU 版 PyTorch。先让 `nvidia-smi` 成功，再重装 `lecturedub[nvidia]` |
| `Intel Macs are not supported` | 换 Apple Silicon，或换一台有 NVIDIA 显卡的电脑 |

## 打开程序

Mac：打开“应用程序”里的 **LectureDub**。如果系统提示无法验证开发者，按住 Control 点图标，选“打开”。

命令行，三种开法是同一个界面：

```bash
lecturedub app
lecturedub app --browser
lecturedub ui
```

- `lecturedub app` 开一个桌面窗口。需要安装时带上 `desktop`（也就是 pywebview）。
- `lecturedub app --browser` 用系统浏览器打开。
- `lecturedub ui` 只在本机启动网页，不自动打开。地址是 `http://127.0.0.1:7860`。7860 被占用时会自动往后试端口，以终端里打印的地址为准。

窗口只监听本机，别的电脑访问不到。

## 用窗口配一节课

1. 把视频拖进虚线框。支持常见的 mp4、mkv、webm、mov。
2. 如果你已经有英文字幕，把 `.srt` 或 `.vtt` 一起拖进去。有字幕就不再做语音识别，更快，也更不容易听错。
3. 没有本地文件的话，把视频的 http(s) 链接贴到“视频链接”。直链，或者 yt-dlp 能解析的页面链接，都可以。
4. 选声音。讲课默认用 **Uncle Fu**，偏低的男声。Serena 是温和女声，Vivian 是明亮女声。
5. 点“开始配音”。
6. 进度会显示“正在转录 / 正在翻译 / 正在配音”，以及做到第几句。
7. 完成后点“下载视频”“中文字幕”“英文字幕”。Mac 上还可以点“在 Finder 中显示”。

第一次会从 Hugging Face 下载模型，这一步只发生一次，之后用的是本机缓存。一节 80 分钟左右的课，在 16 GB 的 Mac 上通常要几十分钟到一个多小时，主要花在逐句配音上。请让窗口开着，不要让电脑睡眠。

下载很慢时，可以在启动前指定镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com   # Windows PowerShell: $env:HF_ENDPOINT="https://hf-mirror.com"
lecturedub app
```

窗口产生的文件在：

- Mac：`~/Library/Application Support/LectureDub/jobs/`
- Windows 和 Linux：`~/.lecturedub/jobs/`

每一节一个文件夹，成片在里面的 `out/video/dubbed.mp4`，字幕是同目录的 `dubbed.zh.srt` 和 `dubbed.en.srt`。

## 用命令行配一节课

在已经激活的虚拟环境里，或者直接用项目里的解释器：`.venv/bin/lecturedub`（Windows 是 `.venv\Scripts\lecturedub`）。

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4
lecturedub run lecture.mp4 --srt lecture.en.srt -o lecture-zh.mp4
lecturedub run "https://example.com/lecture.mp4" -o lecture-zh.mp4
lecturedub run lecture.mp4 -o lecture-zh.mp4 --voice Serena
```

`-o` 是最终的 MP4 路径。中英文字幕会写在这个文件同级的 `video/` 目录里，文件名是你指定的主文件名，扩展名分别是 `.zh.srt` 和 `.en.srt`。例如 `-o ~/Desktop/lecture-zh.mp4` 时，字幕在 `~/Desktop/video/`。

中间文件默认在当前目录的 `work/jobs/`。换地方：

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4 --work /tmp/lecturedub-work
```

`--title` 只影响识别时给模型的课程提示。标题里出现 511、Snowflake、Kafka 这类词时，会用数据管理课的术语表；否则用分布式系统的术语表。你已经有可靠的英文字幕时，这个提示用不上。

## 一次配好几节

准备一个 JSON 列表：

```json
[
  {"title": "Lecture 1", "video": "lecture.mp4", "srt": "lecture.en.srt"},
  {"title": "Lecture 2", "video": "https://example.com/lecture.mp4"}
]
```

`video` 和 `srt` 可以是本地路径，也可以是 http(s) 链接。仓库里有一份例子：`examples/batch.example.json`。

```bash
lecturedub batch examples/batch.example.json --output-dir output
```

成片在 `output/<课程或 video>/<标题>.mp4`。只处理标题里带某个词的条目：

```bash
lecturedub batch manifest.json --output-dir output --only "Lecture 1"
```

先只下载、不跑模型：

```bash
lecturedub fetch manifest.json --work-dir work/lectures --output-dir output
```

只翻译、不配音：

```bash
lecturedub batch manifest.json --output-dir output --translate-only
```

配音已经生成、只差封装：

```bash
lecturedub mux manifest.json --output-dir output --work-dir work/lectures
```

`--pilot-seconds 60` 只配第一节匹配到的课的前 60 秒，用来试声音和术语，不会当成整节课的成片。

批量任务是一节接一节做的。16 GB 内存不要自己再开第二个配音进程。

## 声音

| 名字 | 听感 |
| --- | --- |
| `Uncle_Fu` | 偏低的男声，默认，适合讲课 |
| `Serena` | 温和女声 |
| `Vivian` | 明亮女声 |

窗口里可以直接选。命令行用 `--voice`。

## 模型

三个阶段都是 Qwen3。Apple Silicon 用 MLX 格式，NVIDIA 用 PyTorch 格式。权重都从 Hugging Face 下载到本机缓存，默认在 `~/.cache/huggingface`。

| 阶段 | Apple Silicon | NVIDIA | 环境变量 |
| --- | --- | --- | --- |
| 语音识别 | `Qwen/Qwen3-ASR-1.7B` | 同一个模型，再加 `Qwen/Qwen3-ForcedAligner-0.6B` 用来打时间戳 | `LECTUREDUB_ASR` |
| 翻译成口语中文 | `mlx-community/Qwen3-8B-4bit` | `Qwen/Qwen3-8B`。显存不到 18 GB 时自动 4-bit | `LECTUREDUB_LLM` |
| 中文配音 | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `LECTUREDUB_TTS` |

一般不用改。要指定 GPU 或强制某条路径：

```bash
export LECTUREDUB_BACKEND=cuda          # 或 mlx
export LECTUREDUB_CUDA_DEVICE=cuda:0    # 多卡时换 cuda:1
export LECTUREDUB_LLM=Qwen/Qwen3-8B
```

有英文字幕时会跳过识别。没有字幕时，NVIDIA 上的识别会按官方接口把长音频切开并对齐时间戳，再写成 SRT。

## 处理顺序

1. 读取本地视频，或者用 yt-dlp 下载链接。
2. 有字幕就解析 `.srt` / `.vtt`。没有就用 Qwen3-ASR 听写成带时间的英文。
3. Qwen3 先按上下文改听写错误，再写成能直接念的简体中文。不添加原句没有的内容。
4. Qwen3-TTS 逐句念出来，放到原来的开始时间上。
5. 用 ffmpeg 把原视频画面原样拷进新文件，音轨换成 AAC 的中文，并写入一条中英字幕。

画面不会转成别的编码，所以这一步很快，清晰度和原片一样。

## 常见问题

**窗口开了但一直停在排队。**  
看终端。第一次是在下载模型。下载完会进入转录、翻译或配音。

**配音中途电脑风扇很大，内存告急。**  
关掉浏览器里别的大页面，不要同时跑第二个 `lecturedub`。16 GB 机器只留一个配音进程。

**提示找不到 ffmpeg。**  
从应用程序或 Finder 打开时，PATH 里可能没有 Homebrew。doctor 能找到 `/opt/homebrew/bin/ffmpeg` 就可以。还是失败的话，用终端里的 `lecturedub app` 启动。

**NVIDIA 上报显存不够。**  
翻译会在显存小于 18 GB 时用 4-bit。如果报错说缺少 bitsandbytes，重新执行 `pip install -e ".[nvidia,desktop]"`。不要在配音的同时再加载别的大模型。

**成片没有声音或没有字幕。**  
用支持软字幕的播放器，例如 VLC 或 IINA，并在菜单里打开字幕轨“中英字幕”。`.zh.srt` 和 `.en.srt` 也可以手动挂上去。

**句子结尾被截掉。**  
中文比原句的时间长，加速到 1.16 倍仍然超时，多出来的尾部不会念出来。把对应中文写短，或给这句话留更长的时间，再重跑这一节。已经合成过的句子会按文本做缓存；改了中文才会重念那一句。

**Mac 说应用已损坏或无法打开。**  
Control-点击 LectureDub，选择“打开”。这是本机生成的应用，没有苹果公证。

## 隐私

语音识别、翻译、语音合成都不经过这个项目的服务器。视频只留在你指定的目录，或上面的应用数据目录。`work/`、`output/`、模型缓存和虚拟环境不会被 git 跟踪。

## 开发和测试

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[apple,desktop,dev]"    # NVIDIA 机器把 apple 换成 nvidia
python -m pytest
```

测试不下载模型，也不需要显卡，只检查字幕解析、时间轴分组，以及 Apple / NVIDIA 两条路径有没有选对。

许可是 MIT。版权归 Yixuan Zhang。

## English

LectureDub replaces an English lecture soundtrack with timed Mandarin and writes bilingual subtitles. The picture is copied, not re-encoded. Nothing is uploaded.

You need Python 3.11+, ffmpeg, and either an Apple Silicon Mac or an NVIDIA GPU on Windows or Linux. Intel Macs and machines without CUDA are not supported. Plan on 16 GB of memory and about 25 GB of free disk. On a 16 GB machine, dub one lecture at a time.

Install ffmpeg first (`brew install ffmpeg`, `winget install Gyan.FFmpeg`, or `sudo apt install ffmpeg`). On NVIDIA, `nvidia-smi` must work before you continue.

```bash
git clone https://github.com/asher0913/lecturedub.git
cd lecturedub
./install.sh          # macOS and Linux
```

```powershell
.\install.ps1         # Windows
```

Or, in a virtualenv:

```bash
pip install -e ".[apple,desktop]"     # Apple Silicon
pip install -e ".[nvidia,desktop]"    # NVIDIA
lecturedub doctor
lecturedub app
```

`lecturedub doctor` should report `Apple Silicon, MLX` or `NVIDIA <your gpu name>`, plus ffmpeg. `lecturedub app` opens a window. `lecturedub app --browser` uses your browser. `lecturedub ui` only prints a local URL, `http://127.0.0.1:7860` unless that port is taken.

In the window, drop a video and an optional English `.srt` or `.vtt`, or paste an http(s) link. Pick a voice. The first run downloads the Qwen3 models from Hugging Face. Set `HF_ENDPOINT` if you need a mirror. Finished app jobs are under `~/Library/Application Support/LectureDub/jobs` on a Mac and `~/.lecturedub/jobs` elsewhere.

Command line:

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4
lecturedub run lecture.mp4 --srt lecture.en.srt -o lecture-zh.mp4 --voice Serena
lecturedub batch examples/batch.example.json --output-dir output
```

The MP4 is written to `-o`. The `.zh.srt` and `.en.srt` files are written in a `video/` directory next to it. Batch items are a JSON list of `{"title", "video", "srt"}`. `lecturedub fetch` only downloads. `lecturedub batch --translate-only` stops after the Chinese script. `lecturedub mux` packs a dub that is already on disk.

Voices: `Uncle_Fu` (default, low male), `Serena`, `Vivian`.

Models, with overrides:

| Stage | Apple Silicon | NVIDIA | Variable |
| --- | --- | --- | --- |
| ASR | `Qwen/Qwen3-ASR-1.7B` | same, plus `Qwen/Qwen3-ForcedAligner-0.6B` | `LECTUREDUB_ASR` |
| Translation | `mlx-community/Qwen3-8B-4bit` | `Qwen/Qwen3-8B` (4-bit below 18 GB) | `LECTUREDUB_LLM` |
| Speech | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `LECTUREDUB_TTS` |

`LECTUREDUB_BACKEND` is `mlx` or `cuda`. `LECTUREDUB_CUDA_DEVICE` defaults to `cuda:0`.

A line that is still too long after a 1.16× speedup is cut off at the slot boundary. Shorten that Chinese line and run the lecture again. Only changed lines are synthesized again.

Tests, without downloading models:

```bash
pip install -e ".[apple,desktop,dev]"   # or nvidia
python -m pytest
```

MIT License. Copyright Yixuan Zhang.
