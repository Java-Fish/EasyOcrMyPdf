"""Kopiert Tesseract und Ghostscript nach ``vendor\\windows``.

Unter Windows sind beide Programme bereits in sich abgeschlossen: ihre DLLs
liegen neben der .exe. Es genügt daher, die Installationsordner zu kopieren;
ein Umschreiben von Bibliothekspfaden wie unter macOS ist nicht nötig.

Voraussetzung: Tesseract und Ghostscript sind installiert, z. B. mit

    winget install -e --id UB-Mannheim.TesseractOCR
    winget install -e --id ArtifexSoftware.GhostScript

Aufruf:
    python tools\\vendor_windows.py                        # Deutsch und Englisch
    python tools\\vendor_windows.py --languages european   # 26 europäische Sprachen
    python tools\\vendor_windows.py --languages all        # alle installierten
    python tools\\vendor_windows.py --tesseract "C:\\Pfad" --ghostscript "C:\\Pfad"
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR = PROJECT_ROOT / "vendor" / "windows"

# Sprachpakete, die in die fertigen Pakete eingebettet werden.
#
# "standard" ist die Voreinstellung und enthält nur Deutsch und Englisch. Das
# hält das Paket klein genug, um es als Release-Artefakt hochladen zu können
# (Codeberg nimmt höchstens 100 MB je Datei). Alle übrigen Sprachen lassen sich
# jederzeit nachinstallieren; die Anwendung zeigt automatisch an, was vorhanden
# ist.
#
# "osd" ist keine Sprache, sondern das Modell zur Erkennung von Schriftrichtung
# und Schriftsystem. Ohne dieses Modell scheitert die Einstellung "Seiten
# automatisch drehen".
STANDARD_LANGUAGES = ("deu", "eng", "osd")

# Die in Europa gebräuchlichen Sprachen, für ein bewusst größeres Paket.
EUROPEAN_LANGUAGES = (
    "deu", "deu_latf", "eng", "fra", "spa", "ita", "nld", "por", "pol",
    "ces", "dan", "swe", "nor", "fin", "hun", "ron", "tur", "rus", "ell",
    "ukr", "slk", "slv", "hrv", "bul", "cat", "lat", "osd",
)


def candidate_tesseract_dirs() -> List[Path]:
    """Übliche Installationsorte von Tesseract."""
    return [
        Path(r"C:\Program Files\Tesseract-OCR"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR")),
    ]


def candidate_ghostscript_dirs() -> List[Path]:
    """Ghostscript installiert sich versioniert, z. B. C:\\Program Files\\gs\\gs10.03.1."""
    found: List[Path] = []
    for base in (Path(r"C:\Program Files\gs"), Path(r"C:\Program Files (x86)\gs")):
        if base.is_dir():
            # Neueste Version zuerst.
            found.extend(sorted((d for d in base.iterdir() if d.is_dir()), reverse=True))
    return found


def first_existing(paths: List[Path], marker: str) -> Optional[Path]:
    """Erster Ordner, der die erwartete Programmdatei enthält."""
    for path in paths:
        if (path / marker).is_file() or any(path.glob(f"**/{marker}")):
            return path
    return None


def copy_tree(source: Path, destination: Path) -> int:
    """Kopiert einen Ordner und liefert die kopierte Größe in Bytes."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return sum(f.stat().st_size for f in destination.rglob("*") if f.is_file())


def parse_languages(value: str) -> Optional[Set[str]]:
    """Wertet die Option ``--languages`` aus. ``None`` bedeutet: alle."""
    gewaehlt = value.strip().lower()
    if gewaehlt == "all":
        return None
    if gewaehlt == "standard":
        return set(STANDARD_LANGUAGES)
    if gewaehlt == "european":
        return set(EUROPEAN_LANGUAGES)
    return {code.strip() for code in value.split(",") if code.strip()}


def main() -> int:
    """Kopiert Programme und Sprachdateien nach vendor/windows."""
    if sys.platform != "win32":
        print("This script only runs on Windows.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Bundle Tesseract and Ghostscript.")
    parser.add_argument("--tesseract", type=Path, help="Tesseract installation folder")
    parser.add_argument("--ghostscript", type=Path, help="Ghostscript installation folder")
    parser.add_argument(
        "--languages",
        default="standard",
        help='"standard" (Vorgabe: deu, eng, osd), "european", "all" '
             'oder eine Liste wie "deu,eng,fra"',
    )
    arguments = parser.parse_args()

    tesseract_dir = arguments.tesseract or first_existing(
        candidate_tesseract_dirs(), "tesseract.exe"
    )
    if tesseract_dir is None or not (tesseract_dir / "tesseract.exe").is_file():
        print(
            "ERROR: Tesseract not found. Install it or pass --tesseract <folder>.\n"
            "    winget install -e --id UB-Mannheim.TesseractOCR",
            file=sys.stderr,
        )
        return 1

    ghostscript_dir = arguments.ghostscript or first_existing(
        candidate_ghostscript_dirs(), "gswin64c.exe"
    )
    if ghostscript_dir is None:
        print(
            "ERROR: Ghostscript not found. Install it or pass --ghostscript <folder>.\n"
            "    winget install -e --id ArtifexSoftware.GhostScript",
            file=sys.stderr,
        )
        return 1

    VENDOR.mkdir(parents=True, exist_ok=True)

    print(f"Copying Tesseract from {tesseract_dir} ...")
    # Zielstruktur muss zu dependencies._candidate_paths() passen.
    size = copy_tree(tesseract_dir, VENDOR / "tesseract")
    print(f"  {size / 1024 / 1024:.0f} MB")

    print(f"Copying Ghostscript from {ghostscript_dir} ...")
    size = copy_tree(ghostscript_dir, VENDOR / "gs")
    print(f"  {size / 1024 / 1024:.0f} MB")

    # Die Sprachdateien liegen bei Tesseract unter tessdata/ und werden von
    # dependencies.tessdata_dir() unter vendor\windows\share\tessdata erwartet.
    tessdata_source = VENDOR / "tesseract" / "tessdata"
    if tessdata_source.is_dir():
        wanted = parse_languages(arguments.languages)
        target = VENDOR / "share" / "tessdata"
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        count = 0
        for item in sorted(tessdata_source.glob("*.traineddata")):
            if wanted is not None and item.stem not in wanted:
                continue
            shutil.copy2(item, target / item.name)
            count += 1

        # Neben den Sprachdaten braucht Tesseract seine Konfigurationsdateien.
        # Ohne den Ordner "configs" schlägt jeder Aufruf mit "hocr"/"txt" fehl.
        for folder in ("configs", "tessconfigs"):
            source_folder = tessdata_source / folder
            if source_folder.is_dir():
                shutil.copytree(source_folder, target / folder)
        font = tessdata_source / "pdf.ttf"
        if font.is_file():
            shutil.copy2(font, target / font.name)

        # Die Kopie unter tesseract\tessdata wäre doppelter Ballast.
        shutil.rmtree(tessdata_source, ignore_errors=True)
        print(f"Language files: {count}")

        if wanted is not None:
            fehlend = sorted(wanted - {f.stem for f in target.glob("*.traineddata")})
            if fehlend:
                print(
                    f"  note: not installed, skipped: {', '.join(fehlend)}\n"
                    f"        (add them via the Tesseract installer)",
                    file=sys.stderr,
                )

    total = sum(f.stat().st_size for f in VENDOR.rglob("*") if f.is_file())
    print(f"\nDone: {VENDOR}  ({total / 1024 / 1024:.0f} MB)")
    print("Now run:  pyinstaller packaging\\ocrmypdf_gui.spec --noconfirm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
