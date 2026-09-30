"""Verwaltung der Tesseract-Sprachdateien im Benutzerprofil.

Die mitgelieferten Sprachmodelle liegen im Programmpaket und sind dort
schreibgeschützt; unter macOS ist das Paket zusätzlich signiert. Zum
Nachinstallieren weiterer Sprachen braucht es deshalb einen eigenen Ordner im
Benutzerprofil. Beim ersten Download wird der Bestand aus dem Paket dorthin
kopiert, danach arbeitet die Anwendung ausschließlich mit diesem Ordner.

Die Modelle stammen aus den offiziellen Projekten von Tesseract:
  * tessdata_fast  schnell und klein, 1 bis 4 MB je Sprache
  * tessdata_best  genauer, dafür langsamer, 4 bis 15 MB je Sprache
"""

from __future__ import annotations

import json
import shutil
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ocrmypdf_gui.config import config_directory

# Name des Ordners im Benutzerprofil, der die Sprachdateien aufnimmt.
USER_TESSDATA_NAME = "tessdata"

# Dateien und Ordner, die Tesseract neben den Sprachmodellen benötigt.
REQUIRED_EXTRAS = ("configs", "tessconfigs", "pdf.ttf")

# Zeitlimit für Netzanfragen in Sekunden.
NETWORK_TIMEOUT = 30

# Blockgröße beim Herunterladen.
CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class Variant:
    """Eine Modellvariante von Tesseract."""

    key: str
    repository: str

    @property
    def label_key(self) -> str:
        """Schlüssel der Beschriftung in der Sprachtabelle."""
        return f"download.variant.{self.key}"

    def file_url(self, code: str) -> str:
        """Adresse der Sprachdatei innerhalb des Projekts."""
        return (
            f"https://raw.githubusercontent.com/tesseract-ocr/"
            f"{self.repository}/main/{code}.traineddata"
        )

    @property
    def index_url(self) -> str:
        """Adresse der Dateiliste des Projekts."""
        return f"https://api.github.com/repos/tesseract-ocr/{self.repository}/contents/"


VARIANTS: Dict[str, Variant] = {
    "fast": Variant("fast", "tessdata_fast"),
    "best": Variant("best", "tessdata_best"),
}
DEFAULT_VARIANT = "fast"


class DownloadError(Exception):
    """Ein Download ist fehlgeschlagen; die Meldung ist für Nutzer gedacht."""

    def __init__(self, message_key: str, detail: str = "") -> None:
        super().__init__(message_key)
        self.message_key = message_key
        self.detail = detail


# ----------------------------------------------------------------------
# Ordner im Benutzerprofil
# ----------------------------------------------------------------------
def user_tessdata_dir() -> Path:
    """Ordner im Benutzerprofil, der nachinstallierte Sprachen aufnimmt."""
    return config_directory() / USER_TESSDATA_NAME


def is_user_dir_active() -> bool:
    """True, wenn der Benutzerordner bereits eingerichtet ist und benutzt wird."""
    ordner = user_tessdata_dir()
    return ordner.is_dir() and any(ordner.glob("*.traineddata"))


def ensure_user_dir(source: Optional[Path]) -> Path:
    """Richtet den Benutzerordner ein und übernimmt den vorhandenen Bestand.

    ``source`` ist der Ordner, den Tesseract bisher verwendet hat. Sein Inhalt
    wird einmalig kopiert, damit die bereits vorhandenen Sprachen und die
    Konfigurationsdateien erhalten bleiben.
    """
    ziel = user_tessdata_dir()
    ziel.mkdir(parents=True, exist_ok=True)

    if source is None or not source.is_dir():
        return ziel

    for datei in source.glob("*.traineddata"):
        kopie = ziel / datei.name
        if not kopie.exists():
            shutil.copy2(datei, kopie)

    for name in REQUIRED_EXTRAS:
        herkunft = source / name
        kopie = ziel / name
        if kopie.exists() or not herkunft.exists():
            continue
        if herkunft.is_dir():
            shutil.copytree(herkunft, kopie)
        else:
            shutil.copy2(herkunft, kopie)

    return ziel


def installed_languages(folder: Optional[Path] = None) -> List[str]:
    """Sprachcodes, die in einem Ordner vorliegen."""
    ordner = folder or user_tessdata_dir()
    if not ordner.is_dir():
        return []
    return sorted(datei.stem for datei in ordner.glob("*.traineddata"))


