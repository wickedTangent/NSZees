"""Portable, file-based app settings (no registry, no user profile writes)."""

from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_PATH_REL = Path("config") / "settings.json"


def _settings_path(app_root: Path) -> Path:
    return app_root / _SETTINGS_PATH_REL


def _read_settings(app_root: Path) -> dict:
    path = _settings_path(app_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_last_input_dir(app_root: Path) -> Path | None:
    """Return the last-used input directory, if it still exists on disk."""
    raw = _read_settings(app_root).get("last_input_dir")
    if not raw:
        return None
    candidate = Path(raw)
    return candidate if candidate.is_dir() else None


def save_last_input_dir(app_root: Path, directory: Path) -> None:
    """Persist the given directory as the last-used input directory."""
    path = _settings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_settings(app_root)
    data["last_input_dir"] = str(directory)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
