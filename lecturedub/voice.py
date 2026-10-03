"""Chinese lecture speech and timestamp fitting."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .media import atempo
from .subtitles import speakable_units
from .translate import Line

DEFAULT_TTS = "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16"
DEFAULT_VOICE = "Uncle_Fu"
INSTRUCT = "用沉稳清晰的普通话讲课，语速平稳，像大学课堂录音，不要表演，不要拖腔。"
CONTINUATION = INSTRUCT + "这句还没说完，语调保持平，不要用降调收尾。"
CALIBRATION = (
    "今天我们继续看分布式系统。当一个节点失败的时候，"
    "其他副本要能够接管它的工作，并且不能把已经确认的写入丢掉。"
)


def configure_metal() -> None:
    import os

    import mlx.core as mx

    # One voice is about 5 GB. A 6.5 GB cap leaves room for a second voice on 16 GB.
    mem = int(float(os.environ.get("LECTUREDUB_MEM_GB", "6.5")) * 1024**3)
    cache = int(os.environ.get("LECTUREDUB_CACHE_MB", "256")) * 1024**2
    for call in (
        lambda: mx.set_memory_limit(mem),
        lambda: mx.set_cache_limit(cache),
        lambda: mx.metal.set_memory_limit(mem),
        lambda: mx.metal.set_cache_limit(cache),
    ):
        try:
            call()
        except Exception:
            pass


def release_memory() -> None:
    import gc

    import mlx.core as mx

    gc.collect()
    try:
        mx.clear_cache()
    except Exception:
        pass
    try:
        mx.metal.clear_cache()
    except Exception:
        pass


def _as_audio(value) -> np.ndarray:
    audio = np.array(value, dtype=np.float32).reshape(-1)
    return np.ascontiguousarray(audio)


def _trim(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    if audio.size == 0:
        return audio
    hot = np.flatnonzero(np.abs(audio) > 0.012)
    if hot.size == 0:
        return audio[: int(sample_rate * 0.05)]
    pad = int(sample_rate * 0.04)
    start = max(0, int(hot[0]) - pad)
    end = min(audio.size, int(hot[-1]) + pad)
    return audio[start:end]


def _fade(audio: np.ndarray, sample_rate: int, ms: float = 12) -> np.ndarray:
    count = int(sample_rate * ms / 1000)
    if audio.size < count * 2:
        return audio
    ramp = np.linspace(0, 1, count, dtype=np.float32)
    faded = audio.copy()
    faded[:count] *= ramp
    faded[-count:] *= ramp[::-1]
    return faded


class Speaker:
    def __init__(self, model_id: str = DEFAULT_TTS, voice: str = DEFAULT_VOICE):
        from mlx_audio.tts.utils import load_model

        configure_metal()
        self.model = load_model(model_id)
        self.voice = voice
        self.sample_rate = int(self.model.sample_rate)
        self.model_id = model_id

    def synthesize(self, text: str, instruct: str | None = None) -> np.ndarray:
        pieces = []
        for result in self.model.generate_custom_voice(
            text=text,
            speaker=self.voice,
            language="Chinese",
            instruct=instruct or INSTRUCT,
            temperature=0.5,
            max_tokens=4096,
            verbose=False,
            stream=False,
        ):
            if getattr(result, "is_streaming_chunk", False) and not result.is_final_chunk:
                continue
            pieces.append(_as_audio(result.audio))
        if not pieces:
            return np.zeros(int(self.sample_rate * 0.2), dtype=np.float32)
        return _trim(np.concatenate(pieces), self.sample_rate)

    def units_per_second(self) -> float:
        audio = self.synthesize(CALIBRATION)
        seconds = max(0.5, audio.size / self.sample_rate)
        rate = speakable_units(CALIBRATION) / seconds
        # One slow sample under-counts and makes later lines drop content.
        if rate < 4.2 or rate > 6.5:
            return 4.5
        return rate


def fit_clip(audio: np.ndarray, sample_rate: int, window: float) -> np.ndarray:
    """Fit speech into the gap before the next phrase without large pitch changes."""
    if window <= 0.15:
        return np.zeros(int(sample_rate * 0.08), dtype=np.float32)
    duration = audio.size / sample_rate
    if duration > window:
        speed = min(duration / window, 1.16)
        audio = atempo(audio, sample_rate, speed)
    max_samples = int(window * sample_rate)
    if audio.size > max_samples:
        audio = audio[:max_samples]
    return _fade(audio, sample_rate)


def line_instruct(text: str) -> str:
    if text.rstrip().endswith(("。", "！", "？", "…")):
        return INSTRUCT
    return CONTINUATION


def clip_path(directory: Path, line: Line) -> Path:
    digest = hashlib.sha1(f"{line.zh}\n{line_instruct(line.zh)}".encode()).hexdigest()[:10]
    return directory / f"{line.id:05d}-{digest}.wav"


def render_timeline(
    lines: list[Line],
    speaker: Speaker,
    clip_dir: Path,
    total_seconds: float,
    *,
    on_line=None,
) -> np.ndarray:
    import soundfile as sf

    clip_dir.mkdir(parents=True, exist_ok=True)
    sample_rate = speaker.sample_rate
    timeline = np.zeros(int(total_seconds * sample_rate) + sample_rate, dtype=np.float32)
    for index, line in enumerate(lines):
        path = clip_path(clip_dir, line)
        if path.exists() and path.stat().st_size > 800:
            audio, file_rate = sf.read(str(path), dtype="float32")
            audio = np.asarray(audio, dtype=np.float32).reshape(-1)
            if file_rate != sample_rate:
                raise RuntimeError(f"sample rate mismatch in {path.name}")
        else:
            audio = speaker.synthesize(line.zh, line_instruct(line.zh))
            sf.write(str(path), audio, sample_rate, subtype="PCM_16")
        next_start = lines[index + 1].start if index + 1 < len(lines) else total_seconds
        window = max(0.25, next_start - line.start - 0.03)
        raw_seconds = audio.size / sample_rate
        if raw_seconds > window * 1.16:
            with (clip_dir / "fit.log").open("a", encoding="utf-8") as handle:
                handle.write(f"{line.id}\t{raw_seconds:.2f}\t{window:.2f}\n")
        fitted = fit_clip(audio, sample_rate, window)
        start = int(line.start * sample_rate)
        stop = min(timeline.size, start + fitted.size)
        if stop > start:
            timeline[start:stop] += fitted[: stop - start]
        if on_line:
            on_line(index + 1, len(lines))
        if index % 25 == 24:
            release_memory()
    peak = float(np.max(np.abs(timeline))) if timeline.size else 0.0
    if peak > 0.98:
        timeline *= 0.98 / peak
    need = int(total_seconds * sample_rate)
    if timeline.size < need:
        timeline = np.pad(timeline, (0, need - timeline.size))
    return timeline[:need]
