"""Erzeugt das Anwendungssymbol in allen benötigten Formaten.

Das Symbol wird gezeichnet statt als Bilddatei mitgeliefert: so bleibt das
Repository frei von Binärdateien und die Größen lassen sich jederzeit neu
erzeugen.

Aufruf:  python tools/make_icons.py
Ergebnis: resources/icon.png, resources/icon.icns (macOS), resources/icon.ico
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = PROJECT_ROOT / "resources"

# Größen, die macOS für ein .icns-Paket erwartet.
ICNS_SIZES = (16, 32, 64, 128, 256, 512, 1024)
# Größen, die in eine .ico-Datei für Windows gehören.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_icon(size: int) -> QImage:
    """Zeichnet das Symbol: ein Dokument mit Lupe auf blauem Grund."""
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    unit = size / 1024.0  # alle Maße beziehen sich auf ein 1024er Raster

    # --- Hintergrund: abgerundetes Quadrat mit Farbverlauf ---
    background = QRectF(0, 0, size, size)
    gradient = QLinearGradient(QPointF(0, 0), QPointF(size, size))
    gradient.setColorAt(0.0, QColor("#3b82f6"))
    gradient.setColorAt(1.0, QColor("#1d4ed8"))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(background, 224 * unit, 224 * unit)

    # --- Blatt Papier mit umgeknickter Ecke ---
    left, top = 246 * unit, 186 * unit
    width, height = 470 * unit, 600 * unit
    fold = 130 * unit

    page = QPainterPath()
    page.moveTo(left, top)
    page.lineTo(left + width - fold, top)
    page.lineTo(left + width, top + fold)
    page.lineTo(left + width, top + height)
    page.lineTo(left, top + height)
    page.closeSubpath()

    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.drawPath(page)

    corner = QPainterPath()
    corner.moveTo(left + width - fold, top)
    corner.lineTo(left + width, top + fold)
    corner.lineTo(left + width - fold, top + fold)
    corner.closeSubpath()
    painter.setBrush(QBrush(QColor("#c7d7f5")))
    painter.drawPath(corner)

    # --- Textzeilen auf dem Blatt ---
    painter.setBrush(QBrush(QColor("#9fb4d8")))
    line_left = left + 56 * unit
    line_height = 26 * unit
    for index, line_width in enumerate((300, 340, 250, 320, 190)):
        y = top + (210 + index * 78) * unit
        painter.drawRoundedRect(
            QRectF(line_left, y, line_width * unit, line_height),
            line_height / 2,
            line_height / 2,
        )

    # --- Lupe unten rechts ---
    centre = QPointF(700 * unit, 700 * unit)
    radius = 150 * unit
    stroke = 54 * unit

    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.setPen(Qt.PenStyle.NoPen)
    handle = QPainterPath()
    handle.moveTo(centre.x() + 96 * unit, centre.y() + 96 * unit)
    handle.lineTo(centre.x() + 250 * unit, centre.y() + 250 * unit)
    painter.setPen(
        QPen(QColor("#ffffff"), stroke * 1.15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    )
    painter.drawPath(handle)

    painter.setBrush(QBrush(QColor("#1d4ed8")))
    painter.setPen(QPen(QColor("#ffffff"), stroke))
    painter.drawEllipse(centre, radius, radius)

    # --- Buchstaben "A" in der Lupe, wenn das Symbol groß genug ist ---
    if size >= 64:
        font = QFont()
        font.setPixelSize(int(190 * unit))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        letter_box = QRectF(
            centre.x() - radius, centre.y() - radius, radius * 2, radius * 2
        )
        painter.drawText(letter_box, Qt.AlignmentFlag.AlignCenter, "A")

    painter.end()
    return image


def write_png(path: Path, size: int) -> None:
    """Zeichnet das Symbol in der angegebenen Größe und speichert es als PNG."""
    draw_icon(size).save(str(path), "PNG")


def build_icns(iconset_dir: Path, target: Path) -> bool:
    """Baut eine .icns-Datei; das geht nur auf macOS mit ``iconutil``."""
    if sys.platform != "darwin":
        return False
    iconset_dir.mkdir(parents=True, exist_ok=True)
    for size in ICNS_SIZES:
        write_png(iconset_dir / f"icon_{size}x{size}.png", size)
        # Retina-Varianten: doppelte Pixelzahl, halbe logische Größe.
        if size <= 512:
            write_png(iconset_dir / f"icon_{size}x{size}@2x.png", size * 2)
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"iconutil failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def build_ico(target: Path) -> bool:
    """Baut eine .ico-Datei mit allen Größen (benötigt Pillow)."""
    try:
        from PIL import Image
    except ImportError:
        print("Pillow is not installed - skipping icon.ico", file=sys.stderr)
        return False

    largest = RESOURCES / "icon_1024.png"
    write_png(largest, 1024)
    with Image.open(largest) as source:
        source.save(target, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    largest.unlink(missing_ok=True)
    return True


def main() -> int:
    # QPainter braucht eine laufende Qt-Anwendung, aber kein Fenster.
    """Erzeugt alle benötigten Symbolformate im Ordner resources/."""
    application = QApplication.instance() or QApplication(["make_icons"])
    RESOURCES.mkdir(parents=True, exist_ok=True)

    write_png(RESOURCES / "icon.png", 512)
    print(f"written: {RESOURCES / 'icon.png'}")

    iconset = RESOURCES / "icon.iconset"
    if build_icns(iconset, RESOURCES / "icon.icns"):
        print(f"written: {RESOURCES / 'icon.icns'}")
        for leftover in iconset.glob("*.png"):
            leftover.unlink()
        iconset.rmdir()

    if build_ico(RESOURCES / "icon.ico"):
        print(f"written: {RESOURCES / 'icon.ico'}")

    del application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
