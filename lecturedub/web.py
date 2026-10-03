"""Local app: drop a video or paste a link, get a Chinese dub back."""

from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__
from .paths import data_home
from .pipeline import run_batch
from .voice import DEFAULT_VOICE

JOBS: dict[str, dict] = {}
QUEUE: list[str] = []
LOCK = threading.Lock()
STATIC = Path(__file__).with_name("static")
_WORKER_STARTED = False
_SERVING = False


def _work_root(job_id: str) -> Path:
    return data_home() / "jobs" / job_id


def _worker(voice: str) -> None:
    while True:
        with LOCK:
            job_id = QUEUE.pop(0) if QUEUE else None
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
                voice=job.get("voice") or voice,
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


def _progress(job_id: str) -> dict:
    path = _work_root(job_id) / "progress.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _output_files(job: dict) -> list[str]:
    raw = job.get("output") or ""
    if not raw:
        return []
    video = Path(raw)
    names = [video.name, f"{video.stem}.zh.srt", f"{video.stem}.en.srt"]
    return [name for name in names if (video.parent / name).is_file()]


def _public_job(job: dict) -> dict:
    progress = _progress(job["id"]) if job.get("status") == "running" else {}
    return {
        "id": job["id"],
        "title": job["title"],
        "status": job["status"],
        "error": job.get("error") or "",
        "stage": progress.get("stage") or "",
        "done": progress.get("done"),
        "total": progress.get("total"),
        "files": _output_files(job),
    }


def _safe_output(job_id: str, name: str) -> Path | None:
    job = JOBS.get(job_id)
    if not job or not job.get("output"):
        return None
    video = Path(job["output"])
    target = (video.parent / name).resolve()
    if target.parent != video.parent.resolve() or not target.is_file():
        return None
    if target.name not in _output_files(job):
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    voice = DEFAULT_VOICE

    def log_message(self, fmt: str, *args) -> None:
        print(f"ui  {self.address_string()}  {fmt % args}", flush=True)

    def _send(self, code: int, body: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, target: Path) -> None:
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        size = target.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        self.end_headers()
        with target.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False).encode(), "application/json")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            page = (STATIC / "index.html").read_bytes()
            self._send(200, page, "text/html; charset=utf-8")
            return
        if path == "/api/config":
            self._json(200, {"voice": self.voice, "version": __version__})
            return
        if path == "/api/jobs":
            with LOCK:
                payload = [_public_job(job) for job in JOBS.values()]
            self._json(200, {"jobs": payload})
            return
        if path.startswith("/files/"):
            parts = [unquote(part) for part in path.split("/") if part]
            if len(parts) != 3:
                self._json(404, {"error": "not ready"})
                return
            _, job_id, name = parts
            target = _safe_output(job_id, name)
            if target is None:
                self._json(404, {"error": "not ready"})
                return
            self._send_file(target)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if route == "/api/reveal":
            self._reveal(body)
            return
        if route != "/api/jobs":
            self._json(404, {"error": "not found"})
            return
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
            "voice": fields.get("voice") or self.voice,
            "status": "queued",
            "error": "",
            "output": "",
        }
        with LOCK:
            JOBS[job_id] = job
            QUEUE.append(job_id)
        self._json(202, _public_job(job))

    def _reveal(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "bad request"})
            return
        target = _safe_output(str(payload.get("id") or ""), "dubbed.mp4")
        if target is None:
            self._json(404, {"error": "not ready"})
            return
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", str(target)], check=False)
        else:
            subprocess.run(["xdg-open", str(target.parent)], check=False)
        self._json(200, {"ok": True})


def bind_server(port: int = 7860, voice: str = DEFAULT_VOICE) -> ThreadingHTTPServer:
    Handler.voice = voice
    last_error: OSError | None = None
    server = None
    for candidate in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError as exc:
            last_error = exc
    if server is None:
        raise OSError(f"no free port from {port} to {port + 19}") from last_error
    print(f"jobs    {data_home() / 'jobs'}", flush=True)
    return server


def activate(server: ThreadingHTTPServer, voice: str) -> None:
    global _SERVING, _WORKER_STARTED
    if not _WORKER_STARTED:
        threading.Thread(target=_worker, args=(voice,), daemon=True).start()
        _WORKER_STARTED = True
    if not _SERVING:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _SERVING = True


def start_server(port: int = 7860, voice: str = DEFAULT_VOICE) -> ThreadingHTTPServer:
    server = bind_server(port, voice)
    activate(server, voice)
    return server


def serve(port: int = 7860, voice: str = DEFAULT_VOICE) -> None:
    server = start_server(port, voice)
    bound = server.server_address[1]
    print(f"lecturedub  http://127.0.0.1:{bound}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
