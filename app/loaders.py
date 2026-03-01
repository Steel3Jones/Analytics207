import pandas as pd
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PUBLIC_PATH = DATA_DIR / "public" / "games_public_v50.parquet"

REQUIRED = {
  "GameID","HomeKey","AwayKey",
  "PredHomeWinProb","PredHomeScore","PredAwayScore",
  "PredMargin","PredTotalPoints",
  "CoreVersion","PredBuildID",
}

@st.cache_data(show_spinner=False)
def load_games_public():
    df = pd.read_parquet(PUBLIC_PATH)
    missing = sorted(REQUIRED - set(df.columns))
    if missing:
        raise RuntimeError(f"games_public_v50 missing columns: {missing}")
    return df
