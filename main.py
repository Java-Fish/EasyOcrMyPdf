"""Startskript der Anwendung, zugleich Einstiegspunkt für PyInstaller."""

import sys

from ocrmypdf_gui.app import main

if __name__ == "__main__":
    sys.exit(main())
