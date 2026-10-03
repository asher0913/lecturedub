#!/bin/bash
# Install LectureDub into a local virtualenv and add LectureDub.app.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "LectureDub runs its models on Apple Silicon. This Mac is $(uname -s) $(uname -m)."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ or with: brew install python@3.12"
  exit 1
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
then
  echo "Python 3.11 or newer is required. This one is $(python3 --version)."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 && [[ ! -x /opt/homebrew/bin/ffmpeg ]]; then
  echo "ffmpeg is required. Install it with: brew install ffmpeg"
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[desktop]"
.venv/bin/lecturedub doctor
.venv/bin/lecturedub install-app
echo
echo "LectureDub is in your Applications folder. You can also run: .venv/bin/lecturedub app"
