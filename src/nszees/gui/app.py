from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow

_APP_ICON_REL_PATH = Path("assets") / "icon.ico"


def _configure_qt_environment() -> None:
    """Point Qt to bundled plugin paths when running from portable runtime."""
    bin_dir = Path(sys.executable).resolve().parent
    pyside_dir = bin_dir / "Lib" / "site-packages" / "PySide6"
    plugins_dir = pyside_dir / "plugins"
    platforms_dir = plugins_dir / "platforms"

    if plugins_dir.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_dir))
    if platforms_dir.exists():
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platforms_dir))


def run_app() -> int:
    _configure_qt_environment()
    app = QApplication(sys.argv)
    app.setApplicationName("NSZees")

    app_root = Path(__file__).resolve().parents[3]
    icon_path = app_root / _APP_ICON_REL_PATH
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
