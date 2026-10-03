"""Local app: drop a video or paste a link, get a Chinese dub back."""

from __future__ import annotations

import json
import mimetypes
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .pipeline import ROOT, run_batch
from .voice import DEFAULT_VOICE

JOBS: dict[str, dict] = {}
QUEUE: list[str] = []
LOCK = threading.Lock()
STATIC = Path(__file__).with_name("static")


def _work_root(job_id: str) -> Path:
    return ROOT / "work" / "app" / job_id


def _worker(voice: str) -> None:
    while True:
        with LOCK:
            if not QUEUE:
                job_id = None
            else:
                job_id = QUEUE.pop(0)
        if job_id is None:
            threading.Event().wait(0.4)
            continue
        job = JOBS[job_id]
        job["status"] = "running"
        try:
            item = {
                "course": "video",
                "slug": "dubbed",
                "title": job["title"],
                "video": job["video"],
            }
            if job.get("srt"):
                item["srt"] = job["srt"]
            run_batch(
                [item],
                work_root=_work_root(job_id),
                output_root=_work_root(job_id) / "out",
                voice=voice,
            )
            produced = _work_root(job_id) / "out" / "video" / "dubbed.mp4"
            job["output"] = str(produced)
            job["status"] = "done" if produced.exists() else "error"
            if job["status"] != "done":
                job["error"] = "dubbing finished without an output file"
        except Exception as exc:
            job["status"] = "error"
            job["error"] = f"{exc}\n{traceback.format_exc(limit=4)}"


def _save_part(directory: Path, name: str, filename: str, payload: bytes) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    if filename:
        suffix = Path(filename).suffix or ".bin"
        dest = directory / f"{name}{suffix}"
        dest.write_bytes(payload)
        return str(dest)
    return payload.decode("utf-8", "replace")


def _parts(body: bytes, content_type: str) -> list[dict]:
    marker = "boundary="
    if marker not in content_type:
        raise ValueError("expected a multipart upload")
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    delimiter = b"--" + boundary.encode()
    parts = []
    for chunk in body.split(delimiter):
        if chunk in (b"", b"--") or chunk.startswith(b"--"):
            continue
        chunk = chunk[2:] if chunk.startswith(b"\r\n") else chunk
        if chunk.endswith(b"\r\n"):
            chunk = chunk[:-2]
        header_blob, _, data = chunk.partition(b"\r\n\r\n")
        header = header_blob.decode("utf-8", "replace")
        name = ""
        filename = ""
        for line in header.split("\r\n"):
            if "name=" in line:
                name = line.split('name="', 1)[-1].split('"', 1)[0]
            if "filename=" in line:
                filename = line.split('filename="', 1)[-1].split('"', 1)[0]
        parts.append({"name": name, "filename": filename, "data": data})
    return parts


class Handler(BaseHTTPRequestHandler):
    voice = DEFAULT_VOICE

    def log_message(self, fmt: str, *args) -> None:
        print(f"ui  {self.address_string()}  {fmt % args}", flush=True)

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False).encode(), "application/json")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = (STATIC / "index.html").read_bytes()
            self._send(200, page, "text/html; charset=utf-8")
            return
        if path == "/api/jobs":
            with LOCK:
                self._json(200, {"jobs": list(JOBS.values())})
            return
        if path.startswith("/files/"):
            parts = [unquote(part) for part in path.split("/") if part]
            if len(parts) != 3:
                self._json(404, {"error": "not ready"})
                return
            _, job_id, name = parts
            job = JOBS.get(unquote(job_id))
            if not job or not job.get("output"):
                self._json(404, {"error": "not ready"})
                return
            target = Path(job["output"])
            if name != target.name or not target.exists():
                self._json(404, {"error": "missing file"})
                return
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            data = target.read_bytes()
            self._send(200, data, kind)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/jobs":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        fields: dict[str, str] = {}
        files: dict[str, str] = {}
        job_id = uuid.uuid4().hex[:12]
        inbox = _work_root(job_id) / "inbox"
        if content_type.startswith("application/json"):
            fields = json.loads(body.decode("utf-8"))
        else:
            for part in _parts(body, content_type):
                saved = _save_part(inbox, part["name"] or "file", part["filename"], part["data"])
                if part["filename"]:
                    files[part["name"]] = saved
                else:
                    fields[part["name"]] = saved
        video = files.get("video") or fields.get("url") or fields.get("video")
        if not video:
            self._json(400, {"error": "drop a video or paste a link"})
            return
        title = fields.get("title") or Path(str(video)).stem or "lecture"
        job = {
            "id": job_id,
            "title": title,
            "video": video,
            "srt": files.get("srt") or fields.get("srt") or "",
            "status": "queued",
            "error": "",
            "output": "",
        }
        with LOCK:
            JOBS[job_id] = job
            QUEUE.append(job_id)
        self._json(202, job)


def serve(port: int = 7860, voice: str = DEFAULT_VOICE) -> None:
    Handler.voice = voice
    thread = threading.Thread(target=_worker, args=(voice,), daemon=True)
    thread.start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"lecturedub  http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
