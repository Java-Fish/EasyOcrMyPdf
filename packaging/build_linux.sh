#!/usr/bin/env bash
# Baut OCRmyPDF GUI für Linux.
#
#   ./packaging/build_linux.sh              # Programmordner und .tar.gz
#   ./packaging/build_linux.sh --vendor     # Tesseract/Ghostscript mitliefern
#   ./packaging/build_linux.sh --appimage   # zusätzlich eine .AppImage
#
# Die AppImage ist das, was ein Anwender per Doppelklick startet. Sie braucht
# das Werkzeug "appimagetool"; fehlt es, nennt das Skript den Bezugsweg.
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="OCRmyPDF GUI"
BINARY_NAME="ocrmypdf-gui"
# Der Ordner lässt sich über die Umgebung überschreiben. Im Docker-Abbild
# liegt er außerhalb des Projekts, weil dort bereits ein .venv für macOS
# eingehängt sein kann.
VENV="${VENV:-.venv}"
DO_VENDOR=0
MAKE_APPIMAGE=0

for argument in "$@"; do
  case "$argument" in
    --vendor) DO_VENDOR=1 ;;
    --appimage) MAKE_APPIMAGE=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $argument" >&2; exit 1 ;;
  esac
done

# --- Virtuelle Umgebung vorbereiten ---------------------------------------
# Welcher Interpreter die Umgebung anlegt, lässt sich vorgeben. Nötig etwa im
# Docker-Abbild: dort ist "python3" die Version der Distribution (3.10),
# OCRmyPDF verlangt aber mindestens 3.11.
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d "$VENV" ]; then
  echo "==> Creating virtual environment with $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$VENV"
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
  "$PYTHON" tools/vendor_linux.py
else
  # Ohne diese Variable bände die Spec einen aus einem früheren Lauf
  # übriggebliebenen vendor-Ordner stillschweigend mit ein.
  export OCRMYPDF_GUI_NO_VENDOR=1
fi

# --- Bauen -----------------------------------------------------------------
echo "==> Building the application"
rm -rf build "dist/$BINARY_NAME"
"$PYTHON" -m PyInstaller packaging/ocrmypdf_gui.spec --noconfirm --distpath dist --workpath build

if [ ! -x "dist/$BINARY_NAME/$BINARY_NAME" ]; then
  echo "Build failed: dist/$BINARY_NAME/$BINARY_NAME was not created" >&2
  exit 1
fi

# --- Startskript und Desktop-Eintrag für die Installation von Hand ---------
install -m 644 packaging/ocrmypdf-gui.desktop "dist/$BINARY_NAME/"
install -m 644 resources/icon.png "dist/$BINARY_NAME/ocrmypdf-gui.png"

# --- Archiv ----------------------------------------------------------------
echo "==> Creating archive"
ARCHIVE="dist/OCRmyPDF-GUI-linux-$(uname -m).tar.gz"
rm -f "$ARCHIVE"
tar -czf "$ARCHIVE" -C dist "$BINARY_NAME"
echo "    $ARCHIVE"

# --- Optional: AppImage ----------------------------------------------------
if [ "$MAKE_APPIMAGE" -eq 1 ]; then
  echo "==> Creating AppImage"
  if ! command -v appimagetool >/dev/null 2>&1 && [ ! -f /usr/local/share/appimage-runtime ]; then
    echo "    Neither appimagetool nor an AppImage runtime was found. Get the tool with:" >&2
    echo "      wget -O ~/.local/bin/appimagetool \\" >&2
    echo "        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$(uname -m).AppImage" >&2
    echo "      chmod +x ~/.local/bin/appimagetool" >&2
  else
    APPDIR="build/AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
             "$APPDIR/usr/share/icons/hicolor/512x512/apps"

    cp -R "dist/$BINARY_NAME/." "$APPDIR/usr/bin/"
    install -m 644 packaging/ocrmypdf-gui.desktop \
      "$APPDIR/usr/share/applications/ocrmypdf-gui.desktop"
    install -m 644 packaging/ocrmypdf-gui.desktop "$APPDIR/ocrmypdf-gui.desktop"
    install -m 644 resources/icon.png \
      "$APPDIR/usr/share/icons/hicolor/512x512/apps/ocrmypdf-gui.png"
    install -m 644 resources/icon.png "$APPDIR/ocrmypdf-gui.png"

    # AppRun ist der Einstiegspunkt der AppImage.
    cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/ocrmypdf-gui" "$@"
APPRUN
    chmod +x "$APPDIR/AppRun"

    APPIMAGE="dist/OCRmyPDF-GUI-$(uname -m).AppImage"
    RUNTIME="/usr/local/share/appimage-runtime"
    rm -f "$APPIMAGE"

    if command -v appimagetool >/dev/null 2>&1 && appimagetool --version >/dev/null 2>&1; then
      # ARCH ist für appimagetool verbindlich, sonst bricht es ab.
      ARCH="$(uname -m)" appimagetool "$APPDIR" "$APPIMAGE" >/dev/null
      echo "    $APPIMAGE"
    elif [ -f "$RUNTIME" ] && command -v mksquashfs >/dev/null 2>&1; then
      # Ohne lauffähiges appimagetool von Hand zusammensetzen. Eine AppImage
      # ist ein Squashfs-Abbild, dem die Startroutine vorangestellt wird.
      echo "    (appimagetool nicht ausführbar, baue die AppImage direkt)"
      mksquashfs "$APPDIR" build/AppDir.squashfs \
        -root-owned -noappend -quiet -no-progress -comp zstd
      cat "$RUNTIME" build/AppDir.squashfs > "$APPIMAGE"
      chmod +x "$APPIMAGE"
      rm -f build/AppDir.squashfs
      echo "    $APPIMAGE"
    else
      echo "    Neither appimagetool nor mksquashfs is usable; skipping." >&2
    fi
  fi
fi

# --- Prüfsummen ------------------------------------------------------------
echo "==> Writing checksums"
"$PYTHON" tools/make_checksums.py >/dev/null
echo "    dist/sha.txt"

SIZE="$(du -sh "dist/$BINARY_NAME" | cut -f1)"
echo
echo "Done: dist/$BINARY_NAME ($SIZE)"
echo "Start it with:  ./dist/$BINARY_NAME/$BINARY_NAME"
