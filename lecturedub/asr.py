"""English lecture transcription with Qwen3-ASR."""

from __future__ import annotations

import re
from pathlib import Path

from .media import extract_wav
from .runtime import CUDA_ALIGNER, backend, require_cuda, torch_dtype
from .subtitles import Cue, parse_subtitles, write_srt

DEFAULT_ASR = "Qwen/Qwen3-ASR-1.7B"

CS425_CONTEXT = (
    "University lecture on distributed systems. "
    "Terms: RPC, consensus, Raft, Paxos, MapReduce, GFS, Bigtable, Spanner, "
    "Dynamo, replication, leader election, quorum, fault tolerance, vector clocks."
)
CS511_CONTEXT = (
    "University lecture on advanced data management. "
    "Terms: C-Store, Dremel, Snowflake, System R, query optimizer, columnar storage, "
    "Pregel, Kafka, transactions, write-ahead log, materialized view, OLAP."
)


def context_for(title: str) -> str:
    lowered = title.lower()
    if "511" in lowered or any(
        name in lowered for name in ("c-store", "cstore", "dremel", "snowflake", "system r", "pregel", "kafka")
    ):
        return CS511_CONTEXT
    return CS425_CONTEXT


def _stamp_text(stamp) -> str:
    if isinstance(stamp, dict):
        return str(stamp.get("text") or "").strip()
    return str(getattr(stamp, "text", "") or "").strip()


def _stamp_span(stamp) -> tuple[float, float]:
    if isinstance(stamp, dict):
        start = float(stamp.get("start_time", stamp.get("start", 0.0)))
        end = float(stamp.get("end_time", stamp.get("end", start)))
    else:
        start = float(getattr(stamp, "start_time", getattr(stamp, "start", 0.0)))
        end = float(getattr(stamp, "end_time", getattr(stamp, "end", start)))
    return start, end


def _align_items(stamps):
    if stamps is None:
        return []
    inner = getattr(stamps, "items", None)
    if inner is not None and not callable(inner):
        return list(inner)
    return list(stamps)


def phrases_from_timestamps(stamps, offset: float = 0.0, max_seconds: float = 12.0) -> list[Cue]:
    """Join word timestamps into spoken phrases."""
    stamps = _align_items(stamps)
    cues: list[Cue] = []
    words: list[tuple[str, float, float]] = []

    def flush() -> None:
        if not words:
            return
        text = " ".join(word for word, _, _ in words)
        text = re.sub(r"\s+([,.!?;:])", r"\1", text).strip()
        if text:
            cues.append(Cue(offset + words[0][1], offset + words[-1][2], text))
        words.clear()

    for stamp in stamps or []:
        text = _stamp_text(stamp)
        if not text:
            continue
        start, end = _stamp_span(stamp)
        if words and start - words[-1][2] > 0.8:
            flush()
        words.append((text, start, end))
        span = words[-1][2] - words[0][1]
        if text.endswith((".", "?", "!")) or span >= max_seconds:
            flush()
    flush()
    return cues


def transcribe_to_srt(
    video: Path,
    srt_path: Path,
    *,
    title: str,
    model_id: str = DEFAULT_ASR,
    work_wav: Path | None = None,
) -> None:
    """Transcribe English speech and write an SRT file with phrase timings."""
    wav = work_wav or srt_path.with_name("audio16k.wav")
    if not wav.exists() or wav.stat().st_size < 1000:
        extract_wav(video, wav, 16000)
    if backend() == "mlx":
        _transcribe_mlx(wav, srt_path, title=title, model_id=model_id)
    else:
        _transcribe_cuda(wav, srt_path, title=title, model_id=model_id)
    cues = parse_subtitles(srt_path.read_text(encoding="utf-8"))
    if len(cues) < 3:
        raise RuntimeError("speech recognition produced too few subtitle cues")
    write_srt(cues, srt_path)


def _transcribe_mlx(wav: Path, srt_path: Path, *, title: str, model_id: str) -> None:
    from mlx_qwen3_asr import transcribe
    from mlx_qwen3_asr.writers import write_srt as write_asr_srt

    result = transcribe(
        str(wav),
        model=model_id,
        language="English",
        return_timestamps=True,
        context=context_for(title),
    )
    if not result.segments:
        raise RuntimeError("speech recognition returned no timed segments")
    write_asr_srt(result, str(srt_path))


def _transcribe_cuda(wav: Path, srt_path: Path, *, title: str, model_id: str) -> None:
    import torch
    from qwen_asr import Qwen3ASRModel

    device = require_cuda()
    dtype = torch_dtype()
    model = Qwen3ASRModel.from_pretrained(
        model_id,
        dtype=dtype,
        device_map=device,
        max_inference_batch_size=4,
        max_new_tokens=4096,
        forced_aligner=CUDA_ALIGNER,
        forced_aligner_kwargs={"dtype": dtype, "device_map": device},
    )
    try:
        result = model.transcribe(
            audio=str(wav),
            language="English",
            context=context_for(title),
            return_time_stamps=True,
        )[0]
        cues = phrases_from_timestamps(result.time_stamps)
    finally:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if len(cues) < 3:
        raise RuntimeError("speech recognition returned no timed segments")
    write_srt(cues, srt_path)
