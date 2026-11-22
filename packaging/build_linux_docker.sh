#!/usr/bin/env bash
# Baut die Linux-Pakete in einem Container, auch von macOS oder Windows aus.
#
#   ./packaging/build_linux_docker.sh                 # x86_64, wie für Releases
#   ./packaging/build_linux_docker.sh --arch arm64    # für ARM-Linux
#   ./packaging/build_linux_docker.sh --shell         # Eingabeaufforderung im Container
#
# Warum ein Container: Die glibc des Build-Systems legt fest, ab welcher
# Distribution das Ergebnis läuft. Das Abbild baut auf Ubuntu 22.04 auf und
# deckt damit auch Debian 12 und RHEL 9 ab.
#
# Auf Apple Silicon läuft der x86_64-Bau unter Emulation und braucht deutlich
# länger als nativ. Das ist normal.
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ABBILD="ocrmypdf-gui-build"
ARCH="amd64"
SHELL_MODUS=0
BUILD_ARGUMENTE=("--vendor" "--appimage")

while [ $# -gt 0 ]; do
  case "$1" in
    --arch) ARCH="$2"; shift 2 ;;
    --shell) SHELL_MODUS=1; shift ;;
    --no-vendor) BUILD_ARGUMENTE=("--appimage"); shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

case "$ARCH" in
  amd64|x86_64) PLATTFORM="linux/amd64"; APPIMAGE_ARCH="x86_64" ;;
  arm64|aarch64) PLATTFORM="linux/arm64"; APPIMAGE_ARCH="aarch64" ;;
  *) echo "Unknown architecture: $ARCH" >&2; exit 1 ;;
esac

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and try again." >&2
  exit 1
fi

echo "==> Building the image for $PLATTFORM"
docker build \
  --platform "$PLATTFORM" \
  --build-arg "APPIMAGETOOL_ARCH=$APPIMAGE_ARCH" \
  -f packaging/Dockerfile.linux \
  -t "$ABBILD:$ARCH" \
  .

# Erzeugnisse des Wirtssystems nicht mit denen des Containers vermischen.
mkdir -p dist build

if [ "$SHELL_MODUS" -eq 1 ]; then
  echo "==> Shell in the container (project is mounted at /projekt)"
  exec docker run --rm -it --platform "$PLATTFORM" \
    -v "$PROJECT_ROOT:/projekt" "$ABBILD:$ARCH" bash
fi

echo "==> Building the application"
docker run --rm --platform "$PLATTFORM" \
  -v "$PROJECT_ROOT:/projekt" \
  "$ABBILD:$ARCH" \
  ./packaging/build_linux.sh "${BUILD_ARGUMENTE[@]}"

echo
echo "Done. Results in dist/:"
ls -lh dist/ | grep -iE "linux|AppImage" | sed 's/^/  /' || true
