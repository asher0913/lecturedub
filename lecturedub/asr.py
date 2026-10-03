"""English lecture transcription with Qwen3-ASR on the Apple GPU."""

from __future__ import annotations

from pathlib import Path

from .media import extract_wav
from .subtitles import write_srt, parse_subtitles

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


def transcribe_to_srt(
    video: Path,
    srt_path: Path,
    *,
    title: str,
    model_id: str = DEFAULT_ASR,
    work_wav: Path | None = None,
) -> None:
    """Transcribe English speech and write an SRT file with phrase timings."""
    from mlx_qwen3_asr import transcribe
    from mlx_qwen3_asr.writers import write_srt as write_asr_srt

    wav = work_wav or srt_path.with_name("audio16k.wav")
    if not wav.exists() or wav.stat().st_size < 1000:
        extract_wav(video, wav, 16000)
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
    cues = parse_subtitles(srt_path.read_text(encoding="utf-8"))
    if len(cues) < 3:
        raise RuntimeError("speech recognition produced too few subtitle cues")
    write_srt(cues, srt_path)
