"""End-to-end dubbing, one lecture or a whole folder of them."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .asr import DEFAULT_ASR, transcribe_to_srt
from .media import (
    MediaError,
    download,
    download_text,
    download_with_ytdlp,
    duration_of,
    is_direct_file_url,
    loudnorm,
    mux,
    require_ffmpeg,
    write_timeline_wav,
)
from .subtitles import Cue, group_cues, parse_subtitles, write_srt
from .translate import DEFAULT_LLM, Line, Translator, translate_cues
from .voice import DEFAULT_TTS, DEFAULT_VOICE, Speaker, release_memory, render_timeline

ROOT = Path(__file__).resolve().parents[1]


def log(message: str, log_path: Path | None = None) -> None:
    line = f"{time.strftime('%H:%M:%S')}  {message}"
    print(line, flush=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def env_model(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Job:
    key: str
    title: str
    course: str
    slug: str
    video_url: str | None
    local_video: Path | None
    srt_url: str | None
    local_srt: Path | None
    expected_duration: float | None
    expected_bytes: int | None
    work: Path
    output_video: Path
    output_srt: Path

    def marker(self, name: str) -> Path:
        return self.work / name


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return cleaned[:80] or "lecture"


def job_from_item(item: dict, work_root: Path, output_root: Path) -> Job:
    course = str(item.get("course") or "").strip()
    title = str(item.get("title") or item.get("slug") or "lecture").strip()
    slug = slugify(str(item.get("slug") or title))
    key = f"{course}-{slug}" if course else slug
    video_url = item.get("video") or item.get("videoUrl")
    local_video = None
    if video_url and not str(video_url).startswith(("http://", "https://")):
        local_video = Path(video_url).expanduser()
        video_url = None
    srt_url = item.get("srt")
    captions = item.get("captions") or []
    if not srt_url and captions:
        srt_url = captions[0].get("url")
    local_srt = None
    if srt_url and not str(srt_url).startswith(("http://", "https://")):
        local_srt = Path(srt_url).expanduser()
        srt_url = None
    course_dir = course or "video"
    return Job(
        key=key,
        title=title,
        course=course_dir,
        slug=slug,
        video_url=video_url,
        local_video=local_video,
        srt_url=srt_url,
        local_srt=local_srt,
        expected_duration=item.get("duration"),
        expected_bytes=_expected_bytes(item),
        work=work_root / key,
        output_video=output_root / course_dir / f"{slug}.mp4",
        output_srt=output_root / course_dir / f"{slug}.zh.srt",
    )


def _expected_bytes(item: dict) -> int | None:
    bandwidth = item.get("bandwidth")
    duration = item.get("duration")
    if not bandwidth or not duration:
        return None
    return int(float(bandwidth) * float(duration) / 8)


def _video_ready(path: Path, expected: float | None, expected_bytes: int | None = None) -> bool:
    if not path.exists() or path.stat().st_size < 200_000:
        return False
    # A faststart MP4 reports the full duration before the file has finished downloading.
    if expected_bytes and path.stat().st_size < int(expected_bytes * 0.82):
        return False
    try:
        got = duration_of(path)
    except MediaError:
        return False
    if expected and abs(got - float(expected)) > 4:
        return False
    return True


def ensure_video(job: Job, log_path: Path) -> Path:
    dest = job.marker("source.mp4")
    if _video_ready(dest, job.expected_duration, job.expected_bytes):
        return dest
    job.work.mkdir(parents=True, exist_ok=True)
    if job.local_video is not None:
        if not _video_ready(job.local_video, None):
            raise MediaError(f"video is missing or unreadable: {job.local_video}")
        if dest.exists():
            dest.unlink()
        shutil.copy2(job.local_video, dest)
        return dest
    if not job.video_url:
        raise MediaError(f"{job.key} has no video")
    log(f"download  {job.title}", log_path)
    if is_direct_file_url(job.video_url):
        download(job.video_url, dest)
    else:
        download_with_ytdlp(job.video_url, dest)
    if not _video_ready(dest, job.expected_duration, job.expected_bytes):
        raise MediaError(f"downloaded video for {job.key} failed duration check")
    return dest


def english_ready(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 20:
        return False
    try:
        return len(parse_subtitles(path.read_text(encoding="utf-8"))) >= 5
    except OSError:
        return False


def fetch_english(job: Job, log_path: Path) -> bool:
    """Save provided captions. Return False when the video still needs speech recognition."""
    dest = job.marker("en.orig.srt")
    if english_ready(dest):
        return True
    job.work.mkdir(parents=True, exist_ok=True)
    if job.local_srt is not None:
        dest.write_text(job.local_srt.read_text(encoding="utf-8"), encoding="utf-8")
        return english_ready(dest)
    if not job.srt_url:
        return False
    try:
        dest.write_text(download_text(job.srt_url), encoding="utf-8")
    except MediaError as exc:
        log(f"captions unavailable for {job.title}: {exc}", log_path)
        if dest.exists():
            dest.unlink()
        return False
    if english_ready(dest):
        return True
    if dest.exists():
        dest.unlink()
    return False


def _write_progress(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_lines(path: Path) -> list[Line] | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not raw:
        return None
    return [Line(**row) for row in raw]


def _save_lines(path: Path, lines: list[Line]) -> None:
    payload = [
        {"id": line.id, "start": line.start, "end": line.end, "en": line.en, "zh": line.zh}
        for line in lines
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _phrases(job: Job, pilot_seconds: float | None) -> list[Cue]:
    cues = parse_subtitles(job.marker("en.orig.srt").read_text(encoding="utf-8"))
    grouped = group_cues(cues, max_seconds=16.0)
    if pilot_seconds is not None:
        grouped = [cue for cue in grouped if cue.start < pilot_seconds]
    if not grouped:
        raise RuntimeError(f"no spoken phrases in {job.key}")
    return grouped


def dub_lines(
    lines: list[Line],
    speaker: Speaker,
    job: Job,
    total_seconds: float,
    log_path: Path,
    progress_path: Path,
) -> Path:
    def on_line(done: int, total: int) -> None:
        if done == 1 or done == total or done % 10 == 0:
            log(f"voice  {job.title}  {done}/{total}", log_path)
            _write_progress(
                progress_path,
                {"stage": "voice", "job": job.key, "done": done, "total": total},
            )

    audio = render_timeline(
        lines,
        speaker,
        job.marker("clips"),
        total_seconds,
        on_line=on_line,
    )
    raw = job.marker("dub.raw.wav")
    final = job.marker("dub.wav")
    write_timeline_wav(audio, speaker.sample_rate, raw)
    try:
        loudnorm(raw, final)
    except MediaError:
        shutil.copy2(raw, final)
    return final


def write_tracks(job: Job, lines: list[Line], pilot: bool) -> Path:
    srt_cues = [Cue(line.start, line.end, line.zh) for line in lines]
    srt_path = job.marker("pilot.zh.srt" if pilot else "zh.srt")
    write_srt(srt_cues, srt_path)
    write_srt([Cue(line.start, line.end, line.en) for line in lines], job.marker("en.fixed.srt"))
    return srt_path


def publish(job: Job, video: Path, audio: Path, lines: list[Line], pilot: bool) -> Path:
    srt_path = write_tracks(job, lines, pilot)
    dest = job.marker("pilot.mp4" if pilot else "dubbed.mp4")
    english = job.marker("en.fixed.srt")
    mux(video, audio, srt_path, dest, english=english, caption_lines=lines)
    if not pilot:
        job.output_video.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, job.output_video)
        shutil.copy2(srt_path, job.output_srt)
        en_out = job.output_srt.with_name(f"{job.slug}.en.srt")
        if english.exists():
            shutil.copy2(english, en_out)
        return job.output_video
    return dest


def finished(job: Job) -> bool:
    if not job.output_video.exists():
        return False
    source = job.marker("source.mp4")
    if not source.exists():
        return True
    try:
        return abs(duration_of(job.output_video) - duration_of(source)) < 5
    except MediaError:
        return False


def run_batch(
    items: list[dict],
    *,
    work_root: Path,
    output_root: Path,
    voice: str = DEFAULT_VOICE,
    pilot_seconds: float | None = None,
    only: str | None = None,
    download: bool = True,
    translate_only: bool = False,
) -> list[Path]:
    require_ffmpeg()
    work_root.mkdir(parents=True, exist_ok=True)
    log_path = work_root.parent / "dub.log" if work_root.name == "lectures" else work_root / "dub.log"
    progress_path = log_path.with_name("progress.json")
    jobs = [job_from_item(item, work_root, output_root) for item in items]
    if only:
        jobs = [job for job in jobs if only in job.key or only in job.title]
    if not jobs:
        raise RuntimeError("no lectures matched")

    pending = [job for job in jobs if pilot_seconds or not finished(job)]
    log(f"{len(pending)} lecture(s) to dub, {len(jobs) - len(pending)} already done", log_path)
    if not pending and not pilot_seconds:
        return [job.output_video for job in jobs]

    asr_model = env_model("LECTUREDUB_ASR", DEFAULT_ASR)
    if download:
        needs_asr = [job for job in pending if not fetch_english(job, log_path)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda job: ensure_video(job, log_path), pending))
    else:
        for job in pending:
            fetch_english(job, log_path)
        needs_asr = []
        runnable = []
        for job in pending:
            if english_ready(job.marker("en.orig.srt")):
                runnable.append(job)
            elif _video_ready(job.marker("source.mp4"), job.expected_duration, job.expected_bytes):
                needs_asr.append(job)
            else:
                log(f"wait for video before transcription  {job.title}", log_path)
        if runnable and needs_asr:
            for job in needs_asr:
                log(f"defer transcription until captioned lectures are done  {job.title}", log_path)
            needs_asr = []
        pending = runnable + needs_asr
        if not pending:
            log("nothing ready to dub yet", log_path)
            return []
    if needs_asr:
        log(f"speech recognition on {len(needs_asr)} video(s) with {asr_model}", log_path)
        for job in needs_asr:
            _write_progress(progress_path, {"stage": "asr", "job": job.key})
            log(f"transcribe  {job.title}", log_path)
            transcribe_to_srt(
                job.marker("source.mp4"),
                job.marker("en.orig.srt"),
                title=f"{job.course} {job.title}",
                model_id=asr_model,
                work_wav=job.marker("audio16k.wav"),
            )
        from mlx_qwen3_asr.load_models import _ModelHolder

        _ModelHolder.clear()
        release_memory()

    tts_id = env_model("LECTUREDUB_TTS", DEFAULT_TTS)
    llm_id = env_model("LECTUREDUB_LLM", DEFAULT_LLM)
    log(f"load voice  {tts_id}  {voice}", log_path)
    speaker = Speaker(tts_id, voice)
    rate = speaker.units_per_second()
    log(f"speech rate {rate:.2f} units/sec", log_path)
    del speaker
    release_memory()

    prepared: list[tuple[Job, list[Line], float]] = []
    jobs_to_translate = []
    phrase_map: dict[str, list[Cue]] = {}
    for job in pending:
        phrases = _phrases(job, pilot_seconds)
        phrase_map[job.key] = phrases
        segment_path = job.marker("segments.pilot.json" if pilot_seconds else "segments.json")
        lines = None if pilot_seconds else _load_lines(segment_path)
        if lines is None or len(lines) != len(phrases):
            jobs_to_translate.append((job, lines or []))
    translator = None
    if jobs_to_translate:
        log(f"load translator  {llm_id}", log_path)
        translator = Translator(llm_id)
    for job in pending:
        phrases = phrase_map[job.key]
        segment_path = job.marker("segments.pilot.json" if pilot_seconds else "segments.json")
        lines = None if pilot_seconds else _load_lines(segment_path)
        if lines is None or len(lines) != len(phrases):
            log(f"translate  {job.title}  {len(phrases)} phrases", log_path)

            def on_batch(done: int, total: int, title=job.title, key=job.key) -> None:
                log(f"translate  {title}  {done}/{total}", log_path)
                _write_progress(
                    progress_path,
                    {"stage": "translate", "job": key, "done": done, "total": total},
                )

            lines = translate_cues(
                phrases,
                translator,
                units_per_second=rate,
                batch_size=12,
                on_batch=on_batch,
                already=lines,
                checkpoint=segment_path,
            )
            _save_lines(segment_path, lines)
        source = job.marker("source.mp4")
        if pilot_seconds:
            total = pilot_seconds
        elif _video_ready(source, job.expected_duration, job.expected_bytes):
            total = duration_of(source)
        elif job.expected_duration:
            total = float(job.expected_duration)
        else:
            total = lines[-1].end + 1.0
        prepared.append((job, lines, total))
        if pilot_seconds:
            break
    del translator
    release_memory()
    if translate_only:
        log("translations saved", log_path)
        return []

    log(f"load voice  {tts_id}  {voice}", log_path)
    speaker = Speaker(tts_id, voice)
    produced: list[Path] = []
    for job, lines, total in prepared:
        audio = dub_lines(lines, speaker, job, total, log_path, progress_path)
        source = job.marker("source.mp4")
        if _video_ready(source, None if pilot_seconds else job.expected_duration, None if pilot_seconds else job.expected_bytes):
            dest = publish(job, source, audio, lines, pilot=bool(pilot_seconds))
            produced.append(dest)
            log(f"done  {dest}", log_path)
        else:
            write_tracks(job, lines, pilot=bool(pilot_seconds))
            log(f"voice ready, video still downloading  {job.title}", log_path)
    del speaker
    release_memory()
    if not pilot_seconds:
        mux_ready(jobs, log_path)
        return [job.output_video for job in jobs]
    return produced


def mux_ready(jobs: list[Job], log_path: Path | None = None) -> list[Path]:
    """Mux any lecture whose Chinese audio is done and whose video has finished downloading."""
    done = []
    for job in jobs:
        if finished(job):
            done.append(job.output_video)
            continue
        video = job.marker("source.mp4")
        audio = job.marker("dub.wav")
        lines = _load_lines(job.marker("segments.json"))
        if not lines or not audio.exists() or not _video_ready(video, job.expected_duration, job.expected_bytes):
            continue
        dest = publish(job, video, audio, lines, pilot=False)
        log(f"muxed  {dest}", log_path)
        done.append(dest)
    return done


def prefetch(items: list[dict], *, work_root: Path, output_root: Path) -> None:
    """Download videos and any supplied captions without loading models."""
    require_ffmpeg()
    log_path = work_root.parent / "dub.log" if work_root.name == "lectures" else work_root / "dub.log"
    jobs = [job_from_item(item, work_root, output_root) for item in items]
    for job in jobs:
        ok = fetch_english(job, log_path)
        log(f"captions  {job.title}  {'yes' if ok else 'need asr'}", log_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda job: ensure_video(job, log_path), jobs))
    for job in jobs:
        log(f"fetched  {job.title}", log_path)
