import pandas as pd
import streamlit as st

PUBLIC_PATH = r"C:\ANALYTICS207\data\public\games_public_v40.parquet"

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
        raise RuntimeError(f"games_public_v40 missing columns: {missing}")
    return df
