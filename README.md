# lecturedub

把一节英文课，做成时间轴对齐的中文配音视频。模型在 Apple Silicon 的 GPU 上本地运行，视频不用上传。

Drop in an English lecture, or paste a link. The tool transcribes it, rewrites it as spoken Chinese, synthesizes a voice on the original timestamps, and replaces the English soundtrack.

## What it does

1. Reads a video file, a direct media URL, or a page URL that yt-dlp understands.
2. Uses an English subtitle file when you have one. Otherwise it transcribes with Qwen3-ASR.
3. Corrects the English and rewrites each phrase as spoken Chinese with Qwen3.
4. Speaks the Chinese with Qwen3-TTS, then fits each phrase to the original timing.
5. Writes a new MP4: the original picture is copied, the English soundtrack is replaced with Chinese speech, and one subtitle track shows Chinese and English together. Separate `.zh.srt` and `.en.srt` files are written next to the video.

## Requirements

- Apple Silicon Mac. MLX runs the models on the GPU.
- 16 GB of memory is enough for the default models if stages run one at a time. More memory lets you switch in larger models.
- ffmpeg (`brew install ffmpeg`)
- Python 3.11+

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The first run downloads the models from Hugging Face.

## Use the app

```bash
lecturedub ui
```

Open http://127.0.0.1:7860 and drop a video, or paste a link. If you already have English subtitles, drop the `.srt` or `.vtt` file too.

## Use the command line

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

Chinese lines are written to a length that matches the original phrase. Each clip is placed at the original start time. Small gaps stay silent. If a line still runs long, it is sped up slightly, and never enough to sound like a chipmunk. The picture is copied, not re-encoded.

## Privacy

Recognition, translation, and speech all run on this computer. The tool does not upload your lectures. Downloaded media and finished videos stay in `work/` and `output/`, which are gitignored.
