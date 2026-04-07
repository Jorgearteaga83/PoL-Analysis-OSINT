from pathlib import Path  # Import necessary module or component

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]  # Close bracket/parenthesis
DATA_DIR: Path = PROJECT_ROOT / "data"  # Execute statement or expression
IMAGE_DIR: Path = PROJECT_ROOT / "images"  # Execute statement or expression
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"  # Execute statement or expression
DB_PATH: Path = PROJECT_ROOT / "osint_osintpol.db"  # Execute statement or expression
MATPLOTLIB_STYLE: str = "default"  # Execute statement or expression


def ensure_directories() -> None:  # Define function ensure_directories
    for d in (DATA_DIR, IMAGE_DIR, OUTPUT_DIR):  # Iterate in a loop
        d.mkdir(parents=True, exist_ok=True)  # Close bracket/parenthesis
