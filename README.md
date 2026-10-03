# lecturedub

把一节英文课做成时间轴对齐的中文配音视频。模型在 Apple Silicon 的 GPU 上本地运行，视频不会上传。

Drop in an English lecture, or paste a link. The tool transcribes it, rewrites it as spoken Chinese, synthesizes a voice on the original timestamps, and replaces the English soundtrack. The picture is copied as-is.

## Install

Apple Silicon Mac, Python 3.11+, and ffmpeg.

```bash
git clone https://github.com/asher0913/lecturedub.git
cd lecturedub
./install.sh
```

`install.sh` creates a virtualenv, installs the desktop window, and puts **LectureDub** in your Applications folder. Open that app and drop a video on the window.

The first run downloads the models from Hugging Face. One lecture usually takes several tens of minutes. On a 16 GB Mac, dub one lecture at a time.

You can also install the command into an existing environment:

```bash
pip install "lecturedub[desktop] @ git+https://github.com/asher0913/lecturedub.git"
lecturedub doctor
lecturedub install-app
lecturedub app
```

Without the desktop extra, `lecturedub app --browser` opens the same interface in a browser.

## Desktop app

The window is the whole interface: drop a video, or paste a link, and optionally add an English `.srt` or `.vtt`. Choose a voice and start. Finished videos are saved on this Mac. Use **在 Finder 中显示** to jump to the file.

```bash
lecturedub app
lecturedub app --browser
lecturedub ui
```

`lecturedub ui` only serves the page. `lecturedub app` opens a native window when `pywebview` is installed.

Jobs from the app are stored in `~/Library/Application Support/LectureDub/jobs`.

## Command line

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4
lecturedub run lecture.mp4 --srt lecture.en.srt -o lecture-zh.mp4
lecturedub run "https://example.com/lecture.mp4" -o lecture-zh.mp4
lecturedub batch examples/batch.example.json --output-dir output
```

A batch manifest is a JSON list:

```json
[
  {"title": "Lecture 1", "video": "lecture.mp4", "srt": "lecture.en.srt"},
  {"title": "Lecture 2", "video": "https://example.com/lecture.mp4"}
]
```

`video` and `srt` can each be a filesystem path or an `http` URL.

## What it does

1. Reads a video file, a direct media URL, or a page URL that yt-dlp understands.
2. Uses an English subtitle file when you have one. Otherwise it transcribes with Qwen3-ASR.
3. Corrects the English and rewrites each phrase as spoken Chinese with Qwen3.
4. Speaks the Chinese with Qwen3-TTS, then fits each phrase to the original timing.
5. Writes a new MP4: the original picture is copied, the English soundtrack is replaced with Chinese speech, and one subtitle track shows Chinese and English together. Separate `.zh.srt` and `.en.srt` files are written next to the video.

## Voices

The default voice is `Uncle_Fu`, a low Mandarin voice that suits a lecture. `Serena` and `Vivian` are the other built-in Chinese voices.

```bash
lecturedub run lecture.mp4 -o lecture-zh.mp4 --voice Serena
```

## Models

Defaults are the strongest downloadable models for each stage, at full precision:

| Stage | Model | Override |
| --- | --- | --- |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B` | `LECTUREDUB_ASR` |
| Translation | `mlx-community/Qwen3-8B-4bit` | `LECTUREDUB_LLM` |
| Chinese speech | `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` | `LECTUREDUB_TTS` |

## Timing

Chinese lines are written to a length that matches the original phrase. Each clip is placed at the original start time. Small gaps stay silent. If a line still runs long, it is sped up slightly, and never enough to sound like a chipmunk.

## Privacy

Recognition, translation, and speech all run on this computer. The tool does not upload your lectures. Command-line jobs use the `work/` directory you pass in. The desktop app uses `~/Library/Application Support/LectureDub`.

## Develop

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[desktop,dev]"
python -m pytest
```
