from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Callable, Sequence


def _default_app_root() -> Path:
    # src/nszees/nsz/wrapper.py -> project root in dev mode
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class NszResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.return_code == 0


class NszCommandError(RuntimeError):
    pass


class NszRunner:
    """Executes bundled nsz backend using the app root as working directory."""

    def __init__(self, app_root: Path | None = None) -> None:
        self.app_root = (app_root or _default_app_root()).resolve()
        self.nsz_python = (self.app_root / "bin" / "python.exe").resolve()
        self.nsz_script = (self.app_root / "bin" / "run_nsz.py").resolve()
        self._active_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()

    def quick_verify(self, nsp_path: Path) -> NszResult:
        return self._run(["--quick-verify", *self._keys_args(), str(Path(nsp_path).resolve())])

    def verify(self, nsp_path: Path) -> NszResult:
        return self._run(["--verify", *self._keys_args(), str(Path(nsp_path).resolve())])

    def compress_maximum_cancellable(
        self,
        nsp_path: Path,
        output_dir: Path | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ) -> tuple[NszResult, bool]:
        source = Path(nsp_path).resolve()
        destination = (output_dir or source.parent).resolve()
        destination.mkdir(parents=True, exist_ok=True)

        # XCI stays mountable (block mode) since cartridge dumps are commonly
        # used with emulators/mods that expect random access; NSP keeps the
        # higher-ratio solid mode, matching nsz's own NSZ default.
        mode_flag = "--block" if source.suffix.lower() == ".xci" else "--solid"

        args = [
            "-C",
            mode_flag,
            "--level",
            "22",
            "--long",
            "--threads",
            "0",
            "--overwrite",
            *self._keys_args(),
            "-o",
            str(destination),
            str(source),
        ]
        return self._run_cancellable(args, stop_requested=stop_requested)

    def decompress_cancellable(
        self,
        nsz_path: Path,
        output_dir: Path | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ) -> tuple[NszResult, bool]:
        destination = (output_dir or Path(nsz_path).resolve().parent).resolve()
        destination.mkdir(parents=True, exist_ok=True)

        args = [
            "-D",
            "--overwrite",
            *self._keys_args(),
            "-o",
            str(destination),
            str(Path(nsz_path).resolve()),
        ]
        return self._run_cancellable(args, stop_requested=stop_requested)

    def stop_active_process(self) -> bool:
        with self._process_lock:
            process = self._active_process
            if process is None or process.poll() is not None:
                return False
            self._terminate_process_tree(process)
            return True

    def _run(self, args: Sequence[str], timeout_seconds: float | None = None) -> NszResult:
        self._ensure_backend_present()

        command = [str(self.nsz_python), str(self.nsz_script), *args]
        completed = subprocess.run(
            command,
            cwd=str(self.app_root),
            env=self._subprocess_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )

        return NszResult(
            command=tuple(command),
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _run_cancellable(
        self,
        args: Sequence[str],
        stop_requested: Callable[[], bool] | None = None,
    ) -> tuple[NszResult, bool]:
        self._ensure_backend_present()

        command = [str(self.nsz_python), str(self.nsz_script), *args]
        process = subprocess.Popen(
            command,
            cwd=str(self.app_root),
            env=self._subprocess_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def _drain_stream(stream: object, sink: list[str]) -> None:
            if stream is None:
                return
            try:
                for line in iter(stream.readline, ""):
                    sink.append(line)
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        stdout_thread = threading.Thread(target=_drain_stream, args=(process.stdout, stdout_chunks), daemon=True)
        stderr_thread = threading.Thread(target=_drain_stream, args=(process.stderr, stderr_chunks), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        with self._process_lock:
            self._active_process = process

        stopped = False
        try:
            while process.poll() is None:
                if stop_requested and stop_requested():
                    stopped = True
                    self._terminate_process_tree(process)
                    break
                time.sleep(0.1)

            if process.poll() is None:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._terminate_process_tree(process)
                    process.wait()

            process.wait()
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
        finally:
            with self._process_lock:
                if self._active_process is process:
                    self._active_process = None

        return (
            NszResult(
                command=tuple(command),
                return_code=process.returncode,
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
            ),
            stopped,
        )

    def _subprocess_env(self) -> dict[str, str]:
        # Without this, the backend's own stdout defaults to the system ANSI
        # codepage (e.g. cp1252) when piped rather than UTF-8, and crashes
        # with UnicodeEncodeError the moment it needs to print a filename
        # (its own, or another file in the output directory it scans for
        # duplicates/versioning) containing a character outside that codepage.
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "UTF-8"
        return env

    def _ensure_backend_present(self) -> None:
        if not self.nsz_python.exists():
            raise NszCommandError(f"Missing bundled runtime: {self.nsz_python}")
        if not self.nsz_script.exists():
            raise NszCommandError(f"Missing bundled backend: {self.nsz_script}")

    def _keys_args(self) -> list[str]:
        prod_keys = self.app_root / "prod.keys"
        return ["--keys", str(prod_keys)] if prod_keys.exists() else []

    def _terminate_process_tree(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return

        if os.name == "nt":
            # /T ensures child processes (for example backend python workers) are also terminated.
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            return

        process.terminate()
