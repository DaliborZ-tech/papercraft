"""Activity navigation for the authoring window; no document or camera state."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QWidget

CONTEXTS = ("Modelování", "Spoje a rozvin", "Stránky", "Export")


def wrap_control_text(control, width=220):
    """Let a native button keep its full caption in a narrow inspector."""
    words = control.text().replace("\n", " ").split()
    lines = []
    line = ""
    metrics = control.fontMetrics()
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and metrics.horizontalAdvance(candidate) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    control.setText("\n".join(lines))


class AuthorWorkspaceBar(QWidget):
    context_requested = Signal(str)
    sketch_requested = Signal(bool)
    preview_requested = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.buttons = {}
        for name in CONTEXTS:
            button = QToolButton()
            button.setText(name)
            button.setCheckable(True)
            # Preserve a pending property edit until the window validates it.
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda _checked, name=name: self.context_requested.emit(name))
            layout.addWidget(button)
            self.buttons[name] = button
        layout.addStretch()
        self.sketch_button = self._toggle("Skica", self.sketch_requested, layout)
        self.preview_button = self._toggle("Náhled 3D", self.preview_requested, layout)
        self.set_context(CONTEXTS[0])

    @staticmethod
    def _toggle(text, signal, layout):
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda checked: signal.emit(checked))
        layout.addWidget(button)
        return button

    def set_context(self, name):
        for context, button in self.buttons.items():
            button.setChecked(context == name)
        self.sketch_button.setVisible(name == "Modelování")
        self.preview_button.setVisible(name == "Stránky")
