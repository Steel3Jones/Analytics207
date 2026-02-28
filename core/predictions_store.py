from __future__ import annotations

from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")

PRED_CURRENT = DATA_DIR / "games_predictions_current.parquet"
PRED_V31 = DATA_DIR / "games_predictions_v31.parquet"

def load_predictions(version: str = "current") -> pd.DataFrame:
    if version == "current":
        path = PRED_CURRENT
    elif version == "v31":
        path = PRED_V31
    else:
        raise ValueError(f"Unknown version: {version}")

    if not path.exists():
        raise FileNotFoundError(f"Missing predictions parquet: {path}")

    return pd.read_parquet(path)
