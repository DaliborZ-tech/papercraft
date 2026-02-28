"""Main application entry-point for ArchPapercraft Studio."""

from __future__ import annotations

import sys


def main() -> None:
    """Launch the ArchPapercraft Studio GUI."""
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ArchPapercraft Studio")
    app.setOrganizationName("ArchPapercraft")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
