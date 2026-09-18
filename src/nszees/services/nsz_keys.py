"""Bridge our root prod.keys into the bundled nsz library's in-process key cache.

The nsz Python package keeps a module-level key cache populated once, at first
import, from either a `keys.txt` next to the running script or `~/.switch/prod.keys` —
neither of which tracks this app's own root `prod.keys`. Anything that parses
tickets/NCAs in-process (rather than shelling out to nsz.exe) must call `sync()`
first so it sees the same keys the user actually supplied.
"""

from __future__ import annotations

from pathlib import Path

from nsz.nut import Keys


def sync(app_root: Path) -> None:
    """Load this app's root prod.keys into the nsz library's key cache, if present."""
    prod_keys = app_root / "prod.keys"
    if prod_keys.exists():
        Keys.load(str(prod_keys))
