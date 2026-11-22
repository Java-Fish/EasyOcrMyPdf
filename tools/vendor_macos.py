"""Kopiert Tesseract und Ghostscript samt Bibliotheken nach ``vendor/macos``.

Danach bringt die gebaute .app beide Programme selbst mit; der Nutzer muss
nichts über Homebrew nachinstallieren.

Aufruf (nach ``brew install tesseract tesseract-lang ghostscript``):
    python tools/vendor_macos.py                        # Deutsch und Englisch
    python tools/vendor_macos.py --languages european   # 26 europäische Sprachen
    python tools/vendor_macos.py --languages all        # alle installierten
    python tools/vendor_macos.py --languages deu,eng,fra

Was passiert: Die Programme werden kopiert, alle von ihnen benötigten
Bibliotheken aus /opt/homebrew bzw. /usr/local hinterher, und anschließend
werden die Suchpfade in den Dateien so umgeschrieben, dass sie sich
gegenseitig innerhalb des Pakets finden (``@rpath``/``@loader_path``).
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
VENDOR = PROJECT_ROOT / "vendor" / "macos"

# Nur Bibliotheken aus diesen Präfixen werden mitgenommen. Alles unter
# /usr/lib und /System gehört zu macOS selbst und ist überall vorhanden.
RELOCATABLE_PREFIXES = ("/opt/homebrew", "/usr/local", "/opt/local")

TOOLS = ("tesseract", "gs")

# Nur für die höheren Optimierungsstufen nötig. Fehlen sie, wird ohne sie
# gebaut und die Oberfläche sperrt die betroffenen Stufen.
OPTIONAL_TOOLS = ("pngquant", "jbig2")

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

_OTOOL_LINE = re.compile(r"^\s+(\S+)\s+\(compatibility")


def run(command: List[str]) -> str:
    """Führt ein Kommando aus und bricht bei einem Fehler ab."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)}\n{result.stderr.strip()}")
    return result.stdout


def dependencies_of(binary: Path) -> List[str]:
    """Listet die dynamischen Bibliotheken einer Datei auf."""
    output = run(["otool", "-L", str(binary)])
    found: List[str] = []
    for line in output.splitlines()[1:]:
        match = _OTOOL_LINE.match(line)
        if match:
            found.append(match.group(1))
    return found


def rpaths_of(binary: Path) -> List[str]:
    """Liest die eingebauten Suchpfade (LC_RPATH) einer Datei."""
    output = run(["otool", "-l", str(binary)])
    paths: List[str] = []
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if "cmd LC_RPATH" in line:
            for follow in lines[index : index + 5]:
                match = re.search(r"path (.+?) \(offset", follow)
                if match:
                    paths.append(match.group(1))
                    break
    return paths


def resolve_reference(reference: str, origin: Path) -> Path | None:
    """Findet die Datei hinter einem Bibliotheksverweis.

    Homebrew mischt absolute Pfade und ``@rpath``-Verweise. Systembibliotheken
    unter /usr/lib und /System werden bewusst nicht mitgeliefert, denn sie sind auf
    jedem Mac vorhanden.
    """
    if reference.startswith(("@rpath/", "@loader_path/", "@executable_path/")):
        name = Path(reference).name
        candidates = [origin.parent / name]
        for prefix in RELOCATABLE_PREFIXES:
            candidates.append(Path(prefix) / "lib" / name)
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return None
    if reference.startswith(RELOCATABLE_PREFIXES):
        path = Path(reference)
        return path.resolve() if path.exists() else None
    return None


def resolve(path: str) -> Path:
    """Löst Homebrew-Symlinks auf die tatsächliche Datei auf."""
    return Path(path).resolve()


def collect_libraries(binaries: Iterable[Path]) -> Set[Path]:
    """Sammelt rekursiv alle mitzuliefernden Bibliotheken."""
    pending = list(binaries)
    seen: Set[Path] = set()
    libraries: Set[Path] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for reference in dependencies_of(current):
            real = resolve_reference(reference, current)
            if real is None or real in libraries or not real.is_file():
                continue
            libraries.add(real)
            pending.append(real)
    return libraries


def ad_hoc_sign(path: Path) -> None:
    """Signiert eine geänderte Datei neu.

    Auf Apple Silicon verlieren Dateien durch ``install_name_tool`` ihre
    Signatur und lassen sich danach nicht mehr starten.
    """
    subprocess.run(
        ["codesign", "--force", "--sign", "-", "--timestamp=none", str(path)],
        capture_output=True,
        text=True,
    )


def rewrite_paths(target: Path, library_names: Set[str], is_executable: bool) -> None:
    """Schreibt die Bibliotheksverweise einer Datei auf das Paket um."""
    commands: List[str] = []

    if not is_executable:
        commands += ["-id", f"@rpath/{target.name}"]

    for reference in dependencies_of(target):
        real = resolve_reference(reference, target)
        if real is None:
            continue
        name = real.name
        if name in library_names and reference != f"@rpath/{name}":
            commands += ["-change", reference, f"@rpath/{name}"]

    if commands:
        run(["install_name_tool", *commands, str(target)])

    # Alte Suchpfade nach /opt/homebrew entfernen: sonst zieht die Datei im
    # Zweifel die Systemkopie statt der mitgelieferten.
    for old_rpath in rpaths_of(target):
        if old_rpath.startswith(RELOCATABLE_PREFIXES):
            subprocess.run(
                ["install_name_tool", "-delete_rpath", old_rpath, str(target)],
                capture_output=True,
                text=True,
            )

    # Neuen Suchpfad setzen: Programme liegen in bin/, Bibliotheken in lib/.
    rpath = "@executable_path/../lib" if is_executable else "@loader_path"
    subprocess.run(
        ["install_name_tool", "-add_rpath", rpath, str(target)],
        capture_output=True,
        text=True,
    )
    ad_hoc_sign(target)


