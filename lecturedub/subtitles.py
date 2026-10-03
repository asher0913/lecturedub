"""Subtitle parsing, phrase grouping, and SRT writing."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

TIME_HMS = re.compile(
    r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)
TIME_MS = re.compile(r"(?P<m>\d+):(?P<s>\d{2})[,.](?P<ms>\d{1,3})")
TAG_RE = re.compile(r"<[^>]+>")
SPEAKER_RE = re.compile(r"^\s*[A-Z][A-Za-z .]{0,24}:\s+")
NOISE_RE = re.compile(
    r"^[\s\[\]()（）\-–—]*("
    r"music|applause|laughter|silence|inaudible|blank_audio|"
    r"背景音乐|音乐|掌声|笑声"
    r")[\s\[\]()（）\-–—.]*$",
    re.I,
)
SENTENCE_END = tuple(".?!。？！")


@dataclass
class Cue:
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _seconds(token: str) -> float:
    match = TIME_HMS.search(token)
    if match:
        ms = match.group("ms").ljust(3, "0")
        return (
            int(match.group("h")) * 3600
            + int(match.group("m")) * 60
            + int(match.group("s"))
            + int(ms) / 1000
        )
    match = TIME_MS.search(token)
    if not match:
        raise ValueError(f"bad timestamp: {token}")
    ms = match.group("ms").ljust(3, "0")
    return int(match.group("m")) * 60 + int(match.group("s")) + int(ms) / 1000


def _clean_text(text: str) -> str:
    text = html.unescape(text)
    text = TAG_RE.sub("", text)
    text = text.replace("\u00a0", " ")
    lines = []
    for line in text.splitlines():
        line = SPEAKER_RE.sub("", line).strip()
        if line.startswith("- "):
            line = line[2:].strip()
        if line:
            lines.append(line)
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if NOISE_RE.match(text):
        return ""
    return text


def parse_subtitles(raw: str) -> list[Cue]:
    """Parse SRT or WebVTT into cues sorted by start time."""
    text = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text)
    cues: list[Cue] = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        arrow = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if arrow is None:
            continue
        left, right = lines[arrow].split("-->", 1)
        try:
            start = _seconds(left.strip())
            end = _seconds(right.strip().split()[0])
        except ValueError:
            continue
        body = _clean_text("\n".join(lines[arrow + 1 :]))
        if not body or end <= start:
            continue
        cues.append(Cue(start, end, body))
    cues.sort(key=lambda cue: (cue.start, cue.end))
    return cues


def ends_sentence(text: str) -> bool:
    stripped = text.rstrip().rstrip("\"'”’)")
    return stripped.endswith(SENTENCE_END)


def group_cues(
    cues: list[Cue],
    *,
    min_seconds: float = 3.2,
    max_seconds: float = 14.0,
    gap_seconds: float = 0.55,
) -> list[Cue]:
    """Merge short captions into speakable phrases, breaking on pauses and sentences."""
    grouped: list[Cue] = []
    current: Cue | None = None
    for cue in cues:
        if current is None:
            current = Cue(cue.start, cue.end, cue.text)
            continue
        gap = cue.start - current.end
        joined_end = max(current.end, cue.end)
        joined_dur = joined_end - current.start
        current_dur = current.duration
        should_break = (
            gap > gap_seconds
            or joined_dur > max_seconds
            or (
                ends_sentence(current.text)
                and current_dur >= min_seconds
                and gap > 0.12
            )
        )
        if should_break:
            grouped.append(current)
            current = Cue(cue.start, cue.end, cue.text)
            continue
        spacer = "" if current.text.endswith("-") else " "
        current = Cue(current.start, joined_end, f"{current.text}{spacer}{cue.text}")
    if current is not None:
        grouped.append(current)
    return grouped


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(cues: list[Cue], path) -> None:
    parts = []
    for index, cue in enumerate(cues, 1):
        parts.append(
            f"{index}\n{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}\n{cue.text}\n"
        )
    path.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")


def speakable_units(text: str) -> int:
    """Rough spoken length: one Chinese character, or two units per Latin word."""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9.+#-]*", text)
    return cjk + 2 * len(words)
