"""Schreibt die SHA-256-Prüfsummen der Build-Ergebnisse nach ``dist/sha.txt``.

Damit lässt sich nach dem Herunterladen prüfen, ob eine Datei unverändert und
vollständig ist.

Aufruf (nach einem Build):
    python tools/make_checksums.py
    python tools/make_checksums.py --dist pfad/zum/ordner
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST = PROJECT_ROOT / "dist"
OUTPUT_NAME = "sha.txt"

# Endungen, die als einzelne Datei geprüft werden können.
FILE_SUFFIXES = (".dmg", ".exe", ".msi", ".zip", ".tar.gz", ".AppImage")
# Endungen, die in Wahrheit Verzeichnisse sind (macOS-Programmbündel).
BUNDLE_SUFFIXES = (".app",)

# Blockweise lesen, damit auch mehrere hundert MB nicht in den Speicher müssen.
CHUNK_SIZE = 1024 * 1024


def hash_file(path: Path) -> str:
    """Liefert den SHA-256-Wert einer einzelnen Datei."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_directory(root: Path) -> str:
    """Liefert einen reproduzierbaren SHA-256-Wert über ein ganzes Verzeichnis.

    Ein Programmbündel ist ein Ordner und hat daher keine Prüfsumme im üblichen
    Sinn. Berechnet wird deshalb ein Wert über alle enthaltenen Dateien: nach
    Pfad sortiert, und je Datei fließen der relative Pfad und der Inhalt ein.
    Die Sortierung macht das Ergebnis unabhängig von der Reihenfolge, in der das
    Dateisystem die Einträge liefert.
    """
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = item.relative_to(root).as_posix()
        if item.is_symlink():
            # Nicht dem Verweis folgen, sondern sein Ziel einrechnen.
            digest.update(f"L {relative} -> {item.readlink()}\n".encode("utf-8"))
        elif item.is_dir():
            digest.update(f"D {relative}\n".encode("utf-8"))
        elif item.is_file():
            digest.update(f"F {relative} {hash_file(item)}\n".encode("utf-8"))
    return digest.hexdigest()


def collect(dist: Path) -> Tuple[List[Tuple[Path, str]], List[Tuple[Path, str]]]:
    """Sammelt die Prüfsummen aller Build-Ergebnisse im Ordner ``dist``."""
    files: List[Tuple[Path, str]] = []
    bundles: List[Tuple[Path, str]] = []

    for item in sorted(dist.iterdir(), key=lambda p: p.name.lower()):
        if item.name == OUTPUT_NAME:
            continue
        if item.is_dir() and item.name.endswith(BUNDLE_SUFFIXES):
            bundles.append((item, hash_directory(item)))
        elif item.is_file() and item.name.endswith(FILE_SUFFIXES):
            files.append((item, hash_file(item)))
    return files, bundles


def human_size(path: Path) -> str:
    """Formatiert die Größe einer Datei oder eines Ordners in MB.

    Symbolische Verweise werden übersprungen. Ein Programmbündel enthält
    zahlreiche Verweise auf dieselben Dateien; würde man ihnen folgen, käme
    ungefähr das Doppelte der tatsächlich belegten Größe heraus.
    """
    if path.is_dir():
        total = sum(
            item.stat().st_size
            for item in path.rglob("*")
            if item.is_file() and not item.is_symlink()
        )
    else:
        total = path.stat().st_size
    return f"{total / 1024 / 1024:.0f} MB"


def build_report(dist: Path) -> str:
    """Baut den Inhalt der Datei ``sha.txt``."""
    files, bundles = collect(dist)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = [
        "# SHA-256-Prüfsummen der Build-Ergebnisse von OCRmyPDF GUI",
        f"# Erzeugt am {stamp}",
        "#",
        "# Prüfen unter macOS und Linux:",
        "#     shasum -a 256 -c sha.txt",
        "# Prüfen unter Windows (PowerShell):",
        "#     Get-FileHash .\\<Datei> -Algorithm SHA256",
        "#",
    ]

    # Hinweis: keine Leerzeilen einstreuen. "shasum -c" überliest zwar Zeilen,
    # die mit "#" beginnen, meldet eine leere Zeile aber als fehlerhaft.
    for path, value in files:
        lines.append(f"{value}  {path.name}")

    if bundles:
        lines += [
            "#",
            "# Die folgenden Einträge sind Programmbündel, also Verzeichnisse.",
            "# Sie lassen sich nicht mit 'shasum -c' prüfen und sind deshalb",
            "# auskommentiert. Der Wert ist der SHA-256 über alle enthaltenen",
            "# Dateien, nach Pfad sortiert, und wird von diesem Befehl erzeugt:",
            "#     python tools/make_checksums.py",
        ]
        for path, value in bundles:
            lines.append(f"# {value}  {path.name}")

    if not files and not bundles:
        lines += ["#", "# Keine Build-Ergebnisse gefunden."]

    lines += ["#", "# Größen:"]
    for path, _ in files + bundles:
        lines.append(f"#   {human_size(path):>8}  {path.name}")

    return "\n".join(lines) + "\n"


def main() -> int:
    """Erzeugt ``dist/sha.txt`` und gibt den Inhalt auf der Konsole aus."""
    parser = argparse.ArgumentParser(description="Write SHA-256 checksums for build artifacts.")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST,
                        help="Ordner mit den Build-Ergebnissen (Standard: dist/)")
    arguments = parser.parse_args()

    dist: Path = arguments.dist
    if not dist.is_dir():
        print(f"ERROR: '{dist}' does not exist. Build the application first.", file=sys.stderr)
        return 1

    report = build_report(dist)
    target = dist / OUTPUT_NAME
    target.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"\nwritten: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
