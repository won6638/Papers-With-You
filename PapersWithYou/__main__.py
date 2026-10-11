from pathlib import Path
from .cli import main

raise SystemExit(main(app_dir=Path(__file__).resolve().parent.parent))
