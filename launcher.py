"""
Detached launcher for NSZees GUI on Windows.

Spawns run_nszees.py in a fully detached process with no console window.
This launcher itself exits immediately after spawning the app process.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    entrypoint = root / "run_nszees.py"

    if not entrypoint.exists():
        print(f"[NSZees] Missing entrypoint: {entrypoint}", file=sys.stderr)
        return 1

    python_exe = root / "bin" / "python.exe"
    if not python_exe.exists():
        print(f"[NSZees] Missing runtime: {python_exe}", file=sys.stderr)
        return 1

    try:
        # CREATE_NO_WINDOW = 0x08000000
        # CREATE_NEW_PROCESS_GROUP = 0x00000200
        # Flags ensure the spawned app runs detached from this console window
        subprocess.Popen(
            [str(python_exe), str(entrypoint)],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 | 0x00000200,
        )
        return 0
    except Exception as e:
        print(f"[NSZees] Failed to launch: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
