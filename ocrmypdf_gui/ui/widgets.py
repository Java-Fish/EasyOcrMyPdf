"""Kleine, wiederverwendbare Bausteine der Oberfläche."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    """Eine abgerundete Fläche mit optionaler Überschrift."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        self._title = QLabel(title, self)
        self._title.setObjectName("CardTitle")
        self._title.setVisible(bool(title))

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(12)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)
        outer.addWidget(self._title)
        outer.addLayout(self._body)

    def set_title(self, title: str) -> None:
        """Ändert die Überschrift."""
        self._title.setText(title)
        self._title.setVisible(bool(title))

    @property
    def body(self) -> QVBoxLayout:
        """Layout, in das der Inhalt der Karte eingehängt wird."""
        return self._body


class Field(QWidget):
    """Beschriftung, Eingabeelement und darunter ein erklärender Hinweis."""

    def __init__(
        self,
        label: str,
        widget: QWidget,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._label = QLabel(label, self)
        self._label.setObjectName("FieldLabel")
        self._label.setBuddy(widget)

        self._hint = QLabel(hint, self)
        self._hint.setObjectName("FieldHint")
        self._hint.setWordWrap(True)
        self._hint.setVisible(bool(hint))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self._label)
        layout.addWidget(widget)
        layout.addWidget(self._hint)

        self.widget = widget

    def set_label(self, text: str) -> None:
        """Ändert die Beschriftung des Feldes."""
        self._label.setText(text)

    def set_hint(self, text: str) -> None:
        """Ändert den Hinweis unter dem Feld; leerer Text blendet ihn aus."""
        self._hint.setText(text)
        self._hint.setVisible(bool(text))


class CollapsibleSection(QWidget):
    """Ein aufklappbarer Bereich, hier für die erweiterten Einstellungen."""

    toggled = Signal(bool)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._button = QPushButton(self)
        self._button.setObjectName("Link")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setCheckable(True)
        self._button.clicked.connect(self._on_clicked)
        self._title = title

        self._content = QWidget(self)
        self._content.setVisible(False)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 8, 0, 0)
        self._content_layout.setSpacing(14)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._button)
        header.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self._content)

        self._update_button_text()

    @property
    def content(self) -> QVBoxLayout:
        """Layout, in das der aufklappbare Inhalt eingehängt wird."""
        return self._content_layout

    def set_title(self, title: str) -> None:
        """Ändert die Überschrift."""
        self._title = title
        self._update_button_text()

    def is_expanded(self) -> bool:
        """True, wenn der Bereich aufgeklappt ist."""
        return self._button.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        """Klappt den Bereich auf oder zu."""
        self._button.setChecked(expanded)
        self._content.setVisible(expanded)
        self._update_button_text()

    def _on_clicked(self, checked: bool) -> None:
        """Klappt den Bereich um und meldet den neuen Zustand."""
        self._content.setVisible(checked)
        self._update_button_text()
        self.toggled.emit(checked)

    def _update_button_text(self) -> None:
        # Kleines Dreieck als Auf-/Zuklapp-Anzeige.
        """Aktualisiert Pfeil und Beschriftung der Schaltfläche."""
        arrow = "▾" if self._button.isChecked() else "▸"
        self._button.setText(f"{arrow}  {self._title}")


def horizontal_separator(parent: QWidget | None = None) -> QFrame:
    """Dünne Trennlinie."""
    line = QFrame(parent)
    line.setObjectName("Separator")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line


def row(*widgets: QWidget, spacing: int = 8) -> QHBoxLayout:
    """Legt mehrere Widgets nebeneinander."""
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def value_label(text: str = "", parent: Optional[QWidget] = None) -> QLabel:
    """Ein Label für abgeleitete Werte (z. B. den aktuellen Zielpfad)."""
    label = QLabel(text, parent)
    label.setObjectName("Hint")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label
