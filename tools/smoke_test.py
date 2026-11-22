"""Prüft ein fertig gebautes Programm mit einer echten Texterkennung.

Erzeugt eine eingescannt wirkende PDF-Seite, schickt sie über den
``--ocr-worker``-Modus durch das gebaute Programm und prüft, ob der Text
anschließend in der PDF steht. Damit ist belegt, dass Python, OCRmyPDF,
Tesseract samt Sprachdaten und Ghostscript im Paket zusammenspielen.

Aufruf:
    python tools/smoke_test.py "dist/EasyOcrMyPdf.app/Contents/MacOS/EasyOcrMyPdf"
    python tools/smoke_test.py dist/easyocrmypdf/easyocrmypdf --language deu
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LINES = ("Rechnung Nummer 4711", "Sehr geehrte Damen und Herren,", "die Texterkennung funktioniert.")
EXPECTED_WORDS = ("Rechnung", "4711", "Texterkennung")


def make_scan(path: Path) -> None:
    """Schreibt eine Seite, die nur aus einem Bild besteht, wie nach einem Scan."""
    image = Image.new("L", (1700, 2200), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=64)
    for number, text in enumerate(LINES):
        draw.text((150, 200 + number * 120), text, fill=0, font=font)
    image.save(path, resolution=200)


def extract_text(path: Path) -> str:
    """Liest die Textebene der PDF aus."""
    from pdfminer.high_level import extract_text as pdfminer_extract

    return pdfminer_extract(str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", type=Path, help="das gebaute Programm")
    parser.add_argument("--language", default="deu", help="Tesseract-Sprachcode")
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "scan.pdf"
        target = Path(folder) / "ergebnis.pdf"
        make_scan(source)

        command = [
            str(arguments.binary), "--ocr-worker",
            "-l", arguments.language, "--output-type", "pdfa",
            str(source), str(target),
        ]
        print("$", " ".join(command), flush=True)
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        print(result.stdout[-4000:])
        print(result.stderr[-4000:], file=sys.stderr)

        if result.returncode != 0 or not target.is_file():
            print(f"FAILED: exit code {result.returncode}", file=sys.stderr)
            return 1

        text = extract_text(target)
        missing = [word for word in EXPECTED_WORDS if word not in text]
        if missing:
            print(f"FAILED: words not recognised: {missing}\n{text!r}", file=sys.stderr)
            return 1

    print("OK: text recognised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
