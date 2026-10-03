"""Where lecturedub keeps jobs when it is launched as an app."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_home() -> Path:
    override = os.environ.get("LECTUREDUB_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LectureDub"
    return Path.home() / ".lecturedub"
