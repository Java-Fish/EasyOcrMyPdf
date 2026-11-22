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


def print_process_tree(pid: int) -> None:
    """Zeigt, welche Kindprozesse noch laufen; hilft, einen Hänger zu orten."""
    try:
        import psutil
    except ImportError:
        print("  (install psutil to see the remaining child processes)", file=sys.stderr)
        return
    try:
        for child in psutil.Process(pid).children(recursive=True):
            print(f"  still running: pid {child.pid} {child.cmdline()}", file=sys.stderr)
    except psutil.Error as error:
        print(f"  process tree unavailable: {error}", file=sys.stderr)


def kill_tree(process: subprocess.Popen) -> None:
    """Beendet den Prozess samt Kindern, damit nichts hängen bleibt."""
    try:
        import psutil

        for child in psutil.Process(process.pid).children(recursive=True):
            child.kill()
    except Exception:
        pass
    process.kill()
    process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("binary", type=Path, help="das gebaute Programm")
    parser.add_argument("--language", default="deu", help="Tesseract-Sprachcode")
    parser.add_argument("--timeout", type=int, default=600, help="Sekunden bis zum Abbruch")
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
        # Die Ausgabe geht in eine Datei statt in eine Pipe: so bleibt sie
        # auch dann lesbar, wenn der Prozess hängt und abgebrochen wird.
        log_path = Path(folder) / "ausgabe.txt"
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                return_code = process.wait(timeout=arguments.timeout)
            except subprocess.TimeoutExpired:
                print(f"FAILED: no result after {arguments.timeout} s", file=sys.stderr)
                print_process_tree(process.pid)
                kill_tree(process)
                return_code = None
        print(log_path.read_text(encoding="utf-8", errors="replace")[-6000:])

        if return_code != 0 or not target.is_file():
            print(f"FAILED: exit code {return_code}", file=sys.stderr)
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
