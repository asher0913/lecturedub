from pathlib import Path

from lecturedub.desktop import _launch_command, install_macos_app
from lecturedub.paths import data_home


def test_data_home_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LECTUREDUB_HOME", str(tmp_path / "jobs"))
    assert data_home() == (tmp_path / "jobs").resolve()


def test_launch_command_uses_the_console_script(tmp_path: Path):
    binary = tmp_path / "lecturedub"
    assert _launch_command(binary) == f'"{binary}" app'


def test_launch_command_falls_back_to_module(tmp_path: Path):
    binary = tmp_path / "python3"
    assert _launch_command(binary) == f'"{binary}" -m lecturedub app'


def test_macos_app_bundle(tmp_path: Path):
    binary = tmp_path / "venv" / "bin" / "lecturedub"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/bash\n", encoding="utf-8")
    binary.chmod(0o755)
    app = install_macos_app(dest=tmp_path / "LectureDub.app", executable=binary)
    plist = (app / "Contents" / "Info.plist").read_text(encoding="utf-8")
    launcher = (app / "Contents" / "MacOS" / "lecturedub").read_text(encoding="utf-8")
    assert "com.lecturedub.app" in plist
    assert "CFBundleExecutable" in plist
    assert f'"{binary}" app' in launcher
    assert (app / "Contents" / "MacOS" / "lecturedub").stat().st_mode & 0o111
