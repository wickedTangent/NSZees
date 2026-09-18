from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nszees.naming import unique_destination_path
from nszees.nsz import NszRunner
from nszees.services import (
    FileValidator,
    ValidationResult,
    build_renamed_output_name,
    load_last_input_dir,
    save_last_input_dir,
    summarise_nsz_output,
    summarise_validation,
)
from nszees.services.staging import is_risky_backend_path, stage_input_copy

from .workers import Worker, WorkerTask


@dataclass
class UiState:
    selected_file: Path | None = None
    validation_result: ValidationResult | None = None
    busy: bool = False
    compression_stop_requested: bool = False
    compression_stoppable: bool = False
    operation_completed: bool = False


class MainWindow(QMainWindow):
    """Main desktop UI for NSP/XCI validation and NSZ/XCZ compression."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NSZees")
        self.resize(900, 640)

        self._thread_pool = QThreadPool.globalInstance()
        self._active_workers: set[Worker] = set()
        self._validator = FileValidator()
        self._runner = NszRunner()
        self._state = UiState()

        icon_path = self._runner.app_root / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._on_elapsed_tick)
        self._elapsed_started_at = 0.0

        self._build_ui()
        self._set_idle_state()
        self._refresh_prod_keys_warning()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        file_group = QGroupBox("Input NSP/NSZ/XCI/XCZ")
        file_layout = QGridLayout(file_group)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._choose_file)
        file_layout.addWidget(self.file_path_edit, 0, 0)
        file_layout.addWidget(self.browse_button, 0, 1)
        self.key_status_label = QLabel("Required key: -")
        file_layout.addWidget(self.key_status_label, 1, 0, 1, 2)
        self.prod_keys_warning_label = QLabel()
        self.prod_keys_warning_label.setStyleSheet("color: #b00020;")
        self.prod_keys_warning_label.setVisible(False)
        file_layout.addWidget(self.prod_keys_warning_label, 2, 0, 1, 2)

        status_group = QGroupBox("Status")
        status_layout = QGridLayout(status_group)
        self.step_label = QLabel("Idle")
        self.elapsed_label = QLabel("Elapsed: 00:00")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        status_layout.addWidget(self.step_label, 0, 0)
        status_layout.addWidget(self.elapsed_label, 0, 1)
        status_layout.addWidget(self.progress, 1, 0, 1, 2)

        actions = QHBoxLayout()
        self.validate_button = QPushButton("Validate")
        self.validate_button.clicked.connect(self._start_validation)
        self.deep_verify_button = QPushButton("Deep Verify")
        self.deep_verify_button.clicked.connect(self._start_deep_verify)
        self.compress_button = QPushButton("Compress")
        self.compress_button.clicked.connect(self._start_compress)
        self.force_compress_button = QPushButton("Compress (Force)")
        self.force_compress_button.clicked.connect(self._start_force_compress)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._request_stop)
        self.rename_output_checkbox = QCheckBox("Rename output filename")
        self.rename_output_checkbox.setChecked(True)
        actions.addWidget(self.validate_button)
        actions.addWidget(self.deep_verify_button)
        actions.addWidget(self.force_compress_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.rename_output_checkbox)
        actions.addStretch(1)
        actions.addWidget(self.compress_button)

        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        layout.addWidget(file_group)
        layout.addWidget(status_group)
        layout.addLayout(actions)
        layout.addWidget(results_group, stretch=1)

    def _choose_file(self) -> None:
        start_dir = load_last_input_dir(self._runner.app_root) or Path.cwd()
        picked, _ = QFileDialog.getOpenFileName(
            self,
            "Select NSP/NSZ/XCI/XCZ",
            str(start_dir),
            "Nintendo Package Files (*.nsp *.nsz *.xci *.xcz);;"
            "NSP files (*.nsp);;NSZ files (*.nsz);;"
            "XCI files (*.xci);;XCZ files (*.xcz);;"
            "All files (*.*)",
        )
        if not picked:
            return

        path = Path(picked).resolve()
        save_last_input_dir(self._runner.app_root, path.parent)
        self._state.selected_file = path
        self._state.validation_result = None
        self._state.operation_completed = False
        self.file_path_edit.setText(str(path))
        self.results_text.clear()
        self.results_text.append(f"Selected: {path}")
        self.key_status_label.setText("Required key: checking...")
        self._refresh_prod_keys_warning()
        self._set_idle_state()
        self._start_validation()

    def _start_validation(self) -> None:
        if not self._state.selected_file:
            QMessageBox.warning(self, "No File Selected", "Select an NSP/NSZ/XCI/XCZ file first.")
            return

        self._set_busy_state("Validating...")
        worker = Worker(WorkerTask(fn=self._validator.validate, args=(str(self._state.selected_file),)))
        worker.signals.finished.connect(self._on_validation_done)
        worker.signals.failed.connect(self._on_task_failed)
        self._start_worker(worker)

    def _on_validation_done(self, result: ValidationResult) -> None:
        self._state.validation_result = result
        self._set_idle_state()
        self._update_key_status_label(result)

        self.results_text.clear()
        self.results_text.append(summarise_validation(result))

        if result.can_force_compress and not result.can_compress:
            QMessageBox.warning(
                self,
                "Quick Verify Failed",
                "Quick verification failed. You can still use Compress (Force).",
            )

        if not result.container_valid:
            QMessageBox.critical(self, "Container Check Failed", result.container_error or "Invalid PFS0 container")

        self._refresh_action_state()

    def _start_compress(self) -> None:
        if not self._state.validation_result or not self._state.validation_result.can_compress:
            QMessageBox.warning(self, "Compression Blocked", "Run validation successfully before compressing.")
            return

        action = self._state.validation_result.primary_action
        if action == "decompress":
            self._run_decompress()
        else:
            self._run_compress(force=False)

    def _start_deep_verify(self) -> None:
        if not self._state.selected_file:
            QMessageBox.warning(self, "No File Selected", "Select an NSP/NSZ/XCI/XCZ file first.")
            return

        self._set_busy_state("Deep verifying...")
        worker = Worker(WorkerTask(fn=self._runner.verify, args=(self._state.selected_file,)))
        worker.signals.finished.connect(self._on_deep_verify_done)
        worker.signals.failed.connect(self._on_task_failed)
        self._start_worker(worker)

    def _start_force_compress(self) -> None:
        result = self._state.validation_result
        if not result or not result.can_force_compress:
            QMessageBox.warning(self, "Force Compress Unavailable", "Force compress is only available after quick verify fails.")
            return

        answer = QMessageBox.question(
            self,
            "Confirm Force Compress",
            "Quick verification failed. Continue with force compression?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._run_compress(force=True)

    def _run_compress(self, force: bool, use_staging: bool = False) -> None:
        assert self._state.selected_file is not None
        self._state.compression_stop_requested = False
        label = "Compressing (staging copy)..." if use_staging else "Compressing..."
        self._set_busy_state(label, compression_stoppable=True)
        worker = Worker(WorkerTask(fn=self._compress_task, args=(self._state.selected_file, use_staging)))
        worker.signals.finished.connect(lambda result: self._on_compress_done(result, force, use_staging))
        worker.signals.failed.connect(self._on_task_failed)
        self._start_worker(worker)

    def _run_decompress(self) -> None:
        assert self._state.selected_file is not None
        self._state.compression_stop_requested = False
        self._set_busy_state("Decompressing...", compression_stoppable=True)
        worker = Worker(WorkerTask(fn=self._decompress_task, args=(self._state.selected_file,)))
        worker.signals.finished.connect(self._on_decompress_done)
        worker.signals.failed.connect(self._on_task_failed)
        self._start_worker(worker)

    def _start_worker(self, worker: Worker) -> None:
        self._active_workers.add(worker)
        worker.signals.finished.connect(lambda _result, _worker=worker: self._release_worker(_worker))
        worker.signals.failed.connect(lambda _trace, _worker=worker: self._release_worker(_worker))
        self._thread_pool.start(worker)

    def _release_worker(self, worker: Worker) -> None:
        self._active_workers.discard(worker)

    def _compress_task(self, source_path: Path, use_staging: bool) -> tuple[object, Path | None, bool]:
        run_path = source_path
        staged_path = None

        if use_staging:
            staged_path = stage_input_copy(source_path, self._runner.app_root)
            run_path = staged_path

        result, stopped = self._runner.compress_maximum_cancellable(
            run_path,
            output_dir=source_path.parent,
            stop_requested=lambda: self._state.compression_stop_requested,
        )
        return result, staged_path, stopped

    def _decompress_task(self, source_path: Path) -> tuple[object, bool]:
        result, stopped = self._runner.decompress_cancellable(
            source_path,
            output_dir=source_path.parent,
            stop_requested=lambda: self._state.compression_stop_requested,
        )
        return result, stopped

    def _on_compress_done(self, payload: tuple[object, Path | None, bool], force: bool, used_staging: bool) -> None:
        elapsed_seconds = int(time.monotonic() - self._elapsed_started_at)
        self._set_idle_state()
        result, staged_path, stopped = payload

        # NszResult is a dataclass from wrapper; keep this defensive for type safety.
        ok = getattr(result, "ok", False)
        return_code = getattr(result, "return_code", -1)
        stdout = getattr(result, "stdout", "")
        stderr = getattr(result, "stderr", "")

        mode = "Force" if force else "Normal"
        self.results_text.append(f"\n── {mode} Compression")
        if staged_path is not None:
            self.results_text.append(f"ℹ️  Staging copy: {staged_path.name}")

        output_path = self._locate_compressed_output(staged_path)
        renamed_to = self._rename_output_if_enabled(output_path)
        final_output_path = renamed_to or output_path
        if output_path is not None:
            self.results_text.append(f"ℹ️  Output file: {output_path.name}")
        if renamed_to is not None and output_path is not None and renamed_to != output_path:
            self.results_text.append(f"✅  Renamed output: {renamed_to.name}")

        self.results_text.append(summarise_nsz_output(stdout, stderr, return_code))

        if ok and not stopped:
            self._append_compression_savings_summary(final_output_path, elapsed_seconds)
            self._state.operation_completed = True

        if stopped:
            QMessageBox.information(self, "Compression Stopped", "Compression was stopped by user request.")
        elif ok:
            QMessageBox.information(self, "Compression Complete", "Compression completed successfully.")
        else:
            if not used_staging and self._state.selected_file and is_risky_backend_path(self._state.selected_file):
                answer = QMessageBox.question(
                    self,
                    "Retry Using Staging Copy",
                    "Compression failed on a risky path. Retry using a staging copy in temp/staging?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self._run_compress(force=force, use_staging=True)
                    return

            if "Failed to decrypt NCA header" in stderr:
                QMessageBox.critical(
                    self,
                    "Compression Failed",
                    "A partition inside this cartridge dump (commonly the bundled firmware/"
                    "update partition) couldn't be decrypted with your keys, so compression "
                    "was aborted. This is a known limitation for some XCI dumps and isn't "
                    "specific to NSZees.",
                )
            else:
                QMessageBox.critical(self, "Compression Failed", f"Compression failed (exit code {return_code}).")

        self._refresh_action_state()

    def _append_compression_savings_summary(self, output_path: Path | None, elapsed_seconds: int) -> None:
        source_path = self._state.selected_file
        if source_path is None or output_path is None:
            return
        if not source_path.exists() or not output_path.exists():
            return

        source_size = source_path.stat().st_size
        output_size = output_path.stat().st_size
        if source_size <= 0:
            return

        saved_bytes = source_size - output_size
        if saved_bytes <= 0:
            return

        saved_mb = saved_bytes / (1024 * 1024)
        saved_pct = (saved_bytes / source_size) * 100.0
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        self.results_text.append("")
        self.results_text.append(
            f"💾 Saved {saved_mb:.2f}MBs ({saved_pct:.0f}%) in {minutes:02d}:{seconds:02d} mins"
        )

    def _on_deep_verify_done(self, result: object) -> None:
        self._set_idle_state()

        ok = getattr(result, "ok", False)
        return_code = getattr(result, "return_code", -1)
        stdout = getattr(result, "stdout", "")
        stderr = getattr(result, "stderr", "")

        self.results_text.append(summarise_nsz_output(stdout, stderr, return_code))

        if ok:
            QMessageBox.information(self, "Deep Verify Complete", "Deep verify completed successfully.")
        else:
            QMessageBox.warning(self, "Deep Verify Failed", f"Deep verify failed (exit code {return_code}).")

        self._refresh_action_state()

    def _on_decompress_done(self, payload: tuple[object, bool]) -> None:
        self._set_idle_state()
        result, stopped = payload

        ok = getattr(result, "ok", False)
        return_code = getattr(result, "return_code", -1)
        stdout = getattr(result, "stdout", "")
        stderr = getattr(result, "stderr", "")

        self.results_text.append(summarise_nsz_output(stdout, stderr, return_code))

        if stopped:
            QMessageBox.information(self, "Decompression Stopped", "Decompression was stopped by user request.")
        elif ok:
            QMessageBox.information(self, "Decompression Complete", "Decompression completed successfully.")
            self._state.operation_completed = True
        else:
            QMessageBox.critical(self, "Decompression Failed", f"Decompression failed (exit code {return_code}).")

        self._refresh_action_state()

    def _on_task_failed(self, trace: str) -> None:
        self._set_idle_state()
        self.results_text.append("\nUnexpected error:\n")
        self.results_text.append(trace)
        QMessageBox.critical(self, "Task Failed", "An unexpected error occurred. See details in the results pane.")
        self._refresh_action_state()

    def _request_stop(self) -> None:
        if not (self._state.busy and self._state.compression_stoppable):
            return

        self._state.compression_stop_requested = True
        self._runner.stop_active_process()
        self.step_label.setText("Stopping compression...")
        self.stop_button.setEnabled(False)

    def _set_busy_state(self, label: str, compression_stoppable: bool = False) -> None:
        self._state.busy = True
        self._state.compression_stoppable = compression_stoppable
        self.step_label.setText(label)
        self.progress.setVisible(True)
        self._elapsed_started_at = time.monotonic()
        self.elapsed_label.setText("Elapsed: 00:00")
        self._elapsed_timer.start()
        self._refresh_action_state()

    def _locate_compressed_output(self, staged_path: Path | None) -> Path | None:
        if self._state.selected_file is None:
            return None

        compressed_suffix = ".xcz" if self._state.selected_file.suffix.lower() == ".xci" else ".nsz"
        output_dir = self._state.selected_file.parent
        candidates = [output_dir / f"{self._state.selected_file.stem}{compressed_suffix}"]
        if staged_path is not None:
            candidates.append(output_dir / f"{staged_path.stem}{compressed_suffix}")

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _rename_output_if_enabled(self, output_path: Path | None) -> Path | None:
        if output_path is None:
            return None
        if not self.rename_output_checkbox.isChecked():
            return output_path
        if self._state.selected_file is None:
            return output_path

        target_name = build_renamed_output_name(self._state.selected_file, self._runner.app_root)
        if not target_name:
            return output_path

        target_path = output_path.with_name(target_name)
        if target_path == output_path:
            return output_path

        unique_target = unique_destination_path(target_path)
        if unique_target != target_path:
            self.results_text.append(f"ℹ️  Target name existed, used: {unique_target.name}")

        output_path.replace(unique_target)
        return unique_target

    def _set_idle_state(self) -> None:
        self._state.busy = False
        self._state.compression_stoppable = False
        self._state.compression_stop_requested = False
        self.step_label.setText("Idle")
        self.progress.setVisible(False)
        self._elapsed_timer.stop()
        self.elapsed_label.setText("Elapsed: 00:00")
        self._refresh_action_state()

    def _refresh_prod_keys_warning(self) -> None:
        prod_keys_present = (self._runner.app_root / "prod.keys").exists()
        self.prod_keys_warning_label.setVisible(not prod_keys_present)
        if not prod_keys_present:
            self.prod_keys_warning_label.setText(
                "⚠️  prod.keys not found in app folder — place it next to NSZees before compressing."
            )

    def _update_key_status_label(self, result: ValidationResult) -> None:
        if result.required_key_name and result.required_key_present is True:
            self.key_status_label.setText(f"Required key: ✅ {result.required_key_name}")
            return
        if result.required_key_name and result.required_key_present is False:
            self.key_status_label.setText(f"Required key: ❌ {result.required_key_name}")
            return
        self.key_status_label.setText("Required key: -")

    def _on_elapsed_tick(self) -> None:
        elapsed = int(time.monotonic() - self._elapsed_started_at)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self.elapsed_label.setText(f"Elapsed: {minutes:02d}:{seconds:02d}")

    def _refresh_action_state(self) -> None:
        has_file = self._state.selected_file is not None
        result = self._state.validation_result

        self.browse_button.setEnabled(not self._state.busy)
        self.validate_button.setEnabled(has_file and not self._state.busy)
        self.deep_verify_button.setEnabled(has_file and not self._state.busy)

        can_compress = bool(result and result.can_compress) and not self._state.operation_completed
        can_force = bool(result and result.can_force_compress) and not self._state.operation_completed

        if result and result.primary_action == "decompress":
            self.compress_button.setText("Decompress")
        else:
            self.compress_button.setText("Compress")

        self.compress_button.setEnabled(can_compress and not self._state.busy)
        self.force_compress_button.setEnabled(can_force and not self._state.busy)
        self.stop_button.setEnabled(self._state.busy and self._state.compression_stoppable)
        self.rename_output_checkbox.setEnabled(not self._state.busy)
