"""Auswahl der OCR-Sprachen mit Suchfeld und Mehrfachauswahl."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ocrmypdf_gui import languages as language_names
from ocrmypdf_gui.i18n import tr


class LanguageDialog(QDialog):
    """Listet alle installierten Sprachpakete zum Ankreuzen auf."""

    def __init__(
        self,
        available: Sequence[str],
        selected: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.language"))
        self.setMinimumSize(400, 480)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText(tr("settings.language.search"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self._counter = QLabel(self)
        self._counter.setObjectName("Hint")

        # Eigene Ankreuzfelder statt der eingebauten Markierung von
        # QListWidgetItem: deren Darstellung ist unter macOS unzuverlässig,
        # angekreuzte Einträge blieben ohne sichtbares Häkchen.
        self._boxes: List[Tuple[str, QCheckBox]] = []
        ui_language = tr.language
        chosen = set(selected)
        for code in language_names.order_for_display(list(available), ui_language):
            box = QCheckBox(language_names.display_name(code, ui_language), self._list)
            box.setChecked(code in chosen)
            box.toggled.connect(self._update_counter)

            item = QListWidgetItem(self._list)
            item.setSizeHint(QSize(0, box.sizeHint().height() + 8))
            self._list.addItem(item)
            self._list.setItemWidget(item, box)
            self._boxes.append((code, box))

        hint = QLabel(tr("settings.language.help"), self)
        hint.setObjectName("Hint")
        hint.setWordWrap(True)

        self._manage_button = QPushButton(tr("settings.language.manage"), self)
        self._manage_button.clicked.connect(self._open_download_dialog)

        self._cancel_button = QPushButton(tr("action.cancel"), self)
        self._cancel_button.clicked.connect(self.reject)
        self._ok_button = QPushButton(tr("action.ok"), self)
        self._ok_button.setObjectName("Primary")
        self._ok_button.setDefault(True)
        self._ok_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(self._manage_button)
        buttons.addStretch(1)
        buttons.addWidget(self._cancel_button)
        buttons.addWidget(self._ok_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._counter)
        layout.addWidget(hint)
        layout.addLayout(buttons)

        self._update_counter()

    # ------------------------------------------------------------------
    def selected_languages(self) -> List[str]:
        """Die angekreuzten Sprachcodes in Anzeigereihenfolge."""
        return [code for code, box in self._boxes if box.isChecked()]

    def _apply_filter(self, text: str) -> None:
        """Blendet Einträge aus, die nicht zum Suchbegriff passen."""
        needle = text.strip().lower()
        for row, (_code, box) in enumerate(self._boxes):
            item = self._list.item(row)
            if item is not None:
                item.setHidden(bool(needle) and needle not in box.text().lower())

    def _open_download_dialog(self) -> None:
        """Öffnet die Sprachverwaltung und baut die Liste danach neu auf."""
        from ocrmypdf_gui.ui.download_dialog import DownloadDialog

        dialog = DownloadDialog(self)
        dialog.exec()
        if dialog.changed:
            self._rebuild_list()

    def _rebuild_list(self) -> None:
        """Baut die Auswahlliste neu auf, ohne die Auswahl zu verlieren."""
        from ocrmypdf_gui import dependencies

        gewaehlt = set(self.selected_languages())
        self._list.clear()
        self._boxes.clear()
        ui_language = tr.language
        for code in language_names.order_for_display(dependencies.available_languages(), ui_language):
            box = QCheckBox(language_names.display_name(code, ui_language), self._list)
            box.setChecked(code in gewaehlt)
            box.toggled.connect(self._update_counter)
            item = QListWidgetItem(self._list)
            item.setSizeHint(QSize(0, box.sizeHint().height() + 8))
            self._list.addItem(item)
            self._list.setItemWidget(item, box)
            self._boxes.append((code, box))
        self._apply_filter(self._search.text())
        self._update_counter()

    def _update_counter(self) -> None:
        """Schreibt die Anzahl gewählter Sprachen fort und sperrt OK bei null."""
        count = len(self.selected_languages())
        self._counter.setText(tr("settings.language.selected", count=count))
        # Ohne Sprache lässt sich keine Texterkennung starten.
        self._ok_button.setEnabled(count > 0)
