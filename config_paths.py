# config_paths.py
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))

CORE_DIR        = DATA_DIR / "core"
PREDICTIONS_DIR = DATA_DIR / "predictions"

GAMES_CORE_FILE      = CORE_DIR / "games_game_core_v50.parquet"
GAMES_PRED_CURRENT_FILE = PREDICTIONS_DIR / "games_predictions_current.parquet"
