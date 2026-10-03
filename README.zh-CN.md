# lecturedub

[English](README.md) | **简体中文**

GitHub 默认打开英文页。这一页是同一份说明的中文。点上面的 **English** 可以回到英文。

LectureDub 在你自己的电脑上把一节英文课做成中文配音视频。画面从你给出的文件原样拷贝。英文音轨换成普通话，每一句从原来的时间点开始。成片里有一条软字幕，每条字幕第一行是中文，第二行是英文。视频旁边还有两个字幕文件。

识别、翻译、配音都在本机运行。视频不会上传到 LectureDub 的服务器。第一次运行会从 Hugging Face 下载 Qwen3 模型，并放在平时的 Hugging Face 缓存里。

版本 0.3.0。MIT 许可。版权 2026 Yixuan Zhang。

## 目录

- [做完会得到什么](#做完会得到什么)
- [程序不会改什么](#程序不会改什么)
- [哪些电脑能跑](#哪些电脑能跑)
- [先安装依赖](#先安装依赖)
- [安装 LectureDub](#安装-lecturedub)
- [检查是否装好](#检查是否装好)
- [打开程序](#打开程序)
- [在窗口里配一节课](#在窗口里配一节课)
- [在终端里配一节课](#在终端里配一节课)
- [一次配好几节](#一次配好几节)
- [一节课是怎么处理的](#一节课是怎么处理的)
- [时间是怎么对齐的](#时间是怎么对齐的)
- [声音](#声音)
- [模型](#模型)
- [环境变量](#环境变量)
- [文件放在哪里](#文件放在哪里)
- [时间、内存和磁盘](#时间内存和磁盘)
- [把一节课再跑一遍](#把一节课再跑一遍)
- [字幕、音频和成片](#字幕音频和成片)
- [播放成片](#播放成片)
- [别让电脑睡眠](#别让电脑睡眠)
- [遇到问题](#遇到问题)
- [隐私](#隐私)
- [做不到的事](#做不到的事)
- [开发](#开发)
- [许可](#许可)

## 做完会得到什么

一节课做完是三个文件。输出名叫 `lecture-zh` 时，它们是：

| 文件 | 是什么 |
| --- | --- |
| `lecture-zh.mp4` | 原来的画面、一条中文 AAC 音轨，以及一条内嵌的双语字幕，标题是 中英字幕 |
| `lecture-zh.zh.srt` | 中文句子和对应的时间 |
| `lecture-zh.en.srt` | 同一组时间上用的英文 |

新视频和原视频一样长，误差大约在五秒以内。每一句中文从英文那一句开始的时刻开始。下一句之前的空隙保持安静。中文比这个空隙长时，最多加速到 1.16 倍，然后在边界截断。翻译时会按这个空隙的长度来写句子，所以截断应当少见。一旦发生，缺的是这一句的结尾，下一句仍然按时开始。

60 分钟的课做完仍然大约 60 分钟。画面保持你提供的文件的编码、分辨率和画质，因为视频流是拷贝过去的，没有重新编码。

## 程序不会改什么

- 画面按流拷贝。不会转成 H.265，也不会缩放。
- 原来的英文音轨被替换。不会留成第二条音轨。
- 字幕是 MP4 里的软字幕，再加上两个 `.srt` 文件。不会烧进画面。
- 窗口和命令行一次配一节。第二节在队列里等。
- 窗口界面是中文。每个控件的意思写在 [在窗口里配一节课](#在窗口里配一节课)。

## 哪些电脑能跑

| 电脑 | 后端 | 能不能跑 |
| --- | --- | --- |
| Apple Silicon Mac（M1、M2、M3、M4），macOS 13 或更新 | MLX | 能 |
| Windows 10 或 11，NVIDIA 驱动是新的 | CUDA | 能 |
| Linux，NVIDIA 驱动是新的 | CUDA | 能 |
| Intel Mac |  | 不能 |
| 只有 AMD、Intel 核显，或者没有独显的 Windows / Linux |  | 不能 |

在 Mac 上用 `uname -m` 看芯片。必须打印 `arm64`。

内存：机器比较空闲时，16 GB 够配一节。语音模型大约 5 GB。NVIDIA 显存不到 18 GB 时，翻译会自动使用 4-bit 的 Qwen3-8B。这条路径需要 `bitsandbytes`，它包含在 `nvidia` 这个额外依赖里。

磁盘：第一次运行前至少留出 25 GB。识别、翻译、语音三个模型加起来是这个量级，每一节成片还要另占空间。模型文件留在 Hugging Face 缓存里，一般是 `~/.cache/huggingface`，只下载一次。

Python 必须是 3.11 或更新。必须安装 ffmpeg 和 ffprobe。必须有上表里那种 GPU。Intel Mac 不能走 MLX，这个项目也没有给它用的 CUDA 路径。

## 先安装依赖

在 `install.sh` 或 `pip` 之前做完。安装脚本会检查 Python 和 ffmpeg 是不是已经存在，没有就会停。

### macOS

1. 如果还没有 `brew` 命令，先安装 [Homebrew](https://brew.sh)。
2. 安装 Python 和 ffmpeg：

```bash
brew install python@3.12 ffmpeg
```

3. 确认这台机器：

```bash
uname -m
python3 --version
ffmpeg -version
ffprobe -version
```

`uname -m` 必须是 `arm64`。`python3 --version` 必须是 3.11 或更高。`ffmpeg` 和 `ffprobe` 都要能打出版本。Homebrew 的 ffmpeg 包里带有 ffprobe。

LectureDub 先在 `PATH` 里找 ffmpeg，然后找 `/opt/homebrew/bin`，再找 `/usr/local/bin`。从访达打开应用时，这两个目录里的 Homebrew 安装仍然找得到。

### Windows

1. 从 [python.org](https://www.python.org/downloads/windows/) 安装 Python 3.11 或 3.12。安装程序第一页打开 **Add python.exe to PATH**。
2. 在 PowerShell 里安装 ffmpeg：

```powershell
winget install Gyan.FFmpeg
```

3. 关掉这个终端，新开一个，然后确认：

```powershell
python --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

`nvidia-smi` 必须打出显卡名字和驱动版本。如果没有这个命令，到 NVIDIA 网站安装当前的 Game Ready 或 Studio 驱动，然后重启。只装 CUDA Toolkit 代替不了驱动。

PyTorch 的 CUDA 版本会在后面的 `pip install ".[nvidia]"` 里装上。一般不用单独安装 CUDA Toolkit。

如果 Windows 上既有 Microsoft Store 的 Python 占位，又有真正的 Python，`python --version` 必须是真正的 3.11 或更新。安装脚本用的是它最先找到的 `python`。

### Linux

Debian 或 Ubuntu：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
python3 --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

`nvidia-smi` 必须列出显卡。继续之前，先用发行版的方式装好 NVIDIA 驱动。`python3-venv` 是必需的，因为安装脚本会在克隆目录里创建 `.venv`。

其他发行版用自己的包管理器安装同样四样东西：Python 3.11 或更新、venv 模块、pip，以及带 ffprobe 的 ffmpeg。

## 安装 LectureDub

克隆仓库：

```bash
git clone https://github.com/asher0913/lecturedub.git
cd lecturedub
```

### 用安装脚本

macOS 和 Linux：

```bash
./install.sh
```

Windows PowerShell，在克隆下来的目录里：

```powershell
.\install.ps1
```

如果 PowerShell 拒绝运行脚本，用这一次：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

脚本按下面的顺序做，任何一步失败都会停：

1. 在 macOS 上要求 `arm64`。Intel Mac 会退出，并打印 `Intel Macs are not supported.`
2. 要求 `python3`（Windows 上是 `python`）为 3.11 或更新。
3. 要求 `ffmpeg` 已经在 `PATH` 里。Mac 上也可以是 `/opt/homebrew/bin/ffmpeg`。
4. 在仓库目录里创建 `.venv`。
5. 在这个环境里升级 pip。
6. Apple Silicon 安装 `apple` 和 `desktop` 额外依赖。Windows 和 Linux 安装 `nvidia` 和 `desktop` 额外依赖。
7. 运行 `lecturedub doctor`。
8. Apple Silicon 会写入 `~/Applications/LectureDub.app`，并提示可以从“应用程序”打开 LectureDub。Windows 和 Linux 会打印打开窗口的命令。

`apple` 额外依赖是 MLX：`mlx-qwen3-asr`、`mlx-lm`、`mlx-audio`。`nvidia` 额外依赖是 PyTorch CUDA：`qwen-asr`、`qwen-tts`、`transformers`、`accelerate`、`bitsandbytes`。`desktop` 额外依赖是 `pywebview`，用来画系统窗口。每次安装都有的共享库是 `soundfile`、`numpy`、`yt-dlp`。

### 自己安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

Windows PowerShell 用 `.\.venv\Scripts\Activate.ps1`，不用 `source`。

然后安装其中一套额外依赖：

```bash
pip install -e ".[apple,desktop]"     # Apple Silicon
pip install -e ".[nvidia,desktop]"    # 带 NVIDIA 的 Windows 或 Linux
lecturedub doctor
```

Mac 上可以再把图标放进应用程序文件夹：

```bash
lecturedub install-app
```

`install-app` 是 macOS 应用包。在 Windows 或 Linux 上，同一条命令会退出，并告诉你改跑 `lecturedub app`。

只用浏览器、不要系统窗口时，去掉 `desktop`：

```bash
pip install -e ".[apple]"
# 或者
pip install -e ".[nvidia]"
lecturedub app --browser
```

### 不克隆仓库

```bash
pip install "lecturedub[apple,desktop] @ git+https://github.com/asher0913/lecturedub.git"
```

```bash
pip install "lecturedub[nvidia,desktop] @ git+https://github.com/asher0913/lecturedub.git"
```

这也应该装进虚拟环境。装完之后，`lecturedub doctor` 和 `lecturedub app` 在这个环境的 `PATH` 里。这条路不包含 `install.sh`。Mac 上如果要应用程序图标，自己再运行 `lecturedub install-app`。

### 更新已经装好的版本

在克隆目录里，激活同一个虚拟环境：

```bash
git pull
pip install -e ".[apple,desktop]"
```

Windows 和 Linux 把 `apple` 换成 `nvidia`。Mac 上再运行一次 `lecturedub install-app`，让应用程序图标指向更新后的命令。

### 卸掉

删掉克隆目录，包括里面的 `.venv`。Mac 上再删掉 `~/Applications/LectureDub.app`。下载过的模型还在 Hugging Face 缓存里，要自己删缓存才会消失。成片留在你保存它们的地方。窗口的任务目录是另一处，写在 [文件放在哪里](#文件放在哪里)。

## 检查是否装好

```bash
lecturedub doctor
```

如果用了 `install.sh` 但没有激活 `.venv`，直接调用环境里的命令：

```bash
.venv/bin/lecturedub doctor
```

Windows：

```powershell
.\.venv\Scripts\lecturedub doctor
```

一台正常的 Apple Silicon 会打出类似：

```text
lecturedub 0.3.0
python 3.12.x  arm64
system macOS-...
models: Apple Silicon, MLX
ffmpeg: /opt/homebrew/bin/ffmpeg
ffprobe: /opt/homebrew/bin/ffprobe
window: pywebview 5.4
data: /Users/you/Library/Application Support/LectureDub
```

一台正常的 NVIDIA 机器会打印 `models: NVIDIA` 和驱动报告的显卡名，例如 `models: NVIDIA GeForce RTX 4070`。

GPU 后端、ffmpeg 和数据目录都能用时，`doctor` 的退出码是 0。否则是 1。看失败的那一行：

| 打印出来的话 | 怎么处理 |
| --- | --- |
| `models: NVIDIA extra is missing...` | 在同一个虚拟环境里执行 `pip install -e ".[nvidia,desktop]"` |
| `models: no NVIDIA GPU with CUDA...` | 先让 `nvidia-smi` 成功，再重装 `nvidia` 额外依赖，让 PyTorch 是 CUDA 版本 |
| `ffmpeg: missing` 或 `ffprobe: missing` | 用那一行里打印的命令安装 ffmpeg，新开终端，再跑 doctor |
| `window: browser only...` | 可选。想要系统窗口就执行 `pip install -e ".[desktop]"`。浏览器这条路仍然能用 |
| `data: cannot write ...` | 数据目录不可写。把 `LECTUREDUB_HOME` 设到一个你能写的文件夹，再跑 doctor |
| `Intel Macs are not supported` | 这是 `install.sh` 在 doctor 之前打印的。换 Apple Silicon Mac，或者换一台有 NVIDIA 的 Windows 或 Linux |

Doctor 不下载模型，也不需要视频。

## 打开程序

三条命令打开同一个页面。它们都只监听 `127.0.0.1`。

```bash
lecturedub app
lecturedub app --browser
lecturedub ui
```

| 命令 | 打开什么 |
| --- | --- |
| `lecturedub app` | 一个系统窗口，980×780，标题是 LectureDub。需要 `desktop` 额外依赖。如果没有 pywebview，它会说明这一点并改用浏览器 |
| `lecturedub app --browser` | 系统浏览器。没有系统窗口 |
| `lecturedub ui` | 只启动服务器。它打印网址，不打开窗口，也不打开浏览器 |

默认端口是 7860。这个端口被占用时，服务器会试 7861，然后继续往后，到 7879 为止。用终端里打印的地址，样子是 `lecturedub  http://127.0.0.1:7860`。网络上的另一台电脑连不上。

可选参数：

```bash
lecturedub app --port 9000
lecturedub app --voice Serena
lecturedub ui --port 9000 --voice Vivian
```

`--voice` 是表单里没有另选声音时的默认声音。表单里仍然有自己的声音菜单。

在 Mac 上，`install.sh` 还会在“应用程序”里放一个 **LectureDub**（路径是 `~/Applications`，这是你主目录里的应用程序文件夹，不是 `/Applications`）。第一次打开可能被 Gatekeeper 拦住，因为这个应用包没有公证。按住 Control 点图标，选择 **打开**，再确认。启动器会把 `/opt/homebrew/bin` 和 `/usr/local/bin` 放进 `PATH`，这样能找到 ffmpeg，然后运行 `lecturedub app`。关掉窗口，服务器就停了。

整节课期间让终端或窗口开着。关掉它，这一节就停了。

## 在窗口里配一节课

页面是中文。每个控件的作用如下。

| 屏幕上的字 | 意思 |
| --- | --- |
| 拖入视频 | 把视频拖进来，或点这个框再选文件。接受的类型包括 mp4、mkv、webm、mov |
| 也可以只贴下面的链接。有英文字幕的话一并拖进来。 | 也可以改贴链接。如果有英文 `.srt` 或 `.vtt`，拖进同一个框 |
| 视频链接 | `http://` 或 `https://` 网址。可以是媒体文件的直链，也可以是 yt-dlp 能解析的页面 |
| 中文声音 | 普通话声音。菜单里的三项写在 [声音](#声音) |
| 开始配音 | 开始。上传被接受时按钮会暂时不能按，之后可以再排队下一节 |
| 正在转录 | 语音识别 |
| 正在翻译 | 翻译成口语中文。分数是完成的批次，不是视频的秒数 |
| 正在配音 | 语音合成。分数是完成的句数，例如 `120/380` |
| 正在封装 | 正在把画面、中文音频和字幕写进 MP4 |
| 排队中 | 在等正在跑的那一节 |
| 排队中，正在准备 | 已经在跑，但还没有第一份进度数字。这是在加载或下载模型 |
| 配音完成 | MP4 已经生成 |
| 下载视频 | 下载 `dubbed.mp4` |
| 中文字幕 | 下载 `dubbed.zh.srt` |
| 英文字幕 | 下载 `dubbed.en.srt` |
| 在 Finder 中显示 | 在 Mac 上，于访达中定位 `dubbed.mp4`。在 Linux 上，用 `xdg-open` 打开文件夹。在 Windows 上请用下载链接；这个按钮调用的是 `xdg-open`，Windows 没有这个命令 |

页脚写的是：视频只留在这台电脑上，第一次运行会下载模型，一节课通常要几十分钟，16 GB 内存一次只配一节。页面加载后，版本号会接在这段话后面。

步骤：

1. 把视频拖进虚线框。文件名会换成提示文字。再拖一个 `.srt` 或 `.vtt`，就会附上字幕。新的视频会替换上一份视频。新的字幕会替换上一份字幕。
2. 视频在网上时，把网址贴上，文件框留空。本地文件和网址都有时，用本地文件。
3. 选声音。默认是 **Uncle Fu**。
4. 点 开始配音。任务标题是视频文件名去掉扩展名；只贴了网址时，标题是 `lecture`。这个标题也会当作语音识别的提示。见 [模型](#模型)。
5. 看状态行。页面每两秒刷新一次。
6. 状态变成 配音完成 后，下载三个文件，或在访达里显示视频。

第一节还在跑时可以提交第二节。它会停在 排队中，直到工作线程空出来。只有一个工作线程。16 GB 的机器上不要同时再开第二个 `lecturedub app`。

第一次会在 排队中，正在准备 上停留很久，因为正在下载 Hugging Face 的文件。以后会用缓存。80 分钟的课常常有几百句，慢的是配音：模型加载完之后，大约每句 10 到 16 秒。让电脑保持醒着。见 [别让电脑睡眠](#别让电脑睡眠)。

上传里既没有视频也没有网址时，服务器返回 `drop a video or paste a link`，页面显示这句英文。只有服务器没有带回错误文字时，才会改显示中文的 没有收到视频。

### 窗口把任务存在哪里

每次提交有一个 id。这个 id 的文件在数据目录下：

- macOS：`~/Library/Application Support/LectureDub/jobs/<id>/`
- Windows 和 Linux：`~/.lecturedub/jobs/<id>/`
- 设置了 `$LECTUREDUB_HOME` 时：`$LECTUREDUB_HOME/jobs/<id>/`

一节做完的任务里面是：

```text
jobs/<id>/
  out/video/dubbed.mp4
  out/video/dubbed.zh.srt
  out/video/dubbed.en.srt
  video-dubbed/source.mp4
  video-dubbed/en.orig.srt
  video-dubbed/segments.json
  video-dubbed/clips/
  video-dubbed/dub.wav
  video-dubbed/dubbed.mp4
```

`out/video/` 是下载按钮提供的文件。`video-dubbed/` 是工作副本：原片、英文稿、中文稿、每一句一个 wav，以及混好的音轨。这些工作文件很大。三个结果复制走之后，可以删掉这个任务文件夹。

服务器绑定端口时，也会打印 `jobs    <数据目录>/jobs`。

## 在终端里配一节课

激活虚拟环境，或者直接调用 `.venv/bin/lecturedub`（Windows 是 `.\.venv\Scripts\lecturedub`）。

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4
lecturedub run lecture.mp4 --srt lecture.en.srt -o lecture-zh.mp4
lecturedub run "https://example.com/lecture.mp4" -o lecture-zh.mp4
lecturedub run lecture.mp4 -o lecture-zh.mp4 --voice Serena --title "Distributed systems, lecture 3"
```

`-o` / `--output` 是必填的。它是最终 MP4 的路径。两个字幕文件写在它旁边的 `video/` 目录里，文件名用 `-o` 的主文件名：

```text
~/Desktop/lecture-zh.mp4
~/Desktop/video/lecture-zh.zh.srt
~/Desktop/video/lecture-zh.en.srt
```

这个布局是因为这条命令把单个文件当成一门叫 `video` 的课。MP4 随后会从 `video/` 移到你写的 `-o` 路径。字幕留在 `video/` 里。

一个完整例子：Mac 上，文件在桌面。

```bash
cd ~/Desktop
caffeinate -dims ~/.path/to/lecturedub/lecturedub run "CS lecture.mp4" --srt "CS lecture.en.srt" -o "$HOME/Desktop/cs-lecture-zh.mp4" --voice Uncle_Fu
```

把 `lecturedub` 换成 `.venv` 里的真实路径。结束时，终端会打印 MP4 路径。用 VLC 或 IINA 打开，并打开名为 中英字幕 的字幕轨。

### `run` 的每一个选项

| 选项 | 默认 | 意思 |
| --- | --- | --- |
| `video` | 必填 | 本地路径，或 `http://` / `https://` 网址 |
| `-o`, `--output` | 必填 | 最终 MP4 路径。上级目录不存在时会创建 |
| `--srt` | 无 | 英文 `.srt` 或 `.vtt`，可以是路径或网址。这份文件能读时，就跳过语音识别 |
| `--title` | `-o` 的主文件名 | 交给语音识别，当作术语提示。你已经给了可靠的 `--srt` 时，它不影响配音稿 |
| `--voice` | `Uncle_Fu` | [声音](#声音) 里的一个名字 |
| `--work` | `work/jobs` | 这一次的工作目录。相对路径相对于当前目录，也可以写绝对路径 |

进度会打到终端，并追加到 `<work>/dub.log`。机器可读的一份在 `<work>/progress.json`，`stage` 是 `asr`、`translate` 或 `voice`；翻译和配音时还有 `done` 和 `total`。

工作目录是 `<work>/video-<主文件名>/`，主文件名来自 `-o`。里面有 `source.mp4`、`segments.json`、`clips/` 和 `dub.wav`。见 [文件放在哪里](#文件放在哪里)。

## 一次配好几节

把课写成一个 JSON 列表。同样的形状在 `examples/batch.example.json` 里有一份。

```json
[
  {
    "title": "Lecture 1",
    "slug": "lecture-1",
    "course": "cs101",
    "video": "lecture-1.mp4",
    "srt": "lecture-1.en.srt"
  },
  {
    "title": "Lecture 2",
    "video": "https://example.com/lecture-2.mp4"
  }
]
```

`video` 也可以写成 `videoUrl`。以 `http://` 或 `https://` 开头的会下载。其他值是本地路径。`srt` 一样：网址会下载，路径会读取。没有 `srt`、但 `captions` 是一个列表时，用第一条字幕的 `url`。

`title` 是给人看的名字，也是语音识别的提示。`slug` 是文件名。它只保留字母、数字、`.`、`_` 和 `-`，并截到 80 个字符。省略 `slug` 时，用标题生成。`course` 是输出子目录。省略时，子目录是 `video`。任务键是 `course-slug`；没有 course 时就是 `slug`。

可选的下载检查：

| 字段 | 意思 |
| --- | --- |
| `duration` | 预期长度，单位秒。下载结果和它相差超过 4 秒会被拒绝 |
| `bandwidth` | 比特每秒。和 `duration` 一起用时，文件要达到预期大小的大约 82%，才算下载完整 |

```bash
lecturedub batch manifest.json --output-dir output
```

完成后的文件：

```text
output/cs101/lecture-1.mp4
output/cs101/lecture-1.zh.srt
output/cs101/lecture-1.en.srt
output/video/lecture-2.mp4
output/video/lecture-2.zh.srt
output/video/lecture-2.en.srt
```

几节课一节接一节做。某一节的输出 MP4 已经存在，并且时长和原片相差在 5 秒以内，就会跳过。日志类似 `0 lecture(s) to dub, 2 already done`。

### `batch` 的每一个选项

| 选项 | 默认 | 意思 |
| --- | --- | --- |
| `manifest` | 必填 | JSON 文件。可以是一个列表，也可以是带 `jobs` 或 `items` 数组的对象 |
| `--output-dir` | `output` | MP4 和两个 SRT 复制到这里 |
| `--work-dir` | `work/lectures` | 每一节一个子目录，目录名是任务键 |
| `--voice` | `Uncle_Fu` | 这一次清单里每一节用的声音 |
| `--only` | 无 | 只保留键或标题里包含这段文字的课 |
| `--pilot-seconds` | 无 | 只配筛选后第一节的开头，长度是这个秒数。结果是工作目录里的试听文件，这一节不会被标成已完成 |
| `--no-download` | 关闭 | 不抓取网址。使用工作目录里已经有的 `source.mp4` 和 `en.orig.srt` |
| `--translate-only` | 关闭 | 写好 `segments.json` 后停，不配音 |

相关命令用同一份清单：

```bash
lecturedub fetch manifest.json --work-dir work/lectures --output-dir output
lecturedub batch manifest.json --output-dir output --translate-only
lecturedub batch manifest.json --output-dir output --only "Lecture 1" --pilot-seconds 60
lecturedub mux manifest.json --output-dir output --work-dir work/lectures
```

`fetch` 下载视频和字幕网址。它不加载模型。`mux` 封装已经有 `dub.wav`、`segments.json` 和 `source.mp4` 的那一节。配音已经结束、封装没有完成时用它。`--pilot-seconds` 总会在筛选后的第一节做完就停，哪怕后面还有能匹配的行。

使用 `--no-download` 时，已经有英文字幕的课会配音。同一次运行里如果还有一节仍然需要识别，这次识别会留到下一次、并且那一次不再同时包含已有字幕的课。日志会写 `defer transcription until captioned lectures are done`。

工作目录的名字是 `lectures`（这是默认值）时，批量日志写在工作目录旁边的 `dub.log`。否则日志写在工作目录里面。

## 一节课是怎么处理的

窗口、`run` 和 `batch` 走的是同一步骤。

1. **视频。** 本地文件复制到任务目录的 `source.mp4`。看起来像媒体文件的网址直接下载。其他网址交给 yt-dlp。小于 200 KB 的文件会被拒绝。清单里给了 `duration` 或 `bandwidth` 时，那些检查也会执行。
2. **英文文本。** 提供的 `.srt` 或 `.vtt` 存成 `en.orig.srt`。字幕条先被解析，再合并成能念的短语。短语在停顿超过 0.55 秒时断开，或者在已经至少 3.2 秒并且到了句末时断开，或者在 16 秒时断开，哪一个先到用哪一个。
3. **只有没有可用字幕时才识别。** 音轨抽成 16 kHz 的 `audio16k.wav`。Qwen3-ASR 写出带时间的英文。在 NVIDIA 上，Qwen3-ForcedAligner 提供词的时间；长音频由这个库自己切段。词的时间会收成最多 12 秒的短语，遇到 `.`、`?`、`!` 也会断开，词与词的空隙超过 0.8 秒也会断开。标题决定术语表：标题里有 `511`、`c-store`、`cstore`、`dremel`、`snowflake`、`system r`、`pregel` 或 `kafka` 时，提示是数据管理课；否则提示是分布式系统课。识别之后、翻译之前，MLX 模型会卸掉。
4. **语速样本。** 语音模型念一句固定的中文，这段音频的长度用来计算一秒能放多少字，然后模型再次卸掉。样本慢于每秒 4.2 个单位，或快于每秒 6.5 个单位时，规划用 4.5。一个单位是一个汉字，或者一个拉丁词算两个单位。这个数字只是给翻译用的字数预算。
5. **翻译。** Qwen3-8B 把每一句改成能直接念的简体中文。它看得到上一句、下一句、时长和字数预算。要求是不添加事实，英文停在半句时中文也不要把后半句补完，后面的分句不要漏掉。每批 12 句。结果边做边写进 `segments.json`，所以中断后重跑会从已经有中文的句子往后继续。
6. **配音。** 语音模型再次加载，一句一句念中文。某一句如果已经有大于 800 字节的 wav，就直接用。每一句放在原来的开始时间上。
7. **封装。** 各句音频混成一条时间轴，做响度归一，再封装。画面流原样拷贝。中文音频变成 AAC。双语字幕变成一条 `mov_text`。然后把 `dubbed.mp4`、`zh.srt` 和 `en.fixed.srt` 复制成输出文件名。

窗口上的状态名对应第 3、5、6、7 步：正在转录、正在翻译、正在配音、正在封装。

## 时间是怎么对齐的

每一句的时间槽，是到下一句开始的时间，再减去 0.03 秒。最后一句的时间槽一直到视频结束。

原始录音会去掉头尾的静音：绝对值低于 0.012 的样本当成静音，两侧各留 0.04 秒。两端各做 12 毫秒的淡入淡出，避免拼接时有咔嗒声。

音频比时间槽长时，用保持音高的 `atempo` 加速，最多 1.16 倍。加速之后仍然更长的部分，在时间槽边界截掉。时间槽只有 0.15 秒或更短时，放一小段静音，不放语音。某一句的原始音频超过时间槽的 1.16 倍时，会往 `clips/fit.log` 追加一行：

```text
<句子 id>    <原始秒数>    <时间槽秒数>
```

这一行表示那一句的结尾被截掉了。把 `segments.json` 里这个 id 的中文写短，删掉 `clips/` 里对应的 wav，删掉已经完成的 MP4，让这一节不再被当成做完，然后重新运行。只有改过的那一句会重新念。

中文不是以 `。`、`！`、`？` 或 `…` 结尾时，会用平稳、没收住的语调来念，这样接到下一句的半句听起来不像已经说完。

混好的音轨会做响度归一，综合响度大约 −16 LUFS，真峰值大约 −1.5 dBTP，响度范围 11。归一失败时，就用还没有归一的混音。

## 声音

窗口提供三种 Qwen3 定制声音。命令行用同样的名字。

| 名字 | 窗口里的写法 | 听感 |
| --- | --- | --- |
| `Uncle_Fu` | Uncle Fu · 低沉男声，适合讲课 | 偏低的男声。这是默认，也是用来讲课的那个 |
| `Serena` | Serena · 温和女声 | 比较柔和的女声 |
| `Vivian` | Vivian · 明亮女声 | 比较明亮的女声 |

每一句都带着这样的要求来念：沉稳清晰的普通话讲课，语速平稳，像大学课堂录音，不要表演，不要拖腔。声音按每一节来选。一次批量运行里，整份清单用同一个声音。

## 模型

三个阶段都是 Qwen3。Apple Silicon 加载 MLX 权重。NVIDIA 加载 PyTorch 权重。可以用环境变量换模型 id。没有理由就不要改。

| 阶段 | Apple Silicon | NVIDIA | 变量 |
| --- | --- | --- | --- |
| 语音识别 | `Qwen/Qwen3-ASR-1.7B` | `Qwen/Qwen3-ASR-1.7B`，另加 `Qwen/Qwen3-ForcedAligner-0.6B` 用来取词的时间 | `LECTUREDUB_ASR` |
| 翻译 | `mlx-community/Qwen3-8B-4bit` | `Qwen/Qwen3-8B`。显存不到 18 GB 时用 4-bit | `LECTUREDUB_LLM` |
| 中文配音 | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `LECTUREDUB_TTS` |

下面是大致的下载体积，用来估计第一次要等多久：1.7B 识别模型大约 4 GB，0.6B 对齐模型大约 1.5 GB 并且只有 NVIDIA 会下，4-bit 的 Qwen3-8B 大约 5 GB，16-bit 的 Qwen3-8B 大约 16 GB，1.7B 语音模型大约 4 GB。所以 Apple Silicon 大约要下 13 GB。显存不到 18 GB 的 NVIDIA 差不多，还要加上对齐模型。18 GB 或更大的显卡可能会下载更大的 16-bit 翻译模型，而不是 4-bit 权重。

NVIDIA 推理在显卡支持时用 bfloat16，否则用 float16。语音模型的采样温度是 0.5。翻译是贪心解码。公开的 Hugging Face 模型下载不需要账号。如果下载被限速，通常把 Hugging Face 令牌放进 `HF_TOKEN`。网络慢时可以用镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="$HOME/huggingface-cache"
lecturedub app
```

Windows PowerShell：

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HOME = "$HOME\huggingface-cache"
lecturedub app
```

`HF_HOME` 用来搬家缓存。默认磁盘空间小的话，在第一次运行之前设好。

## 环境变量

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `LECTUREDUB_BACKEND` | Apple Silicon 上是 `mlx`，其他情况是 `cuda` | 强制使用 `mlx` 或 `cuda` |
| `LECTUREDUB_CUDA_DEVICE` | `cuda:0` | 用哪一块 NVIDIA 设备，例如 `cuda:1` |
| `LECTUREDUB_ASR` | 上表 | 识别模型 id |
| `LECTUREDUB_LLM` | 上表 | 翻译模型 id |
| `LECTUREDUB_TTS` | 上表 | 语音模型 id。在 CUDA 上，MLX 的模型 id 会改写成 CUDA 的语音模型 |
| `LECTUREDUB_MEM_GB` | `6.5` | MLX 内存上限，单位 GB。语音模型大约要用其中 5 GB |
| `LECTUREDUB_CACHE_MB` | `256` | MLX 缓存上限，单位 MB |
| `LECTUREDUB_HOME` | 各系统的数据目录 | 窗口把任务存在这里 |
| `HF_HOME` | `~/.cache/huggingface` | Hugging Face 缓存位置 |
| `HF_ENDPOINT` | 官方 Hub | 下载镜像 |
| `HF_TOKEN` | 无 | 下载要求登录时用的 Hub 令牌 |

在启动 `lecturedub` 的同一个终端里设置。macOS 的应用程序图标看不到你在另一个终端里 export 的变量。要改这些变量，就在终端里用 `lecturedub app` 启动。

## 文件放在哪里

窗口用的数据目录：

| 系统 | 路径 |
| --- | --- |
| macOS | `~/Library/Application Support/LectureDub` |
| Windows | `C:\Users\<you>\.lecturedub` |
| Linux | `~/.lecturedub` |

命令行的工作文件取决于 `--work` 或 `--work-dir`。一次默认的 `run`，`-o lecture-zh.mp4` 之后：

```text
work/jobs/dub.log
work/jobs/progress.json
work/jobs/video-lecture-zh/source.mp4
work/jobs/video-lecture-zh/en.orig.srt
work/jobs/video-lecture-zh/audio16k.wav          # 只有做过识别才有
work/jobs/video-lecture-zh/segments.json
work/jobs/video-lecture-zh/zh.srt
work/jobs/video-lecture-zh/en.fixed.srt
work/jobs/video-lecture-zh/clips/00000-aaaaaaaaaa.wav
work/jobs/video-lecture-zh/clips/fit.log         # 只有某一句被截断才有
work/jobs/video-lecture-zh/dub.raw.wav
work/jobs/video-lecture-zh/dub.wav
work/jobs/video-lecture-zh/dubbed.mp4
```

`segments.json` 是一组 `{id, start, end, en, zh}`。`id` 对应音频文件名的前缀。`start` 和 `end` 是秒。`en` 是被翻译的英文。`zh` 是将要念出来的那一句。

`batch` 时，把 `work/jobs/video-lecture-zh` 换成 `work/lectures/<course>-<slug>`。

克隆目录里这些路径被 git 忽略：`.venv/`、`work/`、`output/`、`models/`，以及媒体文件（`*.mp4`、`*.wav`、`*.mov`、`*.mkv`）。不要把课程视频或模型权重提交进去。

## 时间、内存和磁盘

配音在一块 GPU 上逐句进行。开两个配音进程不会更快。在 16 GB 的机器上，那样做可能把 GPU 打崩。窗口已经把任务排成一串。窗口正在配音时，不要再在终端里开第二节。

模型进内存之后，可以用每句 10 到 16 秒的墙上时间来估计。400 句大约是 70 到 110 分钟的配音，再加翻译。这 400 句的翻译比配音短得多，8B 模型加载完之后常常是几分钟。没有字幕的 80 分钟文件，识别还要再花几分钟。第一次运行还要加上模型下载，快慢取决于网络。

封装比较短。拷贝视频流不会重新编码画面。80 分钟的文件通常几分钟就能封装完，取决于磁盘速度。

语音模型大约占 5 GB。`LECTUREDUB_MEM_GB` 默认 6.5，这样 16 GB 的 Mac 还留给系统一些空间。长课开始前关掉其他大程序。NVIDIA 显存不到 18 GB 时，翻译用 4-bit。如果没有 `bitsandbytes`，翻译会停下来并在报错里点名这个包，而不是把 16-bit 的 8B 模型装进这块卡。

工作用的音频在合成过程中是未压缩的。长课的 `dub.raw.wav` 和 `clips` 文件夹可以到好几个 GB。成片 MP4 和原视频差不多大，因为画面是拷贝的，音频是 128 kbps。

## 把一节课再跑一遍

输出 MP4 已经存在，并且时长和 `source.mp4` 相差在 5 秒以内时，`batch` 和 `run` 会跳过这一节。原片文件已经删掉时，任何已经存在的输出 MP4 都算做完。

要整节重做，删掉那个输出 MP4，再运行同一条命令。已经有的句子 wav 会继续用，所以中文没改过的句子不会重新念。

要重做一句：

1. 在 `segments.json` 里改这个 `id` 的 `zh`。JSON 要保持合法。除非你就是要移动这条字幕，否则不要改 `id`、`start` 或 `end`。
2. 删掉 `clips/` 里文件名以这个 id 开头的 wav，例如 `00122-`。文件名里含有中文和语调要求的哈希，旧文件本来也对不上，删掉只是免得混淆。
3. 删掉输出 MP4，否则任务会被跳过。
4. 运行同一条命令。

`--translate-only` 会补上还没有的中文，把配音留到下一次。`--pilot-seconds 60` 用来在做完整文件之前先听开头。试听文件在工作目录里，名叫 `pilot.mp4`，不会替换正式输出。

## 字幕、音频和成片

内嵌字幕是一条 `mov_text`：

- 语言标记 `zho`
- 轨道标题 `中英字幕`
- 默认显示，所以尊重这个标记的播放器不用再点一次就会显示
- 每一条是中文一行、换行、然后英文一行
- 文件带 `+faststart`，在网络上拷贝时可以先开始播放

中文音轨：

- AAC-LC
- 128 kbps
- 44100 Hz
- 立体声
- 语言标记 `zho`
- 响度大约 −16 LUFS，真峰值大约 −1.5 dBTP

视频轨就是原片用的那种。宽度、高度和编码保持原样。没有第二条音轨。

`zh.srt` 和 `en.srt` 用普通的 SRT 时间（`HH:MM:SS,mmm`），边界和内嵌字幕相同。播放器不认 `mov_text` 时，可以把其中一个文件交给它。

## 播放成片

VLC 和 IINA 都能显示内嵌字幕。在 VLC 里打开字幕菜单，选择名叫 中英字幕 的轨道。IINA 在字幕菜单里列出它。播放器藏起了内嵌字幕时，加载旁边的 `.zh.srt`，或加载双语字幕文件。mpv 在某些目录布局下会自动找到同名字幕；没有找到时，把 srt 明确传给它。

QuickTime 有时显示 `mov_text`，有时不显示，取决于 macOS 版本。不显示时用 VLC 或 IINA，或者加载 SRT。

同一条字幕里，中文和英文是两行，所以它们一起出现在画面下方。英文行没有单独的样式。程序不生成烧进画面的字幕。

## 别让电脑睡眠

睡眠会打断一次很长的配音。已经写好的句子音频会留下，下次对同一节再跑会继续，但你要等到发现它停了，这段时间就空过去了。

macOS，包住一条终端任务：

```bash
caffeinate -dims lecturedub run lecture.mp4 -o lecture-zh.mp4
```

`-dims` 要求系统在空闲时不要让显示器、系统和磁盘睡眠。把电源插上。16 GB 的笔记本只用电池时，可能因为内存压力把配音进程杀掉。

Windows：设置、系统、电源，在任务运行期间把睡眠设成从不。Linux：`systemd-inhibit --what=idle:sleep lecturedub run lecture.mp4 -o lecture-zh.mp4`，或者用桌面环境自己的电源设置。

## 遇到问题

**Doctor 说缺少 NVIDIA 额外依赖。**  
你装的是基础包，或者装的是 `apple` 额外依赖。在虚拟环境里执行 `pip install -e ".[nvidia,desktop]"`。

**Doctor 说没有带 CUDA 的 NVIDIA GPU。**  
同一个终端里 `nvidia-smi` 必须成功。然后重装，让 pip 拿到 PyTorch 的 CUDA 轮子，而不是 CPU 轮子。如果只是驱动不行，安装当前的 NVIDIA 驱动并重启。

**从访达打开 Mac 应用时出现 `ffmpeg: missing`。**  
Doctor 除了 `PATH`，还会看 `/opt/homebrew/bin` 和 `/usr/local/bin`。ffmpeg 装在别的地方时，做个符号链接到这两个目录之一，或者在 `ffmpeg -version` 能用的终端里运行 `lecturedub app`。`ffmpeg and ffprobe are required. Install them with: brew install ffmpeg` 是所有系统上的运行时报错；在 Windows 或 Linux 上，用 [先安装依赖](#先安装依赖) 里的安装命令。

**页面一直停在 排队中，正在准备。**  
模型正在加载或下载。看启动程序的那个终端。那里有 Hugging Face 的进度条，就是第一次下载还没完。从你的网络访问 Hub 很慢时，设置 `HF_ENDPOINT`。

**进程因 Metal 报错停下，或者机器内存不够。**  
关掉第二份副本。一次只留一个语音模型。关掉浏览器和其他占用 GPU 的程序。在 Mac 上，`LECTUREDUB_MEM_GB=6.5` 是默认上限；在 16 GB 的机器上把它调高，留给系统的空间就更少。

**翻译说这块 GPU 不到 18 GB。**  
重装 `nvidia` 额外依赖，从而装上 `bitsandbytes`。这个包装好并能导入之后，4-bit 路径会自动启用。

**网址失败，或者下载下来特别小。**  
直链按文件下载。页面链接走 yt-dlp，那个站点必须被 yt-dlp 支持。小于 200 KB 的下载，或者时长和清单里的 `duration` 相差超过 4 秒的下载，会被丢掉。自己先把视频下好，再把本地路径传进去。

**成片没有中文声音。**  
任务没有走到封装。看 `dub.log` 里最后一条 `voice` 或 `done`。如果 `dub.wav` 和 `source.mp4` 都在，`lecturedub mux manifest.json` 可以不再配音、直接封装。

**某一句说了一半，下一句仍然按时开始。**  
这一句即使加速到 1.16 倍仍然比时间槽长。`clips/fit.log` 列出这些 id。按 [把一节课再跑一遍](#把一节课再跑一遍) 处理那个 id。

**整节被跳过，旧文件没有变。**  
输出 MP4 仍然被当成已经完成。想要新的一份，就删掉它。没改过的句子会继续用原来的工作音频。

**7860 端口被占用。**  
服务器会换到下一个端口，最多到 7879，并打印网址。用 `--port` 可以指定。绑定的只有 `127.0.0.1`。

**Mac 应用显示已损坏或无法打开。**  
在 `~/Applications` 里按住 Control 点 `LectureDub`，选择打开。这个应用包是在你的机器上生成的，没有经过苹果公证。`LSMinimumSystemVersion` 是 13.0。

**Windows 不愿意运行 `install.ps1`。**  
在克隆目录里执行 `powershell -ExecutionPolicy Bypass -File .\install.ps1`。脚本仍然要求 `python` 和 `ffmpeg` 在 `PATH` 里。

**Windows 上“在 Finder 中显示”没有反应。**  
这个按钮在 Mac 上始终调用访达的 `open -R`，在其他系统上调用 `xdg-open`。请用 下载视频、中文字幕 和 英文字幕。文件仍然在 [文件放在哪里](#文件放在哪里) 的数据目录里。

## 隐私

语音识别、翻译和语音合成不会把课程发到这个项目的服务器。窗口只绑定 `127.0.0.1`。你贴上的网址由这台机器下载，要么直接下载，要么通过 yt-dlp，来源是那个网址里的网站。模型权重从 Hugging Face 下载；如果你设置了 `HF_ENDPOINT`，就从那里下载，并放进本机缓存。

任务文件、成片和虚拟环境都不在 git 仓库里。不要把课程视频、账号令牌或 `HF_TOKEN` 放进提交。

## 做不到的事

- 这一版是把英文课做成口语简体中文。其他语言方向不是一个可选模式。
- Apple Silicon 走 MLX，NVIDIA 走 CUDA。Intel Mac、AMD 显卡和只有 CPU 的机器不在安装脚本的支持范围内。
- 一节课在配音这一阶段会占住 GPU，直到念完。队列不会把一节课拆到两块设备上。
- 加速到 1.16 倍仍然放不下的句子，会丢掉结尾。后面的句子不会因此推迟。
- 原来的英文音轨是被替换的，不是压低以后垫在中文下面。
- 字幕是软字幕。不认 `mov_text` 的播放器要用 SRT 文件。
- 这一版的窗口文字是中文。
- `lecturedub doctor` 和单元测试不加载模型。测试通过，表示路径选择和字幕时间的代码是完整的。它不表示某一块 GPU 已经下好了权重。

## 开发

在克隆目录里：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[apple,desktop,dev]"
python -m pytest
```

NVIDIA 上改为安装 `".[nvidia,desktop,dev]"`。测试不下载模型，也不需要 GPU。它们检查字幕解析、短语合并、对齐结果的形状，以及在 `LECTUREDUB_BACKEND` 下任务会走到 MLX 还是 CUDA。

和结构有关的路径：

| 路径 | 作用 |
| --- | --- |
| `lecturedub/__main__.py` | `lecturedub` 命令 |
| `lecturedub/pipeline.py` | 下载、识别、翻译、配音、封装 |
| `lecturedub/asr.py` | MLX 和 CUDA 上的 Qwen3-ASR |
| `lecturedub/translate.py` | Qwen3-8B 翻译和长度检查 |
| `lecturedub/voice.py` | Qwen3-TTS 和 1.16 倍的时间适配 |
| `lecturedub/media.py` | ffmpeg 下载、响度和封装 |
| `lecturedub/subtitles.py` | SRT 和 VTT 解析、短语合并 |
| `lecturedub/runtime.py` | MLX 与 CUDA 的选择，以及默认模型 id |
| `lecturedub/web.py` | 本机 HTTP 服务，以及一次一节的队列 |
| `lecturedub/desktop.py` | 系统窗口、`LectureDub.app` 和 doctor |
| `lecturedub/static/index.html` | 窗口里显示的页面 |
| `install.sh`、`install.ps1` | 虚拟环境安装脚本 |
| `examples/batch.example.json` | 一份两节课的清单 |

`pyproject.toml` 里的作者是 Yixuan Zhang，许可是 MIT。控制台命令是 `lecturedub`。

## 许可

MIT 许可。版权 (c) 2026 Yixuan Zhang。

你可以按 `LICENSE` 里的条款使用、复制、修改和分发这个项目。你配音的课程文件是你自己的。它们不在这个仓库里，这个许可也不授予那些文件的任何权利。
