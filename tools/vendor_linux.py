"""Kopiert Tesseract und Ghostscript samt Bibliotheken nach ``vendor/linux``.

Danach bringt das gebaute Programm beide Werkzeuge selbst mit. Die Suchpfade
der kopierten Dateien werden mit ``patchelf`` auf ``$ORIGIN`` umgestellt, damit
sie sich innerhalb des Pakets gegenseitig finden.

Voraussetzungen:
    sudo apt install tesseract-ocr tesseract-ocr-deu ghostscript patchelf
    sudo apt install pngquant                  # optional, für starke Optimierung

Aufruf:
    python tools/vendor_linux.py                        # Deutsch und Englisch
    python tools/vendor_linux.py --languages european   # 26 europäische Sprachen
    python tools/vendor_linux.py --languages all        # alle installierten
    python tools/vendor_linux.py --languages deu,eng,fra

Ein Hinweis zur Verträglichkeit: Mitgelieferte Bibliotheken sind gegen die
glibc des Build-Rechners gebaut. Ein auf einer neuen Distribution erzeugtes
Paket läuft deshalb nicht zwangsläufig auf einer älteren. Wer breit verteilen
möchte, baut auf einer möglichst alten Distribution oder verzichtet auf das
Mitliefern und überlässt die Installation der Paketverwaltung.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR = PROJECT_ROOT / "vendor" / "linux"

# Werkzeuge, ohne die die Anwendung nicht arbeiten kann.
TOOLS = ("tesseract", "gs")

# Nur für die höheren Optimierungsstufen nötig. Fehlen sie, wird ohne sie
# gebaut und die Oberfläche sperrt die betroffenen Stufen.
OPTIONAL_TOOLS = ("pngquant", "jbig2")

# Bibliotheken aus diesen Verzeichnissen gehören zum Betriebssystem und werden
# bewusst nicht mitgeliefert. Sie mitzunehmen führt häufiger zu Problemen, als
# es löst, weil sie eng mit Kernel und glibc verzahnt sind.
SYSTEM_PREFIXES = (
    "/lib/ld-", "/lib64/ld-",
    "linux-vdso", "ld-linux",
)
SYSTEM_LIBRARIES = {
    "libc.so.6", "libm.so.6", "libpthread.so.0", "libdl.so.2", "librt.so.1",
    "libresolv.so.2", "libgcc_s.so.1", "libstdc++.so.6", "ld-linux-x86-64.so.2",
    "libGL.so.1", "libX11.so.6", "libxcb.so.1",
}

# Sprachpakete, die in die fertigen Pakete eingebettet werden.
#
# "standard" ist die Voreinstellung und enthält nur Deutsch und Englisch. Das
# hält das Paket klein genug, um es als Release-Artefakt hochladen zu können
# (Codeberg nimmt höchstens 100 MB je Datei). Alle übrigen Sprachen lassen sich
# in der Anwendung nachladen.
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

# Übliche Orte der Sprachdateien bei den verbreiteten Distributionen.
TESSDATA_CANDIDATES = (
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tesseract-ocr/tessdata",
    "/usr/share/tessdata",
    "/usr/local/share/tessdata",
)

_LDD_LINE = re.compile(r"=>\s+(\S+)\s+\(0x")


def run(command: List[str]) -> str:
    """Führt ein Kommando aus und bricht bei einem Fehler ab."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)}\n{result.stderr.strip()}")
    return result.stdout


def have_patchelf() -> bool:
    """Prüft, ob ``patchelf`` zur Verfügung steht."""
    return shutil.which("patchelf") is not None


def is_system_library(path: str) -> bool:
    """True, wenn die Bibliothek zum Betriebssystem gehört und bleiben soll."""
    if any(marker in path for marker in SYSTEM_PREFIXES):
        return True
    return Path(path).name in SYSTEM_LIBRARIES


def dependencies_of(binary: Path) -> List[Path]:
    """Listet die dynamischen Bibliotheken einer Datei auf."""
    try:
        ausgabe = run(["ldd", str(binary)])
    except RuntimeError:
        return []
    gefunden: List[Path] = []
    for zeile in ausgabe.splitlines():
        treffer = _LDD_LINE.search(zeile)
        if not treffer:
            continue
        pfad = treffer.group(1)
        if pfad and not is_system_library(pfad) and Path(pfad).is_file():
            gefunden.append(Path(pfad).resolve())
    return gefunden


def collect_libraries(binaries: Iterable[Path]) -> Set[Path]:
    """Sammelt rekursiv alle mitzuliefernden Bibliotheken."""
    offen = list(binaries)
    gesehen: Set[Path] = set()
    bibliotheken: Set[Path] = set()
    while offen:
        aktuell = offen.pop()
        if aktuell in gesehen:
            continue
        gesehen.add(aktuell)
        for bibliothek in dependencies_of(aktuell):
            if bibliothek in bibliotheken:
                continue
            bibliotheken.add(bibliothek)
            offen.append(bibliothek)
    return bibliotheken


