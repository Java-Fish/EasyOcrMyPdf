"""Auffinden der externen Programme (Tesseract, Ghostscript, OCRmyPDF).

Die Suche läuft in drei Stufen:

1. mitgelieferte Binaries im Ordner ``vendor/`` des Pakets,
2. der ``PATH`` des Systems,
3. die üblichen Installationsorte je Betriebssystem.

Stufe 3 ist wichtig, weil eine per Doppelklick gestartete macOS-App einen
stark reduzierten ``PATH`` erbt und Homebrew-Pfade dort nicht enthalten sind.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# Verhindert, dass unter Windows für jeden Aufruf ein Konsolenfenster aufblitzt.
_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

# Suchpfade außerhalb von PATH, nach Wahrscheinlichkeit sortiert.
_EXTRA_SEARCH_PATHS: Dict[str, Sequence[str]] = {
    "darwin": (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/local/bin",
        "/usr/bin",
    ),
    "win32": (
        r"C:\Program Files\Tesseract-OCR",
        r"C:\Program Files (x86)\Tesseract-OCR",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR"),
        os.path.expandvars(r"%PROGRAMFILES%\gs"),
    ),
    "linux": ("/usr/bin", "/usr/local/bin", "/snap/bin"),
}

# Mehrere mögliche Programmnamen je Werkzeug (Windows nutzt andere Namen).
_EXECUTABLE_NAMES: Dict[str, Sequence[str]] = {
    "tesseract": ("tesseract.exe",) if IS_WINDOWS else ("tesseract",),
    "ghostscript": ("gswin64c.exe", "gswin32c.exe") if IS_WINDOWS else ("gs",),
    # Optional: nur für die höheren Stufen der Größenoptimierung nötig.
    "pngquant": ("pngquant.exe",) if IS_WINDOWS else ("pngquant",),
    "jbig2": ("jbig2.exe",) if IS_WINDOWS else ("jbig2",),
}

# Welche Zusatzprogramme eine Optimierungsstufe voraussetzt.
# Die Stufen 0 und 1 kommen ohne aus; OCRmyPDF bricht bei fehlenden
# Programmen ab, deshalb sperrt die Oberfläche die betroffenen Stufen.
OPTIMIZE_REQUIREMENTS = {
    0: (),
    1: (),
    2: ("pngquant",),
    3: ("pngquant", "jbig2"),
}


def is_frozen() -> bool:
    """True, wenn die Anwendung als gebündeltes Programm läuft (PyInstaller)."""
    return getattr(sys, "frozen", False)


def resource_root() -> Path:
    """Wurzelverzeichnis für mitgelieferte Dateien."""
    if is_frozen():
        # PyInstaller entpackt Zusatzdateien nach sys._MEIPASS.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def vendor_root() -> Path:
    """Ordner mit den mitgelieferten Binaries für das aktuelle Betriebssystem."""
    platform_dir = "windows" if IS_WINDOWS else ("macos" if IS_MACOS else "linux")
    return resource_root() / "vendor" / platform_dir


def _candidate_paths(tool: str) -> List[Path]:
    """Alle Pfade, an denen ein Werkzeug liegen könnte - in Suchreihenfolge."""
    names = _EXECUTABLE_NAMES[tool]
    candidates: List[Path] = []

    # Stufe 1: mitgelieferte Binaries.
    vendor_bin = vendor_root() / "bin"
    for name in names:
        candidates.append(vendor_bin / name)
    # Windows-Ghostscript bringt eine eigene Ordnerstruktur mit.
    if IS_WINDOWS:
        for name in names:
            candidates.append(vendor_root() / "gs" / "bin" / name)
            candidates.append(vendor_root() / "tesseract" / name)

    # Stufe 2: PATH.
    for name in names:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    # Stufe 3: übliche Installationsorte.
    for directory in _EXTRA_SEARCH_PATHS.get(sys.platform, ()):
        base = Path(directory)
        for name in names:
            candidates.append(base / name)
            # Ghostscript installiert sich unter Windows versioniert:
            # C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe
            if IS_WINDOWS and base.name.lower() == "gs" and base.is_dir():
                for version_dir in sorted(base.iterdir(), reverse=True):
                    candidates.append(version_dir / "bin" / name)
    return candidates


def _is_usable(path: Path) -> bool:
    """Prüft, ob der Pfad auf eine ausführbare Datei zeigt."""
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


@lru_cache(maxsize=None)
def find_tool(tool: str) -> Optional[Path]:
    """Sucht ein Werkzeug und merkt sich das Ergebnis."""
    for candidate in _candidate_paths(tool):
        if _is_usable(candidate):
            # Bewusst ohne resolve(): ein aufgelöster Homebrew-Symlink zeigt in
            # den Cellar, wo neben dem Programm nur die Basissprachen liegen.
            return Path(os.path.abspath(candidate))
    return None


def clear_cache() -> None:
    """Verwirft die gemerkten Fundorte - nötig nach einer Nachinstallation."""
    find_tool.cache_clear()
    tessdata_dir.cache_clear()
    effective_tessdata_dir.cache_clear()
    tool_version.cache_clear()


@lru_cache(maxsize=None)
def tessdata_dir() -> Optional[Path]:
    """Sprachordner, den wir Tesseract aktiv vorgeben *müssen*.

    Gibt ``None`` zurück, wenn Tesseract seinen eigenen, einkompilierten
    Standardordner verwenden soll - das ist bei Systeminstallationen der
    zuverlässigste Weg und vermeidet, dass wir versehentlich einen Ordner mit
    weniger Sprachpaketen erzwingen.
    """
    # Hat der Nutzer Sprachen nachinstalliert, liegt der vollständige Bestand
    # im Benutzerprofil; der Ordner im Programmpaket ist dann veraltet.
    from ocrmypdf_gui import tessdata

    if tessdata.is_user_dir_active():
        return tessdata.user_tessdata_dir()

    bundled = vendor_root() / "share" / "tessdata"
    if bundled.is_dir():
        return bundled

    env_value = os.environ.get("TESSDATA_PREFIX")
    if env_value:
        env_path = Path(env_value)
        # Tesseract akzeptiert sowohl .../tessdata als auch dessen Elternordner.
        for candidate in (env_path, env_path / "tessdata"):
            if candidate.is_dir():
                return candidate
    return None


@lru_cache(maxsize=1)
def effective_tessdata_dir() -> Optional[Path]:
    """Der Ordner, den Tesseract tatsächlich benutzt - nur zur Anzeige.

    Tesseract nennt ihn in der Kopfzeile von ``--list-langs``.
    """
    tesseract = find_tool("tesseract")
    if tesseract is None:
        return None
    for line in run_capture([str(tesseract), "--list-langs"]).splitlines():
        if '"' in line:
            _, _, rest = line.partition('"')
            path_text = rest.rpartition('"')[0].strip()
            if path_text:
                return Path(path_text)
    return None


def process_environment() -> Dict[str, str]:
    """Umgebung für Unterprozesse: mitgelieferte Pfade haben Vorrang."""
    env = os.environ.copy()

    extra_paths: List[str] = []
    vendor_bin = vendor_root() / "bin"
    if vendor_bin.is_dir():
        extra_paths.append(str(vendor_bin))
    for tool in ("tesseract", "ghostscript", "pngquant", "jbig2"):
        location = find_tool(tool)
        if location is not None:
            extra_paths.append(str(location.parent))

    existing = env.get("PATH", "")
    # Reihenfolge beibehalten, Duplikate entfernen.
    merged: List[str] = []
    for entry in extra_paths + existing.split(os.pathsep):
        if entry and entry not in merged:
            merged.append(entry)
    env["PATH"] = os.pathsep.join(merged)

    tessdata = tessdata_dir()
    if tessdata is not None:
        env["TESSDATA_PREFIX"] = str(tessdata)

    # OCRmyPDF findet Ghostscript sonst nur über PATH; ein expliziter Hinweis
    # macht mitgelieferte Binaries zuverlässig auffindbar.
    ghostscript = find_tool("ghostscript")
    if ghostscript is not None:
        env.setdefault("OCRMYPDF_GS", str(ghostscript))
    tesseract = find_tool("tesseract")
    if tesseract is not None:
        env.setdefault("OCRMYPDF_TESSERACT", str(tesseract))

    return env


def ocrmypdf_command() -> Optional[List[str]]:
    """Liefert den Befehl, mit dem OCRmyPDF gestartet wird.

    Im gebündelten Programm ruft sich die Anwendung selbst mit dem Schalter
    ``--ocr-worker`` auf; dadurch braucht der Nutzer keine separate Installation.
    """
    if is_frozen():
        return [sys.executable, "--ocr-worker"]
    if _ocrmypdf_importable():
        return [sys.executable, "-m", "ocrmypdf"]
    external = shutil.which("ocrmypdf")
    if external:
        return [external]
    return None


@lru_cache(maxsize=1)
def _ocrmypdf_importable() -> bool:
    """Prüft, ob OCRmyPDF als Python-Paket verfügbar ist."""
    import importlib.util

    try:
        return importlib.util.find_spec("ocrmypdf") is not None
    except (ImportError, ValueError):
        return False


def run_capture(command: Sequence[str], timeout: float = 20.0) -> str:
    """Führt ein Kommando aus und liefert dessen Ausgabe (leer bei Fehler)."""
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=process_environment(),
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or "") + (result.stderr or "")


@lru_cache(maxsize=None)
def tool_version(tool: str) -> str:
    """Versionszeile eines Werkzeugs, z. B. für den Einrichtungsdialog."""
    if tool == "ocrmypdf":
        command = ocrmypdf_command()
        if command is None:
            return ""
        output = run_capture([*command, "--version"])
    else:
        location = find_tool(tool)
        if location is None:
            return ""
        output = run_capture([str(location), "--version"])
    for line in output.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def available_languages() -> List[str]:
    """Liest die installierten Sprachpakete aus ``tesseract --list-langs``."""
    tesseract = find_tool("tesseract")
    if tesseract is None:
        return []
    output = run_capture([str(tesseract), "--list-langs"])
    languages: List[str] = []
    for line in output.splitlines():
        line = line.strip()
        # Die erste Zeile ist eine Überschrift ("List of available languages ...").
        if not line or " " in line or ":" in line:
            continue
        languages.append(line)
    return sorted(set(languages))


@dataclass(frozen=True)
class ToolStatus:
    """Ergebnis der Prüfung eines einzelnen Werkzeugs."""

    key: str
    label: str
    path: Optional[Path]
    version: str
    required: bool = True

    @property
    def available(self) -> bool:
        """True, wenn das Werkzeug gefunden wurde."""
        return self.path is not None or bool(self.version)


@dataclass(frozen=True)
class DependencyReport:
    """Gesamtergebnis der Abhängigkeitsprüfung."""

    tools: List[ToolStatus] = field(default_factory=list)

    @property
    def missing(self) -> List[ToolStatus]:
        """Alle zwingend benötigten Werkzeuge, die fehlen."""
        return [tool for tool in self.tools if tool.required and not tool.available]

    @property
    def ok(self) -> bool:
        """True, wenn kein zwingend benötigtes Werkzeug fehlt."""
        return not self.missing


def check_dependencies() -> DependencyReport:
    """Prüft alle benötigten Werkzeuge in einem Durchgang."""
    clear_cache()
    _ocrmypdf_importable.cache_clear()

    ocr_command = ocrmypdf_command()
    tools = [
        ToolStatus(
            key="ocrmypdf",
            label="OCRmyPDF",
            path=Path(ocr_command[0]) if ocr_command else None,
            version=tool_version("ocrmypdf"),
        ),
        ToolStatus(
            key="tesseract",
            label="Tesseract OCR",
            path=find_tool("tesseract"),
            version=tool_version("tesseract"),
        ),
        ToolStatus(
            key="ghostscript",
            label="Ghostscript",
            path=find_tool("ghostscript"),
            version=tool_version("ghostscript"),
        ),
    ]
    return DependencyReport(tools=tools)


def missing_optimize_tools(level: int) -> List[str]:
    """Zusatzprogramme, die für diese Optimierungsstufe fehlen."""
    return [
        tool
        for tool in OPTIMIZE_REQUIREMENTS.get(level, ())
        if find_tool(tool) is None
    ]


def optimize_level_available(level: int) -> bool:
    """Lässt sich diese Optimierungsstufe gefahrlos auswählen?"""
    return not missing_optimize_tools(level)
