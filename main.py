"""Startskript der Anwendung, zugleich Einstiegspunkt für PyInstaller."""

import sys

from easyocrmypdf.app import main

if __name__ == "__main__":
    sys.exit(main())
