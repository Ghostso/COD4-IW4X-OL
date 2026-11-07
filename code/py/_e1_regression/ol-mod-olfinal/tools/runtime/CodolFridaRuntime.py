"""Keep Frida's extracted runtime files inside the CODOL workspace."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEMP = REPOSITORY_ROOT / ".runtime" / "frida"
DEFAULT_MAX_AGE_HOURS = 24


def _cleanup_stale_frida_directories(root: Path, max_age_hours: int) -> None:
    cutoff = time.time() - max_age_hours * 60 * 60
    for candidate in root.glob("frida-*"):
        try:
            if not candidate.is_dir() or candidate.stat().st_mtime >= cutoff:
                continue
            shutil.rmtree(candidate)
        except OSError:
            # Another Frida process may still have a helper or DLL open.
            continue


def configure_frida_runtime() -> Path:
    """Select the project temp directory before importing the Frida package."""
    RUNTIME_TEMP.mkdir(parents=True, exist_ok=True)
    runtime_temp = str(RUNTIME_TEMP)
    os.environ["TEMP"] = runtime_temp
    os.environ["TMP"] = runtime_temp
    os.environ["TMPDIR"] = runtime_temp
    tempfile.tempdir = runtime_temp

    try:
        max_age_hours = max(
            1,
            int(os.environ.get("CODOL_FRIDA_TEMP_MAX_AGE_HOURS", DEFAULT_MAX_AGE_HOURS)),
        )
    except ValueError:
        max_age_hours = DEFAULT_MAX_AGE_HOURS
    _cleanup_stale_frida_directories(RUNTIME_TEMP, max_age_hours)
    return RUNTIME_TEMP
