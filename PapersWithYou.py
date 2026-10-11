"""Portable launcher: its parent directory is the default application directory."""
from pathlib import Path
from citeweave.cli import main

if __name__ == "__main__":
    raise SystemExit(main(app_dir=Path(__file__).resolve().parent))