def remove_language(code: str) -> bool:
    """Löscht eine nachinstallierte Sprachdatei aus dem Benutzerordner."""
    datei = user_tessdata_dir() / f"{code}.traineddata"
    try:
        datei.unlink()
        return True
    except OSError:
        return False


# ----------------------------------------------------------------------
# Netzzugriff
# ----------------------------------------------------------------------
def _certificate_bundle() -> Optional[str]:
    """Liefert die Datei mit den Stammzertifikaten, falls eine nötig ist.

    Das gebündelte Python greift nicht auf den Schlüsselbund des Systems zu.
    Ohne eine mitgelieferte Zertifikatsdatei scheitert jede HTTPS-Verbindung
    mit "certificate verify failed".
    """
    try:
        import certifi
    except ImportError:
        return None
    pfad = Path(certifi.where())
    return str(pfad) if pfad.is_file() else None


def _opener() -> urllib.request.OpenerDirector:
    """Baut einen HTTPS-Zugriff mit Zertifikatsprüfung und eigener Kennung."""
    bundle = _certificate_bundle()
    kontext = ssl.create_default_context(cafile=bundle) if bundle else ssl.create_default_context()
    handler = urllib.request.HTTPSHandler(context=kontext)
    opener = urllib.request.build_opener(handler)
    # GitHub weist Anfragen ohne Kennung teilweise ab.
    opener.addheaders = [("User-Agent", "OCRmyPDF-GUI")]
    return opener


def fetch_index(variant_key: str) -> Dict[str, int]:
    """Holt die Liste der verfügbaren Sprachen samt Dateigröße in Bytes."""
    variant = VARIANTS.get(variant_key) or VARIANTS[DEFAULT_VARIANT]
    try:
        with _opener().open(variant.index_url, timeout=NETWORK_TIMEOUT) as antwort:
            eintraege = json.loads(antwort.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as fehler:
        raise DownloadError("download.error.network", str(fehler)) from fehler

    ergebnis: Dict[str, int] = {}
    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            continue
        name = str(eintrag.get("name", ""))
        if name.endswith(".traineddata"):
            ergebnis[name[: -len(".traineddata")]] = int(eintrag.get("size", 0))
    if not ergebnis:
        raise DownloadError("download.error.network", "empty index")
    return ergebnis


def download_language(
    code: str,
    variant_key: str,
    target_dir: Path,
    progress: Optional[Callable[[int, int], None]] = None,
    cancelled: Optional[Callable[[], bool]] = None,
) -> Path:
    """Lädt eine Sprachdatei herunter und legt sie im Zielordner ab.

    Geschrieben wird zuerst in eine Nebendatei und erst am Ende umbenannt. So
    bleibt bei einem Abbruch keine halbe Datei zurück, die Tesseract später
    für ein gültiges Modell halten würde.
    """
    variant = VARIANTS.get(variant_key) or VARIANTS[DEFAULT_VARIANT]
    target_dir.mkdir(parents=True, exist_ok=True)
    ziel = target_dir / f"{code}.traineddata"
    zwischendatei = target_dir / f"{code}.traineddata.part"

    try:
        with _opener().open(variant.file_url(code), timeout=NETWORK_TIMEOUT) as antwort:
            gesamt = int(antwort.headers.get("Content-Length") or 0)
            geladen = 0
            with zwischendatei.open("wb") as ausgabe:
                while True:
                    if cancelled is not None and cancelled():
                        raise DownloadError("download.error.cancelled")
                    block = antwort.read(CHUNK_SIZE)
                    if not block:
                        break
                    ausgabe.write(block)
                    geladen += len(block)
                    if progress is not None:
                        progress(geladen, gesamt)
    except DownloadError:
        zwischendatei.unlink(missing_ok=True)
        raise
    except urllib.error.HTTPError as fehler:
        zwischendatei.unlink(missing_ok=True)
        schluessel = "download.error.notFound" if fehler.code == 404 else "download.error.network"
        raise DownloadError(schluessel, f"HTTP {fehler.code}") from fehler
    except (urllib.error.URLError, OSError, TimeoutError) as fehler:
        zwischendatei.unlink(missing_ok=True)
        raise DownloadError("download.error.network", str(fehler)) from fehler

    try:
        zwischendatei.replace(ziel)
    except OSError as fehler:
        zwischendatei.unlink(missing_ok=True)
        raise DownloadError("download.error.write", str(fehler)) from fehler
    return ziel
