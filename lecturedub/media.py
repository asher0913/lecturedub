"""Download, probe, and mux media with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    brew = Path(f"/opt/homebrew/bin/{name}")
    if brew.exists():
        return str(brew)
    return name


FFMPEG = _tool("ffmpeg")
FFPROBE = _tool("ffprobe")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class MediaError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    if not Path(FFMPEG).exists() or not Path(FFPROBE).exists():
        raise MediaError("ffmpeg and ffprobe are required. Install them with: brew install ffmpeg")


def duration_of(path: Path) -> float:
    result = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr.strip() or f"ffprobe failed for {path}")
    return float(result.stdout.strip())


def _looks_like_html(path: Path) -> bool:
    with path.open("rb") as handle:
        head = handle.read(64).lstrip().lower()
    return head.startswith(b"<!doctype") or head.startswith(b"<html") or head.startswith(b"{")


def download(url: str, dest: Path, referer: str = "https://mediaspace.illinois.edu/") -> None:
    """Resume a direct HTTP download. Rejects HTML error pages."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size < 64:
        dest.unlink()
    command = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "8",
        "--retry-all-errors",
        "--retry-delay",
        "2",
        "--speed-limit",
        "30000",
        "--speed-time",
        "25",
        "-C",
        "-",
        "-A",
        UA,
        "-e",
        referer,
        "-o",
        str(dest),
        url,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr.strip() or f"download failed: {dest.name}")
    if not dest.exists() or dest.stat().st_size < 32 or _looks_like_html(dest):
        if dest.exists():
            dest.unlink()
        raise MediaError(f"download for {dest.name} did not return media")


def download_text(url: str) -> str:
    result = subprocess.run(
        ["curl", "-fsSL", "--retry", "4", "-A", UA, "-e", "https://mediaspace.illinois.edu/", url],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr.decode("utf-8", "replace").strip() or "subtitle download failed")
    return result.stdout.decode("utf-8", "replace")


def download_with_ytdlp(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "yt-dlp",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "-o",
        str(dest),
        url,
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0 or not dest.exists():
        raise MediaError(f"yt-dlp could not download {url}")


def is_direct_file_url(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return path.endswith((".mp4", ".mkv", ".webm", ".mov", ".m4v", ".mp3", ".wav", ".m4a"))


def extract_wav(src: Path, dest: Path, sample_rate: int = 16000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(dest),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr[-500:])


def write_timeline_wav(samples, sample_rate: int, dest: Path) -> None:
    import soundfile as sf

    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), samples, sample_rate, subtype="PCM_16")


def loudnorm(src: Path, dest: Path) -> None:
    result = subprocess.run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(src),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a",
            "pcm_s16le",
            str(dest),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr[-400:])


def video_size(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or "x" not in result.stdout:
        raise MediaError(result.stderr[-300:] or "could not read video size")
    width, height = result.stdout.strip().split("x", 1)
    return int(width), int(height)


def output_frame_size(width: int, height: int) -> tuple[int, int]:
    """1080p is enough. Never upscale, and keep even dimensions for H.265."""
    if height > 1080:
        scaled = 1080 / height
        width = int(width * scaled)
        height = 1080
    width -= width % 2
    height -= height % 2
    return max(width, 2), max(height, 2)


def mux(
    video: Path,
    audio: Path,
    subtitle: Path,
    dest: Path,
    english: Path | None = None,
    caption_lines: list | None = None,
) -> None:
    """Copy the downloaded picture and attach the Chinese voice plus bilingual subtitles.

    The picture is not re-encoded. Chinese and English sit on one subtitle track
    so a player can show both at the bottom. Separate .zh.srt and .en.srt files
    are still written beside the video by the caller.
    """
    del english
    dest.parent.mkdir(parents=True, exist_ok=True)
    if caption_lines:
        from .subtitles import Cue, write_srt

        cues = []
        for line in caption_lines:
            zh = str(getattr(line, "zh", "") or "").strip()
            en = str(getattr(line, "en", "") or "").strip()
            text = zh if not en else f"{zh}\n{en}"
            if not text:
                continue
            cues.append(Cue(float(line.start), float(line.end), text))
        if not cues:
            raise MediaError("mux needs caption lines")
        subtitle = dest.with_name(f"{dest.stem}.bilingual.srt")
        write_srt(cues, subtitle)
    if not subtitle or not Path(subtitle).exists():
        raise MediaError("mux needs a subtitle file")
    # AAC-LC matches the Media Space soundtrack. The picture stays the original H.264.
    command = [
        FFMPEG,
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-i",
        str(subtitle),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-map",
        "2:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:s",
        "mov_text",
        "-metadata:s:a:0",
        "language=zho",
        "-metadata:s:s:0",
        "language=zho",
        "-metadata:s:s:0",
        "title=中英字幕",
        "-disposition:s:0",
        "default",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-1200:])


def atempo(samples, sample_rate: int, factor: float):
    """Pitch-preserving time stretch. factor > 1 makes the clip shorter."""
    import numpy as np

    factor = float(factor)
    if abs(factor - 1.0) < 0.03:
        return samples.astype(np.float32, copy=False)
    pieces = []
    remaining = factor
    while remaining > 2.0:
        pieces.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        pieces.append("atempo=0.5")
        remaining /= 0.5
    pieces.append(f"atempo={remaining:.5f}")
    result = subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-filter:a",
            ",".join(pieces),
            "-f",
            "f32le",
            "-ac",
            "1",
            "pipe:1",
        ],
        input=np.ascontiguousarray(samples, dtype=np.float32).tobytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr.decode("utf-8", "replace")[-300:])
    return np.frombuffer(result.stdout, dtype=np.float32).copy()
