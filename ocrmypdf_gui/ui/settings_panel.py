"""Export-Einstellungen: PDF-Typ, Sprache, Speicherort und erweiterte Optionen."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ocrmypdf_gui import dependencies
from ocrmypdf_gui import languages as language_names
from ocrmypdf_gui.i18n import SUPPORTED_UI_LANGUAGES, tr
from ocrmypdf_gui.models import (
    DEFAULT_OPTIMIZE_LEVEL,
    ExportSettings,
    OcrMode,
    OutputMode,
    PdfType,
)
from ocrmypdf_gui.ui.language_dialog import LanguageDialog
from ocrmypdf_gui.ui.widgets import Card, CollapsibleSection, Field, horizontal_separator

# Reihenfolge der Optimierungsstufen in der Auswahlliste.
_OPTIMIZE_LEVELS = (0, 1, 2, 3)


class SettingsPanel(Card):
    """Alle Einstellungen in einer Karte: Grundlagen oben, Erweitertes zum Aufklappen."""

    settingsChanged = Signal()
    uiLanguageChanged = Signal(str)

    def __init__(self, settings: ExportSettings, parent: QWidget | None = None) -> None:
        super().__init__(tr("settings.title"), parent)
        self._settings = settings
        self._available_languages: List[str] = []
        # Verhindert, dass das Befüllen der Elemente bereits Änderungen meldet.
        self._loading = False

        self._build_basic()
        self.body.addWidget(horizontal_separator(self))
        self._build_advanced()

        self._available_languages = dependencies.available_languages()
        self.load(settings)
        # Eine gespeicherte Sprache kann inzwischen deinstalliert sein; dann
        # würde OCRmyPDF beim Start mit einem Fehler abbrechen.
        self.refresh_languages()

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------
    def _build_basic(self) -> None:
        # --- PDF-Typ ---
        """Baut die Grundeinstellungen: PDF-Typ, Sprache und Speicherort."""
        self._pdf_type = QComboBox(self)
        for pdf_type in PdfType:
            self._pdf_type.addItem("", pdf_type.value)
        self._pdf_type.currentIndexChanged.connect(self._on_pdf_type_changed)
        self._pdf_type_field = Field(tr("settings.pdftype"), self._pdf_type, tr("settings.pdftype.help"))
        self.body.addWidget(self._pdf_type_field)

        # --- Sprache ---
        self._language_button = QPushButton(self)
        self._language_button.clicked.connect(self._choose_languages)
        self._language_field = Field(
            tr("settings.language"), self._language_button, tr("settings.language.help")
        )
        self.body.addWidget(self._language_field)

        # --- Speicherort ---
        self._output_mode = QComboBox(self)
        self._output_mode.addItem("", OutputMode.SUBFOLDER.value)
        self._output_mode.addItem("", OutputMode.FIXED.value)
        self._output_mode.currentIndexChanged.connect(self._on_output_mode_changed)

        self._output_path = QLineEdit(self)
        self._output_path.setReadOnly(True)
        self._output_path.textChanged.connect(self._emit_changed)

        self._browse_button = QPushButton(self)
        self._browse_button.clicked.connect(self._choose_folder)

        self._open_folder_button = QPushButton(self)
        self._open_folder_button.setObjectName("Link")
        self._open_folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_button.clicked.connect(self._open_folder)

        folder_row = QWidget(self)
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        folder_layout.addWidget(self._output_path, 1)
        folder_layout.addWidget(self._browse_button)

        output_container = QWidget(self)
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(6)
        output_layout.addWidget(self._output_mode)
        output_layout.addWidget(folder_row)
        output_layout.addWidget(self._open_folder_button, 0, Qt.AlignmentFlag.AlignLeft)

        self._folder_row = folder_row
        self._output_field = Field(tr("settings.output"), output_container)
        self.body.addWidget(self._output_field)

    def _build_advanced(self) -> None:
        """Baut den aufklappbaren Bereich mit den erweiterten Einstellungen."""
        self._advanced = CollapsibleSection(tr("advanced.title"), self)
        content = self._advanced.content

        # --- Umgang mit vorhandenem Text ---
        self._ocr_mode = QComboBox(self)
        for mode in OcrMode:
            self._ocr_mode.addItem("", mode.value)
        self._ocr_mode.currentIndexChanged.connect(self._emit_changed)
        self._ocr_mode_field = Field(
            tr("advanced.mode"), self._ocr_mode, tr("advanced.mode.help")
        )
        content.addWidget(self._ocr_mode_field)

        # --- Optimierungsstufe ---
        self._optimize = QComboBox(self)
        for level in _OPTIMIZE_LEVELS:
            self._optimize.addItem("", level)
        self._optimize.currentIndexChanged.connect(self._emit_changed)
        self._optimize_field = Field(tr("advanced.optimize"), self._optimize)
        content.addWidget(self._optimize_field)

        # --- Bildverbesserungen ---
        self._checkboxes = {}
        for key, label_key in (
            ("deskew", "advanced.deskew"),
            ("rotate_pages", "advanced.rotate"),
            ("clean", "advanced.clean"),
            ("clean_final", "advanced.cleanFinal"),
            ("remove_background", "advanced.removeBackground"),
            ("sidecar_text", "advanced.sidecar"),
            ("overwrite_existing", "advanced.overwrite"),
        ):
            box = QCheckBox(tr(label_key), self)
            box.setProperty("labelKey", label_key)
            box.toggled.connect(self._emit_changed)
            self._checkboxes[key] = box
            content.addWidget(box)

        # "Gesäubertes Bild übernehmen" ergibt nur zusammen mit "Säubern" Sinn.
        self._checkboxes["clean"].toggled.connect(self._sync_clean_dependency)

        # --- Namenszusatz ---
        self._suffix = QLineEdit(self)
        self._suffix.setMaxLength(32)
        self._suffix.textEdited.connect(self._emit_changed)
        self._suffix_field = Field(tr("advanced.suffix"), self._suffix)
        content.addWidget(self._suffix_field)

        # --- Zahlenwerte ---
        self._jobs = QSpinBox(self)
        self._jobs.setRange(0, 32)
        self._jobs.setSpecialValueText(tr("advanced.jobs.auto"))
        self._jobs.valueChanged.connect(self._emit_changed)
        self._jobs_field = Field(tr("advanced.jobs"), self._jobs)
        content.addWidget(self._jobs_field)

        self._dpi = QSpinBox(self)
        self._dpi.setRange(0, 2400)
        self._dpi.setSingleStep(50)
        self._dpi.setSpecialValueText(tr("advanced.jobs.auto"))
        self._dpi.valueChanged.connect(self._emit_changed)
        self._dpi_field = Field(tr("advanced.dpi"), self._dpi)
        content.addWidget(self._dpi_field)

        self._timeout = QSpinBox(self)
        self._timeout.setRange(0, 3600)
        self._timeout.setSingleStep(30)
        self._timeout.setSpecialValueText(tr("advanced.timeout.none"))
        self._timeout.valueChanged.connect(self._emit_changed)
        self._timeout_field = Field(tr("advanced.timeout"), self._timeout)
        content.addWidget(self._timeout_field)

        # --- Sprache der Oberfläche ---
        self._ui_language = QComboBox(self)
        for code, name in SUPPORTED_UI_LANGUAGES.items():
            self._ui_language.addItem(name, code)
        self._ui_language.currentIndexChanged.connect(self._on_ui_language_changed)
        self._ui_language_field = Field(
            tr("advanced.uiLanguage"), self._ui_language, tr("advanced.restartHint")
        )
        content.addWidget(self._ui_language_field)

        self._reset_button = QPushButton(tr("advanced.reset"), self)
        self._reset_button.setObjectName("Link")
        self._reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_button.clicked.connect(self._reset_defaults)
        content.addWidget(self._reset_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.body.addWidget(self._advanced)

    # ------------------------------------------------------------------
    # Laden und Speichern
    # ------------------------------------------------------------------
    def load(self, settings: ExportSettings) -> None:
        """Überträgt gespeicherte Einstellungen in die Bedienelemente."""
        self._loading = True
        self._settings = settings

        self._select_by_data(self._pdf_type, settings.pdf_type.value)
        self._select_by_data(self._ocr_mode, settings.ocr_mode.value)
        self._select_by_data(self._output_mode, settings.output_mode.value)
        self._select_by_data(self._optimize, settings.optimize_level)
        self._select_by_data(self._ui_language, settings.ui_language)

        for key, box in self._checkboxes.items():
            box.setChecked(bool(getattr(settings, key)))

        self._suffix.setText(settings.filename_suffix)
        self._jobs.setValue(settings.jobs)
        self._dpi.setValue(settings.image_dpi)
        self._timeout.setValue(settings.page_timeout)
        self._output_path.setText(settings.output_folder or str(Path.home() / "OCR"))

        self._loading = False
        self.retranslate()
        self._sync_clean_dependency()
        self._on_output_mode_changed()

    def apply_to(self, settings: ExportSettings) -> ExportSettings:
        """Liest die Bedienelemente in ein Einstellungsobjekt zurück."""
        settings.pdf_type = PdfType(self._pdf_type.currentData())
        settings.ocr_mode = OcrMode(self._ocr_mode.currentData())
        settings.output_mode = OutputMode(self._output_mode.currentData())
        level = int(self._optimize.currentData())
        # Sicherheitsnetz: eine gesperrte Stufe würde OCRmyPDF abbrechen lassen.
        settings.optimize_level = (
            level if dependencies.optimize_level_available(level) else DEFAULT_OPTIMIZE_LEVEL
        )
        settings.output_folder = self._output_path.text().strip() or None
        for key, box in self._checkboxes.items():
            setattr(settings, key, box.isChecked())
        settings.filename_suffix = self._suffix.text()
        settings.jobs = self._jobs.value()
        settings.image_dpi = self._dpi.value()
        settings.page_timeout = self._timeout.value()
        settings.ui_language = str(self._ui_language.currentData())
        return settings

    @property
    def settings(self) -> ExportSettings:
        """Die Einstellungen auf dem Stand der Bedienelemente."""
        return self.apply_to(self._settings)

    # ------------------------------------------------------------------
    # Sprachen
    # ------------------------------------------------------------------
    def refresh_languages(self) -> None:
        """Liest die installierten Sprachpakete neu ein."""
        self._available_languages = dependencies.available_languages()
        self._prune_missing_languages()
        self._update_language_button()

    def _prune_missing_languages(self) -> None:
        """Entfernt Sprachen aus der Auswahl, deren Paket nicht (mehr) da ist.

        Bleibt dabei nichts übrig, wird ein Ersatz gesucht: zuerst die Sprache
        der Oberfläche, dann die jeweils andere, zuletzt irgendeine vorhandene.
        Ohne diesen letzten Schritt stünde die Anwendung ohne Sprache da und
        ließe sich nicht mehr starten, obwohl Sprachpakete vorhanden sind.
        """
        if not self._available_languages:
            return
        kept = [code for code in self._settings.languages if code in self._available_languages]
        if not kept:
            bevorzugt = ["deu", "eng"] if tr.language == "de" else ["eng", "deu"]
            auswahl = [
                code for code in self._available_languages
                if language_names.is_selectable(code)
            ]
            ersatz = next(
                (code for code in bevorzugt if code in auswahl),
                auswahl[0] if auswahl else None,
            )
            kept = [ersatz] if ersatz else []
        self._settings.languages = kept

    def _choose_languages(self) -> None:
        """Öffnet die Sprachauswahl und übernimmt das Ergebnis."""
        available = self._available_languages or list(self._settings.languages)
        dialog = LanguageDialog(available, self._settings.languages, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_languages()
        if chosen:
            self._settings.languages = chosen
            self._update_language_button()
            self._emit_changed()

    def _update_language_button(self) -> None:
        """Beschriftet die Sprachschaltfläche mit der aktuellen Auswahl."""
        codes = self._settings.languages
        if not codes:
            self._language_button.setText(tr("settings.language.none"))
            return
        ui_language = tr.language
        names = [language_names.display_name(code, ui_language).split(" (")[0] for code in codes]
        shown = ", ".join(names[:3])
        if len(names) > 3:
            shown += f" +{len(names) - 3}"
        self._language_button.setText(shown)
        self._language_button.setToolTip(
            ", ".join(language_names.display_name(code, ui_language) for code in codes)
        )

    # ------------------------------------------------------------------
    # Ereignisse
    # ------------------------------------------------------------------
    def _on_pdf_type_changed(self) -> None:
        """Zeigt die Erläuterung zum gewählten PDF-Typ."""
        pdf_type = PdfType(self._pdf_type.currentData())
        self._pdf_type_field.set_hint(tr(pdf_type.description_key))
        self._emit_changed()

    def _on_output_mode_changed(self) -> None:
        """Blendet die Ordnerauswahl je nach Speicherort ein oder aus."""
        is_fixed = self._output_mode.currentData() == OutputMode.FIXED.value
        self._folder_row.setVisible(is_fixed)
        self._open_folder_button.setVisible(is_fixed)
        self._emit_changed()

    def _on_ui_language_changed(self) -> None:
        """Stellt die Sprache der Oberfläche um."""
        if self._loading:
            return
        code = str(self._ui_language.currentData())
        tr.set_language(code)
        self.uiLanguageChanged.emit(code)
        self._emit_changed()

    def _sync_clean_dependency(self) -> None:
        """Koppelt das Übernehmen des gesäuberten Bildes an das Säubern selbst."""
        clean_enabled = self._checkboxes["clean"].isChecked()
        final = self._checkboxes["clean_final"]
        final.setEnabled(clean_enabled)
        if not clean_enabled and final.isChecked():
            final.setChecked(False)

    def _choose_folder(self) -> None:
        """Öffnet die Ordnerauswahl für den festen Zielordner."""
        start = self._output_path.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, tr("settings.output.dialog"), start)
        if folder:
            self._output_path.setText(folder)

    def _open_folder(self) -> None:
        """Öffnet den eingestellten Zielordner im Dateimanager."""
        folder = self._output_path.text().strip()
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _reset_defaults(self) -> None:
        """Setzt alles auf die Werkseinstellungen zurück; die Sprache bleibt."""
        defaults = ExportSettings()
        defaults.ui_language = str(self._ui_language.currentData())
        defaults.languages = list(self._settings.languages)
        self.load(defaults)
        self._emit_changed()

    def _emit_changed(self, *_args) -> None:
        """Meldet eine Änderung, sofern gerade nicht geladen wird."""
        if not self._loading:
            self.settingsChanged.emit()

    def _refresh_optimize_levels(self) -> None:
        """Beschriftet die Optimierungsstufen und sperrt die nicht nutzbaren.

        OCRmyPDF bricht ab, wenn pngquant oder jbig2enc fehlen. Statt den
        Nutzer in diesen Fehler laufen zu lassen, ist die Stufe von vornherein
        nicht auswählbar und nennt den Grund.
        """
        model = self._optimize.model()
        any_blocked = False
        for index in range(self._optimize.count()):
            level = int(self._optimize.itemData(index))
            label = tr(f"advanced.optimize.{level}")
            missing = dependencies.missing_optimize_tools(level)
            if missing:
                any_blocked = True
                self._optimize.setItemText(
                    index,
                    tr(
                        "advanced.optimize.unavailable",
                        level=label,
                        tools=", ".join(missing),
                    ),
                )
            else:
                self._optimize.setItemText(index, label)
            item = model.item(index) if hasattr(model, "item") else None
            if item is not None:
                item.setEnabled(not missing)

        self._optimize_field.set_hint(tr("advanced.optimize.hint") if any_blocked else "")

        # Stand die Auswahl auf einer gesperrten Stufe, auf den Standard zurück.
        current = self._optimize.currentData()
        if current is not None and dependencies.missing_optimize_tools(int(current)):
            self._select_by_data(self._optimize, DEFAULT_OPTIMIZE_LEVEL)

    # ------------------------------------------------------------------
    @staticmethod
    def _select_by_data(combo: QComboBox, value) -> None:
        """Wählt den Eintrag einer Auswahlliste anhand seines Datenwerts."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def retranslate(self) -> None:
        """Alle Beschriftungen neu setzen, etwa nach einem Sprachwechsel."""
        was_loading = self._loading
        self._loading = True

        self.set_title(tr("settings.title"))
        self._pdf_type_field.set_label(tr("settings.pdftype"))
        for index in range(self._pdf_type.count()):
            pdf_type = PdfType(self._pdf_type.itemData(index))
            self._pdf_type.setItemText(index, tr(pdf_type.label_key))
        self._pdf_type_field.set_hint(tr(PdfType(self._pdf_type.currentData()).description_key))

        self._language_field.set_label(tr("settings.language"))
        self._language_field.set_hint(tr("settings.language.help"))
        self._update_language_button()

        self._output_field.set_label(tr("settings.output"))
        self._output_mode.setItemText(0, tr("settings.output.sameAsSource"))
        self._output_mode.setItemText(1, tr("settings.output.custom"))
        self._browse_button.setText(tr("settings.output.browse"))
        self._open_folder_button.setText(tr("settings.output.open"))

        self._advanced.set_title(tr("advanced.title"))
        self._ocr_mode_field.set_label(tr("advanced.mode"))
        self._ocr_mode_field.set_hint(tr("advanced.mode.help"))
        for index in range(self._ocr_mode.count()):
            mode = OcrMode(self._ocr_mode.itemData(index))
            self._ocr_mode.setItemText(index, tr(f"advanced.mode.{mode.value.split('-')[0]}"))

        self._optimize_field.set_label(tr("advanced.optimize"))
        self._refresh_optimize_levels()

        for box in self._checkboxes.values():
            box.setText(tr(str(box.property("labelKey"))))

        self._suffix_field.set_label(tr("advanced.suffix"))
        self._suffix.setPlaceholderText(tr("advanced.suffix.placeholder"))
        self._jobs_field.set_label(tr("advanced.jobs"))
        self._jobs.setSpecialValueText(tr("advanced.jobs.auto"))
        self._dpi_field.set_label(tr("advanced.dpi"))
        self._dpi.setSpecialValueText(tr("advanced.jobs.auto"))
        self._timeout_field.set_label(tr("advanced.timeout"))
        self._timeout.setSpecialValueText(tr("advanced.timeout.none"))
        self._ui_language_field.set_label(tr("advanced.uiLanguage"))
        self._ui_language_field.set_hint(tr("advanced.restartHint"))
        self._reset_button.setText(tr("advanced.reset"))

        self._loading = was_loading
