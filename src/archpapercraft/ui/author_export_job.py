"""Responsive vector publication of one detached snapshot with safe cancellation."""
# ruff: noqa: N802 -- Qt event overrides.

from __future__ import annotations

import copy
import threading

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from archpapercraft.exporter.author_export import ExportCancelledError, export_all


class _Signals(QObject):
    phase = Signal(str)
    finished = Signal(object, object)


class _ExportJob(QRunnable):
    def __init__(self, snapshot, directory, function):
        super().__init__()
        self.snapshot = copy.deepcopy(snapshot)
        self.directory, self.function = directory, function
        self.cancel_requested = threading.Event()
        self.signals = _Signals()

    def checkpoint(self, phase):
        if self.cancel_requested.is_set():
            raise ExportCancelledError("Export byl zrušen; předchozí výstupy zůstaly zachované.")
        self.signals.phase.emit(phase)

    def run(self):
        try:
            result = self.function(self.snapshot, self.directory, checkpoint=self.checkpoint)
        except Exception as exc:
            self.signals.finished.emit(None, exc)
        else:
            self.signals.finished.emit(result, None)


class ExportProgressDialog(QDialog):
    def __init__(self, snapshot, directory, parent=None, *, function=export_all):
        super().__init__(parent)
        self.setWindowTitle("Připravuji SVG a PDF")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(440)
        self.result_paths, self.error = None, None
        self.cancelled = self.finished_during_cancel = self._finished = False
        layout = QVBoxLayout(self)
        self.description = QLabel(
            "Připravuji vektorové výstupy. Model i stránky zůstávají zachované."
        )
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        progress = QProgressBar()
        progress.setRange(0, 0)
        layout.addWidget(progress)
        self.cancel_button = QPushButton("Zrušit export")
        self.cancel_button.clicked.connect(self.request_cancel)
        layout.addWidget(self.cancel_button)
        self.job = _ExportJob(snapshot, directory, function)
        self.job.signals.phase.connect(self._phase)
        self.job.signals.finished.connect(self._done)
        QTimer.singleShot(0, lambda: QThreadPool.globalInstance().start(self.job))

    def _phase(self, phase):
        if phase == "publish":
            self.cancel_button.setEnabled(False)
        if not self.job.cancel_requested.is_set():
            self.description.setText(
                {
                    "prepare": "Kontroluji model a připravuji podklady pro export…",
                    "vectors": "Vytvářím editovatelné SVG stránky a vektorové PDF…",
                    "verify": "Ověřuji přesnost, otvory a úplnost skutečných výstupů…",
                    "publish": "Ukládám ověřené soubory. Dokončuji celou sadu…",
                }[phase]
            )

    def request_cancel(self):
        if self._finished:
            return
        self.job.cancel_requested.set()
        self.cancel_button.setEnabled(False)
        self.description.setText("Ruším export. Čekám na bezpečné dokončení aktuální kontroly…")

    def _done(self, paths, error):
        self.result_paths, self.error = paths, error
        self.cancelled = isinstance(error, ExportCancelledError)
        self.finished_during_cancel = paths is not None and self.job.cancel_requested.is_set()
        self._finished = True
        self.done(QDialog.DialogCode.Accepted if paths is not None else QDialog.DialogCode.Rejected)

    def reject(self):
        self.request_cancel()

    def closeEvent(self, event):
        if self._finished:
            event.accept()
        else:
            self.request_cancel()
            event.ignore()
