"""Command line for lecturedub."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import job_from_item, mux_ready, prefetch, run_batch
from .voice import DEFAULT_VOICE


def _load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("jobs") or data.get("items") or []
    if not isinstance(data, list):
        raise SystemExit("manifest must be a JSON list")
    return data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="lecturedub",
        description="Replace a lecture's English soundtrack with timestamp-aligned Chinese speech.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="dub one video file or URL")
    run.add_argument("video", help="path or URL")
    run.add_argument("-o", "--output", required=True, help="output mp4 path")
    run.add_argument("--srt", help="English SRT or VTT path or URL")
    run.add_argument("--title", default="")
    run.add_argument("--voice", default=DEFAULT_VOICE)
    run.add_argument("--work", default="work/jobs")

    batch = sub.add_parser("batch", help="dub every item in a JSON manifest")
    batch.add_argument("manifest")
    batch.add_argument("--output-dir", default="output")
    batch.add_argument("--work-dir", default="work/lectures")
    batch.add_argument("--voice", default=DEFAULT_VOICE)
    batch.add_argument("--only", help="substring match on the lecture id or title")
    batch.add_argument("--pilot-seconds", type=float, help="dub only the opening of the first match")
    batch.add_argument("--no-download", action="store_true", help="do not download; dub captions already on disk")
    batch.add_argument("--translate-only", action="store_true", help="stop after the Chinese script is written")

    mux = sub.add_parser("mux", help="combine finished Chinese audio with downloaded video")
    mux.add_argument("manifest")
    mux.add_argument("--output-dir", default="output")
    mux.add_argument("--work-dir", default="work/lectures")

    fetch = sub.add_parser("fetch", help="download videos and captions only")
    fetch.add_argument("manifest")
    fetch.add_argument("--output-dir", default="output")
    fetch.add_argument("--work-dir", default="work/lectures")

    ui = sub.add_parser("ui", help="open the local drag-and-drop app")
    ui.add_argument("--port", type=int, default=7860)
    ui.add_argument("--voice", default=DEFAULT_VOICE)

    args = parser.parse_args(argv)
    if args.command == "ui":
        from .web import serve

        serve(port=args.port, voice=args.voice)
        return

    if args.command == "mux":
        items = _load_manifest(Path(args.manifest))
        jobs = [job_from_item(item, Path(args.work_dir), Path(args.output_dir)) for item in items]
        mux_ready(jobs, Path(args.work_dir).parent / "dub.log")
        return

    if args.command == "fetch":
        prefetch(
            _load_manifest(Path(args.manifest)),
            work_root=Path(args.work_dir),
            output_root=Path(args.output_dir),
        )
        return

    if args.command == "run":
        output = Path(args.output)
        item = {
            "course": "video",
            "slug": output.stem,
            "title": args.title or output.stem,
            "video": args.video,
        }
        if args.srt:
            item["srt"] = args.srt
        run_batch(
            [item],
            work_root=Path(args.work),
            output_root=output.parent,
            voice=args.voice,
        )
        produced = output.parent / "video" / f"{output.stem}.mp4"
        if produced.exists() and produced.resolve() != output.resolve():
            output.parent.mkdir(parents=True, exist_ok=True)
            produced.replace(output)
        print(output)
        return

    run_batch(
        _load_manifest(Path(args.manifest)),
        work_root=Path(args.work_dir),
        output_root=Path(args.output_dir),
        voice=args.voice,
        only=args.only,
        pilot_seconds=args.pilot_seconds,
        download=not args.no_download,
        translate_only=args.translate_only,
    )


if __name__ == "__main__":
    main()
