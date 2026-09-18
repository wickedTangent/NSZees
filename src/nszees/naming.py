"""Filename utilities shared across the nsz backend wrapper and GUI."""

from __future__ import annotations

from pathlib import Path


def unique_destination_path(path: Path) -> Path:
    """Return path unchanged if free, otherwise the first "name (n).ext" that is free.

    Mirrors the Windows Explorer convention for resolving filename collisions.
    """
    if not path.exists():
        return path

    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
