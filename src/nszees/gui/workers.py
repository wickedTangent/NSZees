from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import traceback

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    """Signals emitted by a background worker."""

    finished = Signal(object)
    failed = Signal(str)


@dataclass
class WorkerTask:
    """Callable task metadata for background execution."""

    fn: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None


class Worker(QRunnable):
    """Runs a callable in a thread-pool worker thread."""

    def __init__(self, task: WorkerTask) -> None:
        super().__init__()
        self._task = task
        self.signals = WorkerSignals()

    def run(self) -> None:
        kwargs = self._task.kwargs or {}
        try:
            result = self._task.fn(*self._task.args, **kwargs)
            self.signals.finished.emit(result)
        except Exception:
            self.signals.failed.emit(traceback.format_exc())