def set_rpath(target: Path, rpath: str) -> None:
    """Setzt den Suchpfad einer Datei auf einen Ort innerhalb des Pakets."""
    subprocess.run(["patchelf", "--set-rpath", rpath, str(target)],
                   capture_output=True, text=True)


def copy_tessdata(destination: Path, wanted: Optional[Set[str]]) -> int:
    """Kopiert die Sprachdateien von Tesseract.

    ``wanted`` schränkt auf bestimmte Sprachcodes ein; ``None`` nimmt alle.
    """
    quelle = next((Path(p) for p in TESSDATA_CANDIDATES if Path(p).is_dir()), None)
    if quelle is None:
        print("WARNING: no tessdata folder found - languages will be missing",
              file=sys.stderr)
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    anzahl = 0
    for eintrag in sorted(quelle.iterdir()):
        if not eintrag.is_file() or eintrag.suffix != ".traineddata":
            continue
        if wanted is not None and eintrag.stem not in wanted:
            continue
        shutil.copy2(eintrag, destination / eintrag.name)
        anzahl += 1

    # Neben den Sprachdaten braucht Tesseract seine Konfigurationsdateien.
    # Ohne den Ordner "configs" schlägt jeder Aufruf mit "hocr"/"txt" fehl.
    for ordner in ("configs", "tessconfigs"):
        quellordner = quelle / ordner
        if quellordner.is_dir():
            zielordner = destination / ordner
            if zielordner.exists():
                shutil.rmtree(zielordner)
            shutil.copytree(quellordner, zielordner)

    # Die Schrift wird für die PDF-Ausgabe von Tesseract benötigt.
    schrift = quelle / "pdf.ttf"
    if schrift.is_file():
        shutil.copy2(schrift, destination / schrift.name)

    if wanted is not None:
        fehlend = sorted(wanted - {f.stem for f in destination.glob("*.traineddata")})
        if fehlend:
            print(
                f"  note: not installed, skipped: {', '.join(fehlend)}\n"
                f"        (install them with: sudo apt install "
                f"{' '.join('tesseract-ocr-' + c for c in fehlend if c != 'osd')})",
                file=sys.stderr,
            )
    return anzahl


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
    """Kopiert Programme und Bibliotheken nach vendor/linux."""
    if sys.platform.startswith("win") or sys.platform == "darwin":
        print("This script only runs on Linux.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Bundle Tesseract and Ghostscript.")
    parser.add_argument(
        "--languages",
        default="standard",
        help='"standard" (Vorgabe: deu, eng, osd), "european", "all" '
             'oder eine Liste wie "deu,eng,fra"',
    )
    arguments = parser.parse_args()
    wanted = parse_languages(arguments.languages)

    if not have_patchelf():
        print(
            "ERROR: 'patchelf' not found. Install it first:\n"
            "    sudo apt install patchelf",
            file=sys.stderr,
        )
        return 1

    binaries: List[Path] = []
    for tool in TOOLS:
        ort = shutil.which(tool)
        if ort is None:
            print(
                f"ERROR: '{tool}' not found. Install it first:\n"
                f"    sudo apt install tesseract-ocr tesseract-ocr-deu ghostscript",
                file=sys.stderr,
            )
            return 1
        binaries.append(Path(ort).resolve())

    for tool in OPTIONAL_TOOLS:
        ort = shutil.which(tool)
        if ort is None:
            print(
                f"note: optional tool '{tool}' not found - the higher "
                f"optimisation levels will be disabled in the app."
            )
            continue
        binaries.append(Path(ort).resolve())

    bin_dir = VENDOR / "bin"
    lib_dir = VENDOR / "lib"
    shutil.rmtree(VENDOR, ignore_errors=True)
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)

    print("Collecting libraries ...")
    bibliotheken = collect_libraries(binaries)
    print(f"  {len(bibliotheken)} libraries")

    kopierte_programme: List[Path] = []
    for quelle in binaries:
        ziel = bin_dir / quelle.name
        shutil.copy2(quelle, ziel)
        ziel.chmod(0o755)
        kopierte_programme.append(ziel)

    kopierte_bibliotheken: List[Path] = []
    for quelle in bibliotheken:
        ziel = lib_dir / quelle.name
        shutil.copy2(quelle, ziel)
        ziel.chmod(0o755)
        kopierte_bibliotheken.append(ziel)

    print("Rewriting library paths ...")
    for ziel in kopierte_bibliotheken:
        set_rpath(ziel, "$ORIGIN")
    for ziel in kopierte_programme:
        set_rpath(ziel, "$ORIGIN/../lib")

    print("Copying language data ...")
    anzahl = copy_tessdata(VENDOR / "share" / "tessdata", wanted)
    print(f"  {anzahl} language files")

    groesse = sum(f.stat().st_size for f in VENDOR.rglob("*") if f.is_file())
    print(f"\nDone: {VENDOR}  ({groesse / 1024 / 1024:.0f} MB)")
    print("Now run:  ./packaging/build_linux.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
