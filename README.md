# lecturedub

**English** | [简体中文](README.zh-CN.md)

GitHub opens this English page first. The Chinese page is the same manual, translated. Choose **简体中文** above to read it.

LectureDub turns an English lecture into a Chinese-dubbed video on your own computer. The picture is copied from the file you give it. The English soundtrack is replaced by Mandarin that starts on the original timestamps. The result carries one soft subtitle track with Chinese on the first line of each cue and English on the second, plus two subtitle files beside the video.

Recognition, translation, and speech all run locally. The video is not uploaded to a LectureDub server. The first run downloads the Qwen3 models from Hugging Face and keeps them in the normal Hugging Face cache.

Version 0.3.0. MIT License. Copyright 2026 Yixuan Zhang.

## Contents

- [What you get](#what-you-get)
- [What the program leaves alone](#what-the-program-leaves-alone)
- [Computers that can run it](#computers-that-can-run-it)
- [Install the prerequisites](#install-the-prerequisites)
- [Install LectureDub](#install-lecturedub)
- [Check the installation](#check-the-installation)
- [Open the app](#open-the-app)
- [Dub one lecture in the window](#dub-one-lecture-in-the-window)
- [Dub one lecture from the terminal](#dub-one-lecture-from-the-terminal)
- [Dub many lectures](#dub-many-lectures)
- [How one lecture is processed](#how-one-lecture-is-processed)
- [How the timing works](#how-the-timing-works)
- [Voices](#voices)
- [Models](#models)
- [Environment variables](#environment-variables)
- [Files on disk](#files-on-disk)
- [Time, memory, and disk](#time-memory-and-disk)
- [Run a lecture again](#run-a-lecture-again)
- [Subtitles, audio, and the finished file](#subtitles-audio-and-the-finished-file)
- [Play the result](#play-the-result)
- [Keep the computer awake](#keep-the-computer-awake)
- [Troubleshooting](#troubleshooting)
- [Privacy](#privacy)
- [Limits](#limits)
- [Development](#development)
- [License](#license)

## What you get

One finished lecture is three files. For an output name `lecture-zh` they are:

| File | What it is |
| --- | --- |
| `lecture-zh.mp4` | The original picture, a Chinese AAC soundtrack, and one embedded bilingual subtitle track titled 中英字幕 |
| `lecture-zh.zh.srt` | The Chinese lines and their timestamps |
| `lecture-zh.en.srt` | The English lines used for those same timestamps |

The new video is the same length as the source, within about five seconds. Each Chinese sentence starts when the English phrase started. The gap before the next phrase stays quiet. If the Chinese is longer than that gap, it is sped up by at most 1.16× and then cut at the boundary. Translation is asked to write a line that fits the gap, so a cut should be rare. When it happens, the end of that one sentence is missing and the next sentence still starts on time.

A 60-minute lecture stays about 60 minutes. The picture keeps the codec, frame size, and quality of the file you supplied, because the video stream is copied rather than encoded again.

## What the program leaves alone

- The picture is stream-copied. It is not converted to H.265, and it is not scaled.
- The original English audio is replaced. It is not kept as a second audio track.
- Subtitles are a soft track inside the MP4, plus the two `.srt` files. They are not burned into the picture.
- The window and the command line dub one lecture at a time. A second lecture waits in a queue.
- The interface of the window is in Chinese. The labels are translated in [Dub one lecture in the window](#dub-one-lecture-in-the-window).

## Computers that can run it

| Computer | Backend | Can run |
| --- | --- | --- |
| Apple Silicon Mac (M1, M2, M3, M4), macOS 13 or newer | MLX | Yes |
| Windows 10 or 11 with a current NVIDIA driver | CUDA | Yes |
| Linux with a current NVIDIA driver | CUDA | Yes |
| Intel Mac |  | No |
| Windows or Linux with only AMD, Intel graphics, or no discrete GPU |  | No |

Check the Mac chip with `uname -m`. It must print `arm64`.

Memory: 16 GB is enough for one lecture if you leave the machine otherwise quiet. The speech model is about 5 GB. On an NVIDIA card with less than 18 GB of VRAM, translation automatically uses a 4-bit Qwen3-8B. That path needs `bitsandbytes`, which is part of the `nvidia` extra.

Disk: leave at least 25 GB free before the first run. The recognizer, the translator, and the voice together are on that order, and each finished video needs space of its own. Model files stay in the Hugging Face cache, usually `~/.cache/huggingface`, and are downloaded once.

Python must be 3.11 or newer. ffmpeg and ffprobe must be installed. A GPU of the kind in the table above must be present. An Intel Mac cannot use the MLX path, and this project has no CUDA path for it.

## Install the prerequisites

Do this before `install.sh` or `pip`. The installer checks that Python and ffmpeg already exist, and it stops if they do not.

### macOS

1. Install [Homebrew](https://brew.sh) if `brew` is not already a command.
2. Install Python and ffmpeg:

```bash
brew install python@3.12 ffmpeg
```

3. Confirm the machine:

```bash
uname -m
python3 --version
ffmpeg -version
ffprobe -version
```

`uname -m` must be `arm64`. `python3 --version` must be 3.11 or higher. Both `ffmpeg` and `ffprobe` must print a version. Homebrew's ffmpeg package includes ffprobe.

LectureDub looks for ffmpeg on `PATH`, then in `/opt/homebrew/bin`, then in `/usr/local/bin`. Opening the app from Finder still finds a Homebrew install in those two directories.

### Windows

1. Install Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/windows/). On the first installer page, turn on **Add python.exe to PATH**.
2. Install ffmpeg from PowerShell:

```powershell
winget install Gyan.FFmpeg
```

3. Close that terminal, open a new one, and confirm:

```powershell
python --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

`nvidia-smi` must print the GPU name and a driver version. If the command is missing, install the current NVIDIA Game Ready or Studio driver from NVIDIA's site and reboot. Installing the CUDA Toolkit alone does not replace the driver.

The CUDA build of PyTorch is installed later by `pip install ".[nvidia]"`. A separate CUDA Toolkit install is usually unnecessary.

If Windows has both the Microsoft Store Python stub and a real Python, `python --version` must be the real 3.11+ interpreter. The installer uses the `python` command it finds first.

### Linux

On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg
python3 --version
ffmpeg -version
ffprobe -version
nvidia-smi
```

`nvidia-smi` must list the card. Install the NVIDIA driver from your distribution before you continue. `python3-venv` is required because the installer creates `.venv` inside the clone.

On other distributions, install the same four things with that distribution's package manager: Python 3.11+, the venv module, pip, and ffmpeg (with ffprobe).

## Install LectureDub

Clone the repository:

```bash
git clone https://github.com/asher0913/lecturedub.git
cd lecturedub
```

### With the installer

macOS and Linux:

```bash
./install.sh
```

Windows PowerShell, from the cloned directory:

```powershell
.\install.ps1
```

If PowerShell refuses to run the script, run it once with:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The script does all of the following, and stops at the first failure:

1. On macOS it requires `arm64`. An Intel Mac exits with the message `Intel Macs are not supported.`
2. It requires `python3` (or `python` on Windows) at version 3.11 or newer.
3. It requires `ffmpeg` already on `PATH`. On a Mac it also accepts `/opt/homebrew/bin/ffmpeg`.
4. It creates `.venv` in the repository directory.
5. It upgrades pip inside that environment.
6. On Apple Silicon it installs the `apple` and `desktop` extras. On Windows and Linux it installs the `nvidia` and `desktop` extras.
7. It runs `lecturedub doctor`.
8. On Apple Silicon it writes `~/Applications/LectureDub.app` and prints that you can open LectureDub from the Applications folder. On Windows and Linux it prints the command that opens the window.

The `apple` extra is MLX: `mlx-qwen3-asr`, `mlx-lm`, and `mlx-audio`. The `nvidia` extra is PyTorch CUDA: `qwen-asr`, `qwen-tts`, `transformers`, `accelerate`, and `bitsandbytes`. The `desktop` extra is `pywebview`, which draws the native window. Shared libraries in every install are `soundfile`, `numpy`, and `yt-dlp`.

### By hand

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

Windows PowerShell uses `.\.venv\Scripts\Activate.ps1` instead of `source`.

Then install one extra set:

```bash
pip install -e ".[apple,desktop]"     # Apple Silicon
pip install -e ".[nvidia,desktop]"    # Windows or Linux with NVIDIA
lecturedub doctor
```

On a Mac you can add the Applications icon after that:

```bash
lecturedub install-app
```

`install-app` is a macOS bundle. On Windows or Linux the same command exits and tells you to run `lecturedub app`.

Leave out `desktop` if you only want the browser:

```bash
pip install -e ".[apple]"
# or
pip install -e ".[nvidia]"
lecturedub app --browser
```

### Without cloning

```bash
pip install "lecturedub[apple,desktop] @ git+https://github.com/asher0913/lecturedub.git"
```

```bash
pip install "lecturedub[nvidia,desktop] @ git+https://github.com/asher0913/lecturedub.git"
```

Use a virtualenv for this too. After it finishes, `lecturedub doctor` and `lecturedub app` are on that environment's `PATH`. `install.sh` is not part of this path; run `lecturedub install-app` yourself on a Mac if you want the Applications icon.

### Update an existing install

From the clone, with the same virtualenv active:

```bash
git pull
pip install -e ".[apple,desktop]"
```

Use `nvidia` instead of `apple` on Windows and Linux. On a Mac, run `lecturedub install-app` again so the Applications icon points at the updated command.

### Remove it

Delete the clone, including `.venv`. On a Mac, also delete `~/Applications/LectureDub.app`. Downloaded models remain in the Hugging Face cache until you delete that cache yourself. Finished videos remain wherever you saved them. The app's job folder is separate and is listed under [Files on disk](#files-on-disk).

## Check the installation

```bash
lecturedub doctor
```

If you used `install.sh` and did not activate `.venv`, call the environment directly:

```bash
.venv/bin/lecturedub doctor
```

Windows:

```powershell
.\.venv\Scripts\lecturedub doctor
```

A healthy Apple Silicon machine prints lines like:

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

A healthy NVIDIA machine prints `models: NVIDIA` and the card name from the driver, for example `models: NVIDIA GeForce RTX 4070`.

`doctor` returns exit code 0 when the GPU backend, ffmpeg, and the data directory are all usable. It returns 1 otherwise. Read the failing line:

| Printed line | What to do |
| --- | --- |
| `models: NVIDIA extra is missing...` | `pip install -e ".[nvidia,desktop]"` in the same virtualenv |
| `models: no NVIDIA GPU with CUDA...` | Make `nvidia-smi` work, then reinstall the `nvidia` extra so PyTorch is the CUDA build |
| `ffmpeg: missing` or `ffprobe: missing` | Install ffmpeg with the command printed on that line, open a new terminal, run doctor again |
| `window: browser only...` | Optional. `pip install -e ".[desktop]"` if you want a native window. The browser path still works |
| `data: cannot write ...` | The data directory is not writable. Set `LECTUREDUB_HOME` to a folder you can write, then run doctor again |
| `Intel Macs are not supported` | This is printed by `install.sh` before doctor. Use an Apple Silicon Mac, or a Windows or Linux machine with NVIDIA |

Doctor does not download models and does not need a video.

## Open the app

Three commands serve the same page. All of them listen only on `127.0.0.1`.

```bash
lecturedub app
lecturedub app --browser
lecturedub ui
```

| Command | What opens |
| --- | --- |
| `lecturedub app` | A native window, 980×780, titled LectureDub. Requires the `desktop` extra. If pywebview is missing, it says so and opens the browser instead |
| `lecturedub app --browser` | The system browser. No native window |
| `lecturedub ui` | The server only. It prints the URL and does not open a window or a browser |

The default port is 7860. If that port is taken, the server tries 7861, then the next port, and stops after 7879. Use the URL printed in the terminal, which looks like `lecturedub  http://127.0.0.1:7860`. Another machine on the network cannot connect.

Optional flags:

```bash
lecturedub app --port 9000
lecturedub app --voice Serena
lecturedub ui --port 9000 --voice Vivian
```

`--voice` is the default voice for jobs that do not pick one in the form. The form still has its own voice menu.

On a Mac, `install.sh` also creates **LectureDub** in the Applications folder (`~/Applications`, which is the Applications folder inside your home, not `/Applications`). The first launch may be blocked by Gatekeeper because the bundle is not notarized. Control-click the icon, choose **Open**, and confirm. The launcher puts `/opt/homebrew/bin` and `/usr/local/bin` on `PATH` so ffmpeg is visible, then runs `lecturedub app`. Closing the window stops the server.

Leave the terminal or the window open for the whole lecture. Closing it stops the job.

## Dub one lecture in the window

The page is in Chinese. This is what each control does.

| On screen | Meaning |
| --- | --- |
| 拖入视频 | Drop a video, or click the box and choose one. Accepted types include mp4, mkv, webm, and mov |
| 也可以只贴下面的链接。有英文字幕的话一并拖进来。 | You may paste a link instead. If you have an English `.srt` or `.vtt`, drop it in the same box |
| 视频链接 | An `http://` or `https://` URL. A direct media file, or a page yt-dlp can parse |
| 中文声音 | The Mandarin voice. The menu is described under [Voices](#voices) |
| 开始配音 | Start. The button is disabled while the upload is accepted, then you can queue another lecture |
| 正在转录 | Speech recognition |
| 正在翻译 | Translation into spoken Chinese. The fraction is batches finished, not seconds of video |
| 正在配音 | Speech synthesis. The fraction is lines finished, for example `120/380` |
| 正在封装 | The picture, the Chinese audio, and the subtitle are being written into the MP4 |
| 排队中 | Waiting for the lecture already running |
| 排队中，正在准备 | Running, before the first progress count exists. This is model load or download |
| 配音完成 | The MP4 exists |
| 下载视频 | Download `dubbed.mp4` |
| 中文字幕 | Download `dubbed.zh.srt` |
| 英文字幕 | Download `dubbed.en.srt` |
| 在 Finder 中显示 | On a Mac, reveal `dubbed.mp4` in Finder. On Linux, open the folder with `xdg-open`. On Windows, use the download links; that button calls `xdg-open`, which Windows does not have |

The footer says the video stays on this computer, the first run downloads models, one lecture usually takes tens of minutes, and a 16 GB machine should dub one lecture at a time. The version number is appended after the page loads.

Steps:

1. Drop the video into the dashed box. The filename replaces the hint text. Dropping an `.srt` or `.vtt` as well attaches it. A video file replaces a previous video. A subtitle file replaces a previous subtitle.
2. If the video is remote, paste the URL and leave the file box empty. A local file is used when both are present.
3. Choose the voice. **Uncle Fu** is the default.
4. Press 开始配音. The job title becomes the video filename without its extension, or `lecture` when you only pasted a URL. That title is also the hint given to speech recognition. See [Models](#models).
5. Watch the status line. The page refreshes every two seconds.
6. When it says 配音完成, download the three files or reveal the movie.

You can submit a second lecture while the first is running. It stays at 排队中 until the worker is free. There is one worker. Do not start a second `lecturedub app` at the same time on a 16 GB machine.

The first run spends a long time on 排队中，正在准备 while Hugging Face files download. Later runs reuse the cache. An 80-minute lecture is often a few hundred spoken lines, and speech is the slow part: on the order of 10 to 16 seconds per line after the model is loaded. Keep the computer awake. See [Keep the computer awake](#keep-the-computer-awake).

If the upload has no video and no URL, the server answers `drop a video or paste a link`, and the page shows that text. The Chinese fallback 没有收到视频 is used only when the server sends an empty error.

### Where the window stores the job

Each submission gets an id. Files for that id live under the data directory:

- macOS: `~/Library/Application Support/LectureDub/jobs/<id>/`
- Windows and Linux: `~/.lecturedub/jobs/<id>/`
- Or `$LECTUREDUB_HOME/jobs/<id>/` when that variable is set

Inside a finished job:

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

`out/video/` is what the download buttons serve. `video-dubbed/` is the working copy: the source, the English script, the Chinese script, one wav per line, and the mixed soundtrack. Those working files are large. After you have copied the three results out, you can delete that job folder.

The server also prints `jobs    <data directory>/jobs` when it binds the port.

## Dub one lecture from the terminal

Activate the virtualenv, or call `.venv/bin/lecturedub` (Windows: `.\.venv\Scripts\lecturedub`).

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4
lecturedub run lecture.mp4 --srt lecture.en.srt -o lecture-zh.mp4
lecturedub run "https://example.com/lecture.mp4" -o lecture-zh.mp4
lecturedub run lecture.mp4 -o lecture-zh.mp4 --voice Serena --title "Distributed systems, lecture 3"
```

`-o` / `--output` is required. It is the final MP4 path. The two subtitle files are written next to it, in a `video/` directory, using the stem of `-o`:

```text
~/Desktop/lecture-zh.mp4
~/Desktop/video/lecture-zh.zh.srt
~/Desktop/video/lecture-zh.en.srt
```

That layout comes from the command treating this one file as a course named `video`. The MP4 is then moved from `video/` onto the exact `-o` path. The subtitles stay in `video/`.

A full example, from a file on the Desktop, on a Mac:

```bash
cd ~/Desktop
caffeinate -dims ~/.path/to/lecturedub/lecturedub run "CS lecture.mp4" --srt "CS lecture.en.srt" -o "$HOME/Desktop/cs-lecture-zh.mp4" --voice Uncle_Fu
```

Use the real path of `lecturedub` inside `.venv`. When it exits, the terminal prints the MP4 path. Open that file in VLC or IINA and turn on the subtitle track 中英字幕.

### Every `run` option

| Option | Default | Meaning |
| --- | --- | --- |
| `video` | required | Local path, or an `http://` / `https://` URL |
| `-o`, `--output` | required | Final MP4 path. The parent directory is created if needed |
| `--srt` | none | English `.srt` or `.vtt`, as a path or a URL. When this is present and readable, speech recognition is skipped |
| `--title` | the stem of `-o` | Passed to speech recognition as a glossary hint. Ignored for the soundtrack when you already passed a good `--srt` |
| `--voice` | `Uncle_Fu` | One of the names in [Voices](#voices) |
| `--work` | `work/jobs` | Working directory for this run, relative to the current directory unless you pass an absolute path |

Progress is printed to the terminal and appended to `<work>/dub.log`. A machine-readable snapshot is `<work>/progress.json`, with `stage` of `asr`, `translate`, or `voice`, plus `done` and `total` during translation and speech.

The working job directory is `<work>/video-<stem>/`, where `<stem>` is the stem of `-o`. It holds `source.mp4`, `segments.json`, `clips/`, and `dub.wav`. See [Files on disk](#files-on-disk).

## Dub many lectures

Put the lectures in a JSON list. A copy of this shape is in `examples/batch.example.json`.

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

`video` may also be spelled `videoUrl`. A value that starts with `http://` or `https://` is downloaded. Anything else is a local path. `srt` is the same: a URL is fetched, a path is read. If `srt` is omitted and `captions` is a list, the `url` of the first caption is used.

`title` is the human name and the speech-recognition hint. `slug` is the filename. It is forced to letters, digits, `.`, `_`, and `-`, and cut at 80 characters. When `slug` is omitted, the title is slugified. `course` is the output subdirectory. When it is omitted, the subdirectory is `video`. The job key is `course-slug`, or just `slug` when there is no course.

Optional download checks:

| Field | Meaning |
| --- | --- |
| `duration` | Expected length in seconds. A download that differs by more than 4 seconds is rejected |
| `bandwidth` | Bits per second. Together with `duration`, the file must reach about 82% of the expected size before it counts as complete |

```bash
lecturedub batch manifest.json --output-dir output
```

Finished files:

```text
output/cs101/lecture-1.mp4
output/cs101/lecture-1.zh.srt
output/cs101/lecture-1.en.srt
output/video/lecture-2.mp4
output/video/lecture-2.zh.srt
output/video/lecture-2.en.srt
```

Lectures run one after another. A lecture whose output MP4 already matches the source duration within 5 seconds is skipped. The log line looks like `0 lecture(s) to dub, 2 already done`.

### Every `batch` option

| Option | Default | Meaning |
| --- | --- | --- |
| `manifest` | required | JSON file. A bare list, or an object with a `jobs` or `items` array |
| `--output-dir` | `output` | Where the MP4 and the two SRT files are copied |
| `--work-dir` | `work/lectures` | One subdirectory per lecture, named by the job key |
| `--voice` | `Uncle_Fu` | Voice for every lecture in this run |
| `--only` | none | Keep lectures whose key or title contains this substring |
| `--pilot-seconds` | none | Dub only the opening of the first matched lecture, for this many seconds. The result is a pilot file in the work directory, and the lecture is not marked finished |
| `--no-download` | off | Do not fetch URLs. Use `source.mp4` and `en.orig.srt` already in the work directory |
| `--translate-only` | off | Write `segments.json` and stop before speech |

Related commands use the same manifest:

```bash
lecturedub fetch manifest.json --work-dir work/lectures --output-dir output
lecturedub batch manifest.json --output-dir output --translate-only
lecturedub batch manifest.json --output-dir output --only "Lecture 1" --pilot-seconds 60
lecturedub mux manifest.json --output-dir output --work-dir work/lectures
```

`fetch` downloads video and any subtitle URL. It does not load a model. `mux` packs a lecture that already has `dub.wav`, `segments.json`, and `source.mp4`. Use it when speech finished and packing did not. `--pilot-seconds` always stops after the first lecture in the filtered list, even if later rows would also have matched.

With `--no-download`, lectures that already have an English subtitle are dubbed. If the same run also contains a lecture that still needs recognition, that recognition waits for a later run that does not also include a captioned lecture. The log says `defer transcription until captioned lectures are done`.

Batch logs go to `dub.log` beside the work directory when the work directory is named `lectures` (the default). Otherwise the log is inside the work directory.

## How one lecture is processed

The same sequence runs for the window, `run`, and `batch`.

1. **Video.** A local file is copied to `source.mp4` in the job directory. A URL that looks like a media file is downloaded directly. Any other URL is handed to yt-dlp. A file under 200 KB is rejected. If the manifest gave `duration` or `bandwidth`, those checks run too.
2. **English text.** A provided `.srt` or `.vtt` is stored as `en.orig.srt`. Subtitle cues are parsed, then merged into speakable phrases. A phrase breaks on a pause longer than 0.55 seconds, at a sentence end once the phrase is at least 3.2 seconds, or at 16 seconds, whichever comes first.
3. **Recognition, only when there is no usable subtitle.** The soundtrack is extracted to `audio16k.wav` at 16 kHz. Qwen3-ASR writes timed English. On NVIDIA, Qwen3-ForcedAligner supplies the word times; the library chunks a long file itself. Word times are joined into phrases of at most 12 seconds, also breaking after `.`, `?`, or `!`, or after a gap of 0.8 seconds. The title chooses a glossary: if it contains `511`, `c-store`, `cstore`, `dremel`, `snowflake`, `system r`, `pregel`, or `kafka`, the hint is a data-management lecture; otherwise the hint is a distributed-systems lecture. After recognition, the MLX model is unloaded before translation starts.
4. **A speech-rate sample.** The voice model speaks one fixed Chinese sentence, the length of that clip sets how many characters fit in a second, and the model is unloaded again. If the sample is slower than 4.2 or faster than 6.5 units per second, the planner uses 4.5. A unit is one Chinese character, or two units per Latin word. This number is only a budget for the translator.
5. **Translation.** Qwen3-8B rewrites each phrase into spoken Simplified Chinese. It sees the previous phrase, the next phrase, the duration, and a character budget. It is asked not to add facts, not to finish an English sentence that stopped mid-thought, and not to drop a later clause. Batches are 12 phrases. Results are saved in `segments.json` as they go, so a restart continues from the phrases that already have Chinese.
6. **Speech.** The voice model loads again and speaks each Chinese line on its own. A line whose text already has a wav larger than 800 bytes is reused. Each line is placed at its original start time.
7. **Packing.** The line clips are mixed into one timeline, loudness-normalized, and muxed. The picture stream is copied. The Chinese audio becomes AAC. The bilingual subtitle becomes a `mov_text` track. `dubbed.mp4`, `zh.srt`, and `en.fixed.srt` are then copied to the output names.

The window's status names match steps 3, 5, 6, and 7: 正在转录, 正在翻译, 正在配音, 正在封装.

## How the timing works

For each line, the slot is the time until the next line starts, minus 0.03 seconds. The last line's slot runs to the end of the video.

The raw recording is trimmed: samples below 0.012 are treated as silence, and 0.04 seconds of padding is kept on each side. A 12 ms fade is applied to both ends so clips do not click.

If the clip is longer than the slot, it is sped up with a pitch-preserving `atempo`, at most 1.16×. Audio that is still longer is cut at the slot boundary. A slot of 0.15 seconds or less becomes a short silence instead of speech. When a raw clip was longer than 1.16 times the slot, a row is appended to `clips/fit.log`:

```text
<line id>    <raw seconds>    <slot seconds>
```

That row means the end of that line was cut. Shorten the Chinese for that id in `segments.json`, delete the matching wav in `clips/`, delete the finished MP4 so the lecture is no longer considered done, and run it again. Only the changed line is spoken again.

A line whose Chinese does not end in `。`, `！`, `？`, or `…` is spoken with a flat, unfinished tone, so a sentence that continues in the next cue does not sound like it ended.

Loudness of the mixed track is normalized to about −16 LUFS integrated, with a true peak near −1.5 dBTP and a loudness range of 11. If normalization fails, the un-normalized mix is used.

## Voices

The window offers three Qwen3 custom voices. The command line uses the same names.

| Name | In the window | Character |
| --- | --- | --- |
| `Uncle_Fu` | Uncle Fu · 低沉男声，适合讲课 | Lower male voice. This is the default, and the one meant for lecturing |
| `Serena` | Serena · 温和女声 | Softer female voice |
| `Vivian` | Vivian · 明亮女声 | Brighter female voice |

Every line is spoken with this instruction: a calm, clear Mandarin lecture, steady pace, like a university classroom recording, without performance and without a drawn-out delivery. The voice is chosen per job. A batch run uses one voice for the whole manifest.

## Models

All three stages are Qwen3. Apple Silicon loads the MLX weights. NVIDIA loads the PyTorch weights. You can override the id with an environment variable. Leave them unset unless you have a reason to change them.

| Stage | Apple Silicon | NVIDIA | Variable |
| --- | --- | --- | --- |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B` | `Qwen/Qwen3-ASR-1.7B`, plus `Qwen/Qwen3-ForcedAligner-0.6B` for word times | `LECTUREDUB_ASR` |
| Translation | `mlx-community/Qwen3-8B-4bit` | `Qwen/Qwen3-8B`. 4-bit when VRAM is under 18 GB | `LECTUREDUB_LLM` |
| Chinese speech | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `LECTUREDUB_TTS` |

Rough download size, so you can judge the first run: the 1.7B recognizer is about 4 GB, the 0.6B aligner is about 1.5 GB and is NVIDIA-only, Qwen3-8B in 4-bit is about 5 GB, Qwen3-8B in 16-bit is about 16 GB, and the 1.7B voice is about 4 GB. Apple Silicon therefore downloads on the order of 13 GB. An NVIDIA card under 18 GB is similar, plus the aligner. A card with 18 GB or more may download the larger 16-bit translator instead of the 4-bit weights.

NVIDIA inference uses bfloat16 when the GPU supports it, and float16 otherwise. The speech model samples at a temperature of 0.5. Translation is greedy. Public Hugging Face downloads do not need an account. If a download is rate-limited, a Hugging Face token in `HF_TOKEN` is the usual fix. A slow connection can use a mirror:

```bash
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="$HOME/huggingface-cache"
lecturedub app
```

Windows PowerShell:

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HF_HOME = "$HOME\huggingface-cache"
lecturedub app
```

`HF_HOME` moves the cache. Set it before the first run if the default disk is small.

## Environment variables

| Variable | Default | Effect |
| --- | --- | --- |
| `LECTUREDUB_BACKEND` | `mlx` on Apple Silicon, `cuda` otherwise | Force `mlx` or `cuda` |
| `LECTUREDUB_CUDA_DEVICE` | `cuda:0` | Which NVIDIA device to use, for example `cuda:1` |
| `LECTUREDUB_ASR` | the table above | Recognizer model id |
| `LECTUREDUB_LLM` | the table above | Translator model id |
| `LECTUREDUB_TTS` | the table above | Voice model id. On CUDA, an MLX model id is remapped to the CUDA voice |
| `LECTUREDUB_MEM_GB` | `6.5` | MLX memory cap, in gigabytes. The speech model needs about 5 GB of that |
| `LECTUREDUB_CACHE_MB` | `256` | MLX cache cap, in megabytes |
| `LECTUREDUB_HOME` | the platform data directory | Where the window stores jobs |
| `HF_HOME` | `~/.cache/huggingface` | Hugging Face cache location |
| `HF_ENDPOINT` | the official Hub | Download mirror |
| `HF_TOKEN` | none | Hub token if a download asks you to sign in |

Set them in the same terminal that starts `lecturedub`. The macOS Applications icon does not see variables you exported in some other terminal. To change those, start the app from the terminal with `lecturedub app`.

## Files on disk

Data directory, for the window:

| System | Path |
| --- | --- |
| macOS | `~/Library/Application Support/LectureDub` |
| Windows | `C:\Users\<you>\.lecturedub` |
| Linux | `~/.lecturedub` |

Command-line working files depend on `--work` or `--work-dir`. For one `run` with the defaults, after `-o lecture-zh.mp4`:

```text
work/jobs/dub.log
work/jobs/progress.json
work/jobs/video-lecture-zh/source.mp4
work/jobs/video-lecture-zh/en.orig.srt
work/jobs/video-lecture-zh/audio16k.wav          # only if recognition ran
work/jobs/video-lecture-zh/segments.json
work/jobs/video-lecture-zh/zh.srt
work/jobs/video-lecture-zh/en.fixed.srt
work/jobs/video-lecture-zh/clips/00000-aaaaaaaaaa.wav
work/jobs/video-lecture-zh/clips/fit.log         # only if some line was cut
work/jobs/video-lecture-zh/dub.raw.wav
work/jobs/video-lecture-zh/dub.wav
work/jobs/video-lecture-zh/dubbed.mp4
```

`segments.json` is a list of `{id, start, end, en, zh}`. `id` matches the clip prefix. `start` and `end` are seconds. `en` is the English that was translated. `zh` is the line that will be spoken.

For `batch`, replace `work/jobs/video-lecture-zh` with `work/lectures/<course>-<slug>`.

These directories are gitignored in a clone: `.venv/`, `work/`, `output/`, `models/`, and media files (`*.mp4`, `*.wav`, `*.mov`, `*.mkv`). Do not commit lectures or model weights.

## Time, memory, and disk

Speech is one line at a time, on one GPU. Two speech processes do not finish sooner. On a 16 GB machine they can crash the GPU. The window already serializes jobs. Do not start a second terminal job while the window is speaking.

A usable planning rate is 10 to 16 seconds of wall clock per spoken line, after the model is in memory. A lecture of 400 lines is therefore about 70 to 110 minutes of speech, plus translation. Translation of those 400 lines is much shorter than the speech, often a few minutes once the 8B model is loaded. Recognition of a caption-less 80-minute file is another several minutes. The first run adds the model download, which is limited by your connection.

Packing is short. Copying the video stream does not re-encode the picture. An 80-minute file usually packs in a few minutes, depending on disk speed.

The speech model holds about 5 GB. `LECTUREDUB_MEM_GB` defaults to 6.5 so a 16 GB Mac still has room for the system. Close other large apps before a long lecture. NVIDIA cards under 18 GB run the translator in 4-bit. If `bitsandbytes` is missing, translation stops with an error that names it, rather than trying to load a 16-bit 8B model into that card.

Working audio is uncompressed while it is being built. `dub.raw.wav` and the clip folder can be several gigabytes for a long lecture. The finished MP4 is about the size of the original video, because the picture was copied and the audio is 128 kbps.

## Run a lecture again

A batch or `run` skips a lecture when the output MP4 exists and its duration is within 5 seconds of `source.mp4`. If the source file has already been deleted, any existing output MP4 counts as finished.

To redo a whole lecture, delete that output MP4, then run the same command. Existing clip wavs are reused, so lines whose Chinese did not change are not spoken again.

To redo one line:

1. Edit `zh` for that `id` in `segments.json`. Keep the JSON valid. Do not change `id`, `start`, or `end` unless you mean to move the cue.
2. Delete the wav in `clips/` whose name starts with that id, for example `00122-`. The filename contains a hash of the Chinese text and the tone instruction, so the old file would not match anyway, but deleting it avoids confusion.
3. Delete the output MP4, so the job is not skipped.
4. Run the same command.

`--translate-only` rewrites missing Chinese and leaves speech for a later run. `--pilot-seconds 60` is the way to hear the opening before committing to the full file. The pilot is stored in the work directory as `pilot.mp4` and does not replace the output.

## Subtitles, audio, and the finished file

The embedded subtitle is one `mov_text` track:

- Language tag `zho`
- Track title `中英字幕`
- Default disposition, so a player that honors the flag shows it without an extra click
- Each cue is the Chinese line, a newline, then the English line
- The file is written with `+faststart`, so it can start playing before it is fully copied over a network

The Chinese audio track:

- AAC-LC
- 128 kbps
- 44100 Hz
- Stereo
- Language tag `zho`
- Loudness about −16 LUFS, true peak about −1.5 dBTP

The video track is whatever the source used. Width, height, and codec stay as they were. There is no second audio track.

`zh.srt` and `en.srt` use normal SRT timestamps (`HH:MM:SS,mmm`) and the same cue boundaries as the embedded track. You can hand either file to a player that ignores `mov_text`.

## Play the result

VLC and IINA both show the embedded track. In VLC, use Subtitle and select the track named 中英字幕. IINA lists it in the subtitle menu. If a player hides the embedded track, load the `.zh.srt` or the bilingual file next to the video. mpv will pick up a similarly named subtitle in some layouts; if it does not, pass the srt explicitly.

QuickTime sometimes shows `mov_text` and sometimes does not, depending on the macOS version. When it does not, use VLC or IINA, or load the SRT.

The Chinese and English of one cue are two lines of the same subtitle, so they appear together at the bottom. There is no separate style for the English line. Burned-in captions are not produced.

## Keep the computer awake

Sleep interrupts a long speech run. The clips already written are kept, and the next run of the same job continues, but you lose the time until you notice.

macOS, wrapping a terminal job:

```bash
caffeinate -dims lecturedub run lecture.mp4 -o lecture-zh.mp4
```

`-dims` asks the system not to idle-sleep the display, the system, or the disk. Plug the machine in. A 16 GB laptop on battery can hit memory pressure and kill the speech process.

Windows: Settings, System, Power, and set sleep to Never while the job runs. Linux: `systemd-inhibit --what=idle:sleep lecturedub run lecture.mp4 -o lecture-zh.mp4`, or your desktop's power settings.

## Troubleshooting

**Doctor says the NVIDIA extra is missing.**  
You installed the base package or the `apple` extra. From the virtualenv, run `pip install -e ".[nvidia,desktop]"`.

**Doctor says there is no NVIDIA GPU with CUDA.**  
`nvidia-smi` must succeed in the same terminal. Then reinstall so pip fetches the CUDA wheel of PyTorch rather than a CPU wheel. A driver-only failure is fixed by installing the current NVIDIA driver and rebooting.

**`ffmpeg: missing` when you opened the Mac app from Finder.**  
Doctor looks in `/opt/homebrew/bin` and `/usr/local/bin` as well as `PATH`. If ffmpeg is somewhere else, symlink it into one of those, or start with `lecturedub app` from a terminal where `ffmpeg -version` works. The error `ffmpeg and ffprobe are required. Install them with: brew install ffmpeg` is the runtime message on every system; on Windows or Linux, use the install command from [Install the prerequisites](#install-the-prerequisites).

**The page stays on 排队中，正在准备.**  
The model is loading or downloading. Look at the terminal that launched the app. A Hugging Face progress bar there means the first-run download is still going. Set `HF_ENDPOINT` if the Hub is slow from your network.

**The process stops with a Metal error, or the machine runs out of memory.**  
Quit the second copy. One speech model at a time. Close browsers and other GPU apps. On a Mac, `LECTUREDUB_MEM_GB=6.5` is the default cap; raising it on a 16 GB machine leaves less room for the system.

**Translation says this GPU has less than 18 GB.**  
Install `bitsandbytes` by reinstalling the `nvidia` extra. The 4-bit path is automatic once that package imports.

**The URL fails or the download is tiny.**  
A direct file URL is fetched as a file. A page URL goes through yt-dlp, which must support that site. A download under 200 KB, or one whose duration misses the manifest `duration` by more than 4 seconds, is discarded. Download the video yourself and pass the local path.

**The finished video has no Chinese audio.**  
The job did not reach packing. Check `dub.log` for the last `voice` or `done` line. If `dub.wav` exists and `source.mp4` exists, `lecturedub mux manifest.json` packs without speaking again.

**A sentence is cut off, and the next one starts on time.**  
That line was longer than the slot even after the 1.16× speedup. `clips/fit.log` lists those ids. Follow [Run a lecture again](#run-a-lecture-again) for that id.

**The whole lecture is skipped and the old file is unchanged.**  
The output MP4 is still considered finished. Delete it if you want a new one. The working clips are reused for lines you did not edit.

**Port 7860 is in use.**  
The server moves to the next port, up to 7879, and prints the URL. Pass `--port` to choose one. Only `127.0.0.1` is bound.

**The Mac app is damaged or cannot be opened.**  
Control-click `LectureDub` in `~/Applications` and choose Open. The bundle is generated on your machine and is not notarized by Apple. `LSMinimumSystemVersion` is 13.0.

**Windows will not run `install.ps1`.**  
`powershell -ExecutionPolicy Bypass -File .\install.ps1` from the clone. The script still requires `python` and `ffmpeg` on `PATH`.

**The reveal button does nothing on Windows.**  
The button always runs Finder's `open -R` on a Mac and `xdg-open` elsewhere. Use 下载视频, 中文字幕, and 英文字幕. The files are still in the data directory from [Files on disk](#files-on-disk).

## Privacy

Speech recognition, translation, and speech synthesis do not send the lecture to a project server. The window binds `127.0.0.1` only. A URL you paste is downloaded by this machine, either directly or through yt-dlp, from the site in that URL. Model weights are downloaded from Hugging Face, or from `HF_ENDPOINT` if you set one, into the local cache.

Job files, finished videos, and the virtualenv are not part of the git repository. Do not put lecture media, account tokens, or `HF_TOKEN` into a commit.

## Limits

- English lectures into spoken Simplified Chinese. Other language pairs are not a mode in this version.
- Apple Silicon through MLX, or NVIDIA through CUDA. Intel Macs, AMD GPUs, and CPU-only machines are outside the installers.
- One lecture occupies the GPU until its speech pass finishes. The queue does not split a lecture across two devices.
- A line that cannot fit after a 1.16× speedup loses its ending. The following line is not delayed.
- The original English soundtrack is replaced, not ducked under the Chinese.
- Subtitles are soft. Players that ignore `mov_text` need the SRT files.
- The window text is Chinese in this version.
- `lecturedub doctor` and the unit tests do not load the models. A successful test run means the routing and the subtitle timing code are intact. It does not mean a particular GPU has already downloaded the weights.

## Development

From a clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[apple,desktop,dev]"
python -m pytest
```

On NVIDIA, install `".[nvidia,desktop,dev]"` instead. The tests do not download models and do not need a GPU. They check subtitle parsing, phrase grouping, the aligner result shape, and that a job is sent to the MLX path or the CUDA path according to `LECTUREDUB_BACKEND`.

The package layout that matters:

| Path | Role |
| --- | --- |
| `lecturedub/__main__.py` | The `lecturedub` command |
| `lecturedub/pipeline.py` | Download, recognize, translate, speak, pack |
| `lecturedub/asr.py` | Qwen3-ASR on MLX and on CUDA |
| `lecturedub/translate.py` | Qwen3-8B translation and the length checks |
| `lecturedub/voice.py` | Qwen3-TTS and the 1.16× fit |
| `lecturedub/media.py` | ffmpeg download, loudness, and mux |
| `lecturedub/subtitles.py` | SRT and VTT parsing, phrase grouping |
| `lecturedub/runtime.py` | MLX versus CUDA, default model ids |
| `lecturedub/web.py` | The local HTTP server and the one-job queue |
| `lecturedub/desktop.py` | The native window, `LectureDub.app`, and doctor |
| `lecturedub/static/index.html` | The page the window shows |
| `install.sh`, `install.ps1` | Virtualenv installers |
| `examples/batch.example.json` | A two-lecture manifest |

`pyproject.toml` names the author as Yixuan Zhang and the license as MIT. The console script is `lecturedub`.

## License

MIT License. Copyright (c) 2026 Yixuan Zhang.

You can use, copy, modify, and distribute this project under the terms in `LICENSE`. The lecture files you dub are yours. They are not included in this repository, and the license does not grant any rights to them.