def copy_tessdata(destination: Path, wanted: Optional[Set[str]]) -> int:
    """Kopiert die Sprachdateien von Tesseract.

    ``wanted`` schränkt auf bestimmte Sprachcodes ein; ``None`` nimmt alle.
    """
    candidates = [
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/local/share/tessdata"),
        Path("/opt/local/share/tessdata"),
    ]
    source = next((path for path in candidates if path.is_dir()), None)
    if source is None:
        print("WARNING: no tessdata folder found - languages will be missing", file=sys.stderr)
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in sorted(source.iterdir()):
        if not item.is_file() or item.suffix != ".traineddata":
            continue
        if wanted is not None and item.stem not in wanted:
            continue
        shutil.copy2(item, destination / item.name)
        count += 1

    # Neben den Sprachdaten braucht Tesseract seine Konfigurationsdateien.
    # Ohne den Ordner "configs" schlägt jeder Aufruf mit "hocr"/"txt" fehl.
    for folder in ("configs", "tessconfigs"):
        source_folder = source / folder
        if source_folder.is_dir():
            target_folder = destination / folder
            if target_folder.exists():
                shutil.rmtree(target_folder)
            shutil.copytree(source_folder, target_folder)

    # Die Schrift wird für die PDF-Ausgabe von Tesseract benötigt.
    font = source / "pdf.ttf"
    if font.is_file():
        shutil.copy2(font, destination / font.name)

    if wanted is not None:
        missing = sorted(wanted - {f.stem for f in destination.glob("*.traineddata")})
        if missing:
            print(
                f"  note: not installed, skipped: {', '.join(missing)}\n"
                f"        (install them with: brew install tesseract-lang)",
                file=sys.stderr,
            )
    return count


def parse_languages(value: str) -> Optional[Set[str]]:
    """Wertet die Option ``--languages`` aus. ``None`` bedeutet: alle."""
    chosen = value.strip().lower()
    if chosen == "all":
        return None
    if chosen == "standard":
        return set(STANDARD_LANGUAGES)
    if chosen == "european":
        return set(EUROPEAN_LANGUAGES)
    return {code.strip() for code in value.split(",") if code.strip()}


def main() -> int:
    """Kopiert Programme und Bibliotheken nach vendor/macos."""
    if sys.platform != "darwin":
        print("This script only runs on macOS.", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Bundle Tesseract and Ghostscript.")
    parser.add_argument(
        "--languages",
        default="standard",
        help='"standard" (Vorgabe: deu, eng, osd), "european", "all" oder eine Liste wie "deu,eng,fra"',
    )
    arguments = parser.parse_args()
    wanted = parse_languages(arguments.languages)

    binaries: List[Path] = []
    for tool in TOOLS:
        location = shutil.which(tool)
        if location is None:
            print(
                f"ERROR: '{tool}' not found. Install it first:\n"
                f"    brew install tesseract tesseract-lang ghostscript",
                file=sys.stderr,
            )
            return 1
        binaries.append(resolve(location))

    for tool in OPTIONAL_TOOLS:
        location = shutil.which(tool)
        if location is None:
            print(
                f"note: optional tool '{tool}' not found - the higher "
                f"optimisation levels will be disabled in the app.\n"
                f"      install it with: brew install pngquant jbig2enc"
            )
            continue
        binaries.append(resolve(location))

    bin_dir = VENDOR / "bin"
    lib_dir = VENDOR / "lib"
    shutil.rmtree(VENDOR, ignore_errors=True)
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)

    print("Collecting libraries ...")
    libraries = collect_libraries(binaries)
    library_names = {library.name for library in libraries}
    print(f"  {len(libraries)} libraries")

    copied_binaries: List[Path] = []
    for source in binaries:
        target = bin_dir / source.name
        shutil.copy2(source, target)
        target.chmod(0o755)
        copied_binaries.append(target)

    copied_libraries: List[Path] = []
    for source in libraries:
        target = lib_dir / source.name
        shutil.copy2(source, target)
        target.chmod(0o755)
        copied_libraries.append(target)

    print("Rewriting library paths ...")
    for target in copied_libraries:
        rewrite_paths(target, library_names, is_executable=False)
    for target in copied_binaries:
        rewrite_paths(target, library_names, is_executable=True)

    print("Copying language data ...")
    count = copy_tessdata(VENDOR / "share" / "tessdata", wanted)
    print(f"  {count} language files")

    size = sum(f.stat().st_size for f in VENDOR.rglob("*") if f.is_file())
    print(f"\nDone: {VENDOR}  ({size / 1024 / 1024:.0f} MB)")
    print("Now run:  pyinstaller packaging/ocrmypdf_gui.spec --noconfirm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
