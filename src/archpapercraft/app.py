"""Main application entry-point for ArchPapercraft Studio."""

from __future__ import annotations

import logging
import sys

_log = logging.getLogger("archpapercraft")


def _setup_logging() -> None:
    """Inicializace logování — soubor + konzole.

    Nikdy nevyhodí výjimku; v nejhorším bude logovat jen na stderr.
    """
    root = logging.getLogger("archpapercraft")
    root.setLevel(logging.DEBUG)

    # Konzolový handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    # Souborový handler (bezpečný fallback)
    try:
        from archpapercraft.project_io.project import _ensure_log_dir

        log_dir = _ensure_log_dir()
        fh = logging.FileHandler(log_dir / "archpapercraft.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
        )
        root.addHandler(fh)
    except Exception:
        pass  # Nikdy nespadnout kvůli logování


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Globální handler neošetřených výjimek — zapíše crash report."""
    # Nepřepisovat KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    _log.critical("Neošetřená výjimka", exc_info=(exc_type, exc_value, exc_tb))

    try:
        from archpapercraft.project_io.project import Project

        path = Project.write_crash_report(exc_value)
        if path:
            _log.critical("Crash report: %s", path)
    except Exception:
        pass

    # Zobrazit dialog uživateli pokud je GUI k dispozici
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app_inst = QApplication.instance()
        if app_inst is not None:
            QMessageBox.critical(
                None,
                "Kritická chyba",
                f"Nastala neočekávaná chyba:\n\n"
                f"{exc_type.__name__}: {exc_value}\n\n"
                f"Crash report byl uložen.",
            )
    except Exception:
        pass


def main() -> None:
    """Launch the ArchPapercraft Studio GUI."""
    _setup_logging()
    sys.excepthook = _global_exception_handler

    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ArchPapercraft Studio")
    app.setOrganizationName("ArchPapercraft")
    app.setApplicationVersion("0.2.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
