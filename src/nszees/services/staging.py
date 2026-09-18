from __future__ import annotations

from pathlib import Path
import shutil
import string


_MAX_SAFE_BACKEND_PATH = 240
_SAFE_CHARS = set(string.ascii_letters + string.digits + "._-() []")


def is_risky_backend_path(path: Path) -> bool:
    """Return True if the path may be unsafe for the backend to process directly."""
    path_str = str(path)
    return len(path_str) >= _MAX_SAFE_BACKEND_PATH or any(char not in _SAFE_CHARS and ord(char) > 127 for char in path_str)


def stage_input_copy(source_path: Path, app_root: Path) -> Path:
    """Copy an input file into temp/staging using a backend-safe ASCII name."""
    source_path = Path(source_path).resolve()
    staging_dir = Path(app_root).resolve() / "temp" / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    suffix = source_path.suffix.lower() or ".nsp"
    destination = staging_dir / f"staged_input{suffix}"
    counter = 1
    while destination.exists():
        destination = staging_dir / f"staged_input_{counter}{suffix}"
        counter += 1

    shutil.copy2(source_path, destination)
    return destination
