"""Erlaubt den Start per ``python -m easyocrmypdf``."""

from easyocrmypdf.app import main

if __name__ == "__main__":
    raise SystemExit(main())
