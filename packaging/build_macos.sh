#!/usr/bin/env bash
# Baut "OCRmyPDF GUI.app" und optional ein DMG zum Weitergeben.
#
#   ./packaging/build_macos.sh            # nur die .app
#   ./packaging/build_macos.sh --dmg      # zusätzlich ein DMG
#   ./packaging/build_macos.sh --vendor   # Tesseract/Ghostscript mitliefern
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="OCRmyPDF GUI"
DMG_NAME="OCRmyPDF-GUI.dmg"
VENV=".venv"
MAKE_DMG=0
DO_VENDOR=0

for argument in "$@"; do
  case "$argument" in
    --dmg) MAKE_DMG=1 ;;
    --vendor) DO_VENDOR=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $argument" >&2; exit 1 ;;
  esac
done

# --- Virtuelle Umgebung vorbereiten ---------------------------------------
if [ ! -d "$VENV" ]; then
  echo "==> Creating virtual environment"
  python3 -m venv "$VENV"
fi
PYTHON="$VENV/bin/python"

echo "==> Installing dependencies"
"$PYTHON" -m pip install --quiet --upgrade pip
"$PYTHON" -m pip install --quiet -r requirements.txt -r requirements-build.txt

# --- Symbole erzeugen ------------------------------------------------------
echo "==> Generating icons"
"$PYTHON" tools/make_icons.py

# --- Optional: Tesseract und Ghostscript mitliefern ------------------------
if [ "$DO_VENDOR" -eq 1 ]; then
  echo "==> Bundling Tesseract and Ghostscript"
  "$PYTHON" tools/vendor_macos.py
else
  # Ohne diese Variable bände die Spec einen aus einem früheren Lauf
  # übriggebliebenen vendor-Ordner stillschweigend mit ein.
  export OCRMYPDF_GUI_NO_VENDOR=1
fi

# --- Bauen -----------------------------------------------------------------
echo "==> Building the application"
rm -rf build "dist/$APP_NAME.app" "dist/$APP_NAME"
"$PYTHON" -m PyInstaller packaging/ocrmypdf_gui.spec --noconfirm --distpath dist --workpath build

if [ ! -d "dist/$APP_NAME.app" ]; then
  echo "Build failed: dist/$APP_NAME.app was not created" >&2
  exit 1
fi

# Ad-hoc-Signatur: ohne sie verweigert macOS auf Apple Silicon den Start.
echo "==> Signing (ad-hoc)"
codesign --force --deep --sign - "dist/$APP_NAME.app" 2>/dev/null || \
  echo "    Note: ad-hoc signing reported a problem - the app usually still runs."

# --- Optional: DMG ---------------------------------------------------------
if [ "$MAKE_DMG" -eq 1 ]; then
  echo "==> Creating DMG"
  DMG_DIR="$(mktemp -d)"
  cp -R "dist/$APP_NAME.app" "$DMG_DIR/"
  ln -s /Applications "$DMG_DIR/Applications"
  # Dateiname ohne Leerzeichen: das erspart beim Herunterladen "%20" in der URL.
  rm -f "dist/$DMG_NAME"
  # ULMO komprimiert mit LZMA und liefert rund ein Viertel kleinere Dateien als
  # das übliche UDZO. Zum Einbinden wird macOS 10.15 oder neuer benötigt, was
  # ohnehin Voraussetzung für diese Anwendung ist.
  hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_DIR" \
    -ov -format ULMO "dist/$DMG_NAME" >/dev/null
  rm -rf "$DMG_DIR"
  echo "    dist/$DMG_NAME"
fi

# --- Prüfsummen ------------------------------------------------------------
echo "==> Writing checksums"
"$PYTHON" tools/make_checksums.py >/dev/null
echo "    dist/sha.txt"

SIZE="$(du -sh "dist/$APP_NAME.app" | cut -f1)"
echo
echo "Done: dist/$APP_NAME.app ($SIZE)"
echo "Drag it into /Applications and start it with a double-click."
