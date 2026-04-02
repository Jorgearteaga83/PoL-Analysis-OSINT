from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = PROJECT_ROOT / "data"
IMAGE_DIR: Path = PROJECT_ROOT / "images"
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"
DB_PATH: Path = PROJECT_ROOT / "osint_osintpol.db"
MATPLOTLIB_STYLE: str = "default"


def ensure_directories() -> None:
    for d in (DATA_DIR, IMAGE_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)
