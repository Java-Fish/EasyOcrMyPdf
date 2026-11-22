"""Farben und Stylesheet der Anwendung.

Qt bringt auf jeder Plattform ein anderes Standardaussehen mit. Damit die
Anwendung überall gleich aufgeräumt wirkt, definieren wir hier ein eigenes,
schlichtes Design, einmal hell und einmal dunkel.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Farbtoken. Der Schlüssel wird im Stylesheet als {name} eingesetzt.
LIGHT: Dict[str, str] = {
    "bg": "#f4f5f7",
    "surface": "#ffffff",
    "surfaceAlt": "#fafbfc",
    "border": "#d9dde4",
    "borderStrong": "#c2c8d2",
    "text": "#1b1f27",
    "muted": "#646c7a",
    "accent": "#2563eb",
    "accentHover": "#1d4ed8",
    "accentPressed": "#1e40af",
    "accentSoft": "#eef3ff",
    "success": "#15803d",
    "successSoft": "#e8f6ec",
    "danger": "#c02626",
    "dangerSoft": "#fdeaea",
    "warning": "#b45309",
    "onAccent": "#ffffff",
    "disabled": "#a2a9b5",
}

DARK: Dict[str, str] = {
    "bg": "#181b21",
    "surface": "#22262e",
    "surfaceAlt": "#1e222a",
    "border": "#343a45",
    "borderStrong": "#454c59",
    "text": "#e7eaef",
    "muted": "#98a0ad",
    "accent": "#4a86f7",
    "accentHover": "#699bf9",
    "accentPressed": "#3b6fd4",
    "accentSoft": "#1f2a3d",
    "success": "#49b877",
    "successSoft": "#1c2f25",
    "danger": "#e5716b",
    "dangerSoft": "#331f20",
    "warning": "#e0a955",
    "onAccent": "#ffffff",
    "disabled": "#5d6472",
}

_STYLESHEET = """
QWidget {{
    color: {text};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {bg};
}}

/* --- Karten: die weißen Flächen, aus denen das Fenster aufgebaut ist --- */
QFrame#Card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QLabel#CardTitle {{
    font-size: 14px;
    font-weight: 600;
}}
QLabel#Hint, QLabel#FieldHint {{
    color: {muted};
    font-size: 12px;
}}
QLabel#HeaderTitle {{
    font-size: 21px;
    font-weight: 600;
}}
QLabel#HeaderSubtitle {{
    color: {muted};
    font-size: 13px;
}}
QLabel#FieldLabel {{
    font-weight: 600;
}}
QLabel#StatusText {{
    color: {muted};
}}

/* --- Ablagebereich --- */
QFrame#DropArea {{
    background: {surfaceAlt};
    border: 2px dashed {borderStrong};
    border-radius: 14px;
}}
QFrame#DropArea[state="hover"] {{
    background: {accentSoft};
    border-color: {accent};
}}
QFrame#DropArea[state="active"] {{
    background: {accentSoft};
    border: 2px solid {accent};
}}
QFrame#DropArea[state="rejected"] {{
    background: {dangerSoft};
    border-color: {danger};
}}
QLabel#DropTitle {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#DropSubtitle {{
    color: {muted};
}}
QLabel#DropIcon {{
    font-size: 34px;
}}

/* --- Schaltflächen --- */
QPushButton {{
    background: {surface};
    border: 1px solid {borderStrong};
    border-radius: 7px;
    padding: 7px 14px;
    min-height: 18px;
}}
QPushButton:hover {{
    background: {accentSoft};
    border-color: {accent};
}}
QPushButton:pressed {{
    background: {accentSoft};
    border-color: {accentPressed};
}}
QPushButton:disabled {{
    color: {disabled};
    border-color: {border};
    background: {surfaceAlt};
}}
QPushButton#Primary {{
    background: {accent};
    border: 1px solid {accent};
    color: {onAccent};
    font-weight: 600;
    padding: 11px 26px;
    font-size: 14px;
}}
QPushButton#Primary:hover {{ background: {accentHover}; border-color: {accentHover}; }}
QPushButton#Primary:pressed {{ background: {accentPressed}; border-color: {accentPressed}; }}
QPushButton#Primary:disabled {{ background: {disabled}; border-color: {disabled}; color: {surface}; }}
QPushButton#Danger {{ color: {danger}; }}
QPushButton#Danger:hover {{ background: {dangerSoft}; border-color: {danger}; }}
QPushButton#Link {{
    background: transparent;
    border: none;
    color: {accent};
    padding: 2px 4px;
    text-align: left;
}}
QPushButton#Link:hover {{ text-decoration: underline; background: transparent; }}

/* --- Eingabefelder --- */
QComboBox, QLineEdit, QSpinBox {{
    background: {surface};
    border: 1px solid {borderStrong};
    border-radius: 7px;
    padding: 6px 10px;
    min-height: 18px;
    selection-background-color: {accent};
    selection-color: {onAccent};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{
    border-color: {accent};
}}
QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled {{
    color: {disabled};
    background: {surfaceAlt};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {surface};
    border: 1px solid {borderStrong};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {accent};
    selection-color: {onAccent};
    outline: none;
}}

/* Das Ankreuzfeld selbst zeichnet bewusst das Betriebssystem: eine eigene
   Gestaltung über das Stylesheet ersetzt auch das Häkchen, und ein gefülltes
   Kästchen ohne Haken ist schwerer zu deuten. */
QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QCheckBox:disabled {{ color: {disabled}; }}

/* --- Listen --- */
QListWidget {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{ border-radius: 7px; padding: 0px; margin: 2px; }}
QListWidget::item:selected {{ background: {accentSoft}; }}

/* --- Fortschritt --- */
QProgressBar {{
    background: {surfaceAlt};
    border: 1px solid {border};
    border-radius: 6px;
    height: 10px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}

/* --- Protokoll --- */
QPlainTextEdit#Log {{
    background: {surfaceAlt};
    border: 1px solid {border};
    border-radius: 9px;
    color: {muted};
    font-family: "SF Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 11px;
}}

/* --- Trenner und Bildlaufleisten --- */
QFrame#Separator {{ background: {border}; max-height: 1px; border: none; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {borderStrong}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {borderStrong}; border-radius: 5px; min-width: 28px; }}

QToolTip {{
    background: {surface};
    color: {text};
    border: 1px solid {borderStrong};
    border-radius: 6px;
    padding: 5px 8px;
}}
"""


def is_dark_mode(app: QApplication) -> bool:
    """Erkennt anhand der Systempalette, ob ein dunkles Design aktiv ist."""
    window_color = app.palette().color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


def palette_for(colors: Dict[str, str]) -> QPalette:
    """Basispalette, damit auch nicht gestylte Elemente zum Design passen."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surfaceAlt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["onAccent"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text"]))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors["disabled"])
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors["disabled"])
    )
    return palette


def apply_theme(app: QApplication) -> Dict[str, str]:
    """Wendet Stil, Palette und Stylesheet an und liefert die aktiven Farben zurück."""
    # "Fusion" statt des Systemstils: Qt zeichnet angekreuzte Kästchen unter
    # macOS sonst nur als gefüllte Fläche ohne Häkchen. Fusion stellt sie
    # korrekt dar und sieht auf macOS und Windows gleich aus.
    app.setStyle("Fusion")

    colors = DARK if is_dark_mode(app) else LIGHT
    app.setPalette(palette_for(colors))
    app.setStyleSheet(_STYLESHEET.format(**colors))
    return colors
