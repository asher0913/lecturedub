"""Draw small bilingual captions and a timed picture the muxer can overlay."""

from __future__ import annotations

import re
from pathlib import Path

from .translate import Line

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ZH_SIZE = 26
EN_SIZE = 18
BOTTOM = 18
MAX_WIDTH_RATIO = 0.86


def _font(size: int):
    from PIL import ImageFont

    return ImageFont.truetype(FONT, size=size, index=0)


def _cjk_heavy(text: str) -> bool:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk >= max(1, len(text) / 4)


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    if not text:
        return []
    if _cjk_heavy(text):
        units = list(text)
        joiner = ""
    else:
        units = text.split(" ")
        joiner = " "
    lines: list[str] = []
    current = ""
    for unit in units:
        trial = unit if not current else current + joiner + unit
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = unit
    if current:
        lines.append(current)
    return lines


def _fit_lines(draw, text: str, size: int, max_width: int, limit: int) -> tuple[list[str], object]:
    font = _font(size)
    lines = _wrap(draw, text, font, max_width)
    while len(lines) > limit and size > 15:
        size -= 2
        font = _font(size)
        lines = _wrap(draw, text, font, max_width)
    if len(lines) > limit:
        lines = lines[: limit - 1] + [" ".join(lines[limit - 1 :])]
    return lines, font


def render_caption(zh: str, en: str, width: int, height: int, dest: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    max_width = int(width * MAX_WIDTH_RATIO)
    zh_lines, zh_font = _fit_lines(draw, zh, ZH_SIZE, max_width, 2)
    en_lines, en_font = _fit_lines(draw, en, EN_SIZE, max_width, 2)
    rows: list[tuple[str, object, tuple[int, int, int, int]]] = []
    for line in zh_lines:
        rows.append((line, zh_font, (255, 255, 255, 255)))
    for line in en_lines:
        rows.append((line, en_font, (230, 230, 230, 255)))
    if not rows:
        image.save(dest)
        return
    heights = []
    widths = []
    for text, font, _color in rows:
        box = draw.textbbox((0, 0), text, font=font)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    gap = 3
    pad_x, pad_y = 12, 7
    block_w = min(width - 24, max(widths) + pad_x * 2)
    block_h = sum(heights) + gap * (len(rows) - 1) + pad_y * 2
    x0 = (width - block_w) // 2
    y0 = height - BOTTOM - block_h
    draw.rounded_rectangle((x0, y0, x0 + block_w, y0 + block_h), radius=8, fill=(0, 0, 0, 148))
    y = y0 + pad_y
    for (text, font, color), row_w, row_h in zip(rows, widths, heights):
        tx = x0 + (block_w - row_w) // 2
        draw.text((tx + 1, y + 1), text, font=font, fill=(0, 0, 0, 180))
        draw.text((tx, y), text, font=font, fill=color)
        y += row_h + gap
    image.save(dest)


def build_caption_track(lines: list[Line], width: int, height: int, total: float, directory: Path) -> Path:
    """One still per caption interval, including blanks so text does not stick on screen."""
    directory.mkdir(parents=True, exist_ok=True)
    blank = directory / "blank.png"
    if not blank.exists():
        from PIL import Image

        Image.new("RGBA", (width, height), (0, 0, 0, 0)).save(blank)
    pieces: list[tuple[Path, float]] = []
    clock = 0.0
    for index, line in enumerate(lines):
        nxt = lines[index + 1].start if index + 1 < len(lines) else total
        show_until = min(max(line.end, line.start + 0.4), nxt)
        if nxt - line.end > 1.2:
            show_until = min(show_until, line.end)
        start = max(line.start, clock)
        if start - clock > 0.05:
            pieces.append((blank, start - clock))
        duration = max(0.12, show_until - start)
        frame = directory / f"{line.id:05d}.png"
        render_caption(line.zh, line.en, width, height, frame)
        pieces.append((frame, duration))
        clock = start + duration
    if total - clock > 0.05:
        pieces.append((blank, total - clock))
    listing = directory / "captions.ffconcat"
    rows = ["ffconcat version 1.0"]
    for path, duration in pieces:
        rows.append(f"file '{path}'")
        rows.append(f"duration {duration:.3f}")
    if pieces:
        rows.append(f"file '{pieces[-1][0]}'")
    listing.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return listing
