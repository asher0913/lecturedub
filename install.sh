#!/bin/bash
# Install LectureDub into a local virtualenv. On an Apple Silicon Mac, also add LectureDub.app.
set -euo pipefail
cd "$(dirname "$0")"

os="$(uname -s)"
arch="$(uname -m)"
extra="nvidia"
if [[ "$os" == "Darwin" && "$arch" == "arm64" ]]; then
  extra="apple"
elif [[ "$os" == "Darwin" ]]; then
  echo "Intel Macs are not supported. Use an Apple Silicon Mac, or Windows/Linux with an NVIDIA GPU."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required."
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
  if [[ "$os" == "Darwin" ]]; then
    echo "ffmpeg is required. Install it with: brew install ffmpeg"
  else
    echo "ffmpeg is required. Install it with your package manager, for example: sudo apt install ffmpeg"
  fi
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[${extra},desktop]"
.venv/bin/lecturedub doctor
if [[ "$extra" == "apple" ]]; then
  .venv/bin/lecturedub install-app
  echo
  echo "LectureDub is in your Applications folder. You can also run: .venv/bin/lecturedub app"
else
  echo
  echo "Run: .venv/bin/lecturedub app"
fi
