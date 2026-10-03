"""Native window and a double-clickable macOS app bundle."""

from __future__ import annotations

import platform
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

from . import __version__

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>LectureDub</string>
  <key>CFBundleDisplayName</key>
  <string>LectureDub</string>
  <key>CFBundleIdentifier</key>
  <string>com.lecturedub.app</string>
  <key>CFBundleVersion</key>
  <string>{version}</string>
  <key>CFBundleShortVersionString</key>
  <string>{version}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>lecturedub</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
"""

LAUNCHER = """#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:${{PATH}}"
cd "$HOME"
exec {command}
"""


def console_script() -> Path:
    sibling = Path(sys.executable).with_name("lecturedub")
    if sibling.exists():
        return sibling
    found = shutil.which("lecturedub")
    if found:
        return Path(found)
    return Path(sys.executable)


def _launch_command(executable: Path) -> str:
    quoted = str(executable).replace('"', '\\"')
    name = executable.name
    if name == "lecturedub":
        return f'"{quoted}" app'
    return f'"{quoted}" -m lecturedub app'


def install_macos_app(dest: Path | None = None, executable: Path | None = None) -> Path:
    """Write ~/Applications/LectureDub.app, pointed at this installation."""
    if dest is None and sys.platform != "darwin":
        raise SystemExit("LectureDub.app is a macOS bundle. Elsewhere, run: lecturedub app")
    if dest is None:
        dest = Path.home() / "Applications" / "LectureDub.app"
    binary = executable or console_script()
    macos = dest / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    (dest / "Contents" / "Info.plist").write_text(INFO_PLIST.format(version=__version__), encoding="utf-8")
    launcher = macos / "lecturedub"
    launcher.write_text(LAUNCHER.format(command=_launch_command(binary)), encoding="utf-8")
    launcher.chmod(0o755)
    return dest


def _wait_until_stopped(server) -> None:
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


def open_app(port: int = 7860, voice: str = "Uncle_Fu", browser: bool = False) -> None:
    from .web import activate, bind_server, start_server

    window = None if browser else _webview()
    if window is None:
        if not browser:
            print("桌面窗口需要 pywebview。已改用浏览器。安装：pip install 'lecturedub[desktop]'", flush=True)
        server = start_server(port, voice)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print(f"lecturedub  {url}", flush=True)
        webbrowser.open(url)
        _wait_until_stopped(server)
        return

    # Bind first, then let pywebview start the GUI before any worker thread.
    # On macOS the window has to be created on the main thread.
    server = bind_server(port, voice)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"lecturedub  {url}", flush=True)

    def boot() -> None:
        activate(server, voice)

    window.create_window(
        "LectureDub",
        url,
        width=980,
        height=780,
        min_size=(760, 600),
        text_select=True,
    )
    try:
        window.start(boot)
    except Exception as exc:
        print(f"desktop window failed: {exc}", flush=True)
        print("改用浏览器打开。", flush=True)
        activate(server, voice)
        webbrowser.open(url)
        _wait_until_stopped(server)
        return
    server.shutdown()


def _webview():
    try:
        import webview
    except ImportError:
        return None
    return webview


def doctor() -> int:
    from .media import FFMPEG, FFPROBE
    from .paths import data_home

    print(f"lecturedub {__version__}")
    print(f"python {sys.version.split()[0]}  {platform.machine()}")
    print(f"system {platform.platform()}")
    ok = True
    if sys.platform == "darwin" and platform.machine() == "arm64":
        print("models: Apple Silicon")
    else:
        print("models: Apple Silicon required. MLX does not run on this machine.")
        ok = False
    for label, path in (("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)):
        if Path(path).exists():
            print(f"{label}: {path}")
        else:
            print(f"{label}: missing. Install with: brew install ffmpeg")
            ok = False
    try:
        import webview

        print(f"window: pywebview {getattr(webview, '__version__', 'installed')}")
    except ImportError:
        print("window: browser only. For a desktop window: pip install 'lecturedub[desktop]'")
    home = data_home()
    try:
        home.mkdir(parents=True, exist_ok=True)
        print(f"data: {home}")
    except OSError as exc:
        print(f"data: cannot write {home} ({exc})")
        ok = False
    return 0 if ok else 1
