import numpy as np
import pandas as pd

PRED_IN  = r"C:\ANALYTICS207\data\predictions\archives\games_predictions_current__before__20260217_011902.parquet"
PRED_OUT = r"C:\ANALYTICS207\data\predictions\archives\games_predictions_current__before__20260217_011902__MARGINCAL.parquet"
TRUTH    = r"C:\ANALYTICS207\data\core\games_game_core_v40.parquet"

pred_cols = ["GameID","PredMargin","PredTotalPoints","PredHomeScore","PredAwayScore","PredHomeWinProb","ResultHomeWin"]
truth_cols = ["GameID","Played","HomeScore","AwayScore"]

pred = pd.read_parquet(PRED_IN, columns=pred_cols).copy()
truth = pd.read_parquet(TRUTH, columns=truth_cols).copy()

pred["GameID"] = pred["GameID"].astype(str).str.strip()
truth["GameID"] = truth["GameID"].astype(str).str.strip()
truth["Played"] = truth["Played"].fillna(False).astype(bool)

for c in ["PredMargin","PredTotalPoints","PredHomeScore","PredAwayScore","PredHomeWinProb"]:
    pred[c] = pd.to_numeric(pred[c], errors="coerce")

truth["HomeScore"] = pd.to_numeric(truth["HomeScore"], errors="coerce")
truth["AwayScore"] = pd.to_numeric(truth["AwayScore"], errors="coerce")

j = pred.merge(truth, on="GameID", how="inner")
j = j[j["Played"]].dropna(subset=["HomeScore","AwayScore","PredMargin","PredTotalPoints"]).copy()

y = (j["HomeScore"] - j["AwayScore"]).to_numpy(float)          # actual margin
x = j["PredMargin"].to_numpy(float)                             # predicted margin

# Fit y = a + b*x (least squares)
b, a = np.polyfit(x, y, 1)

# Apply to full pred file
out = pred.copy()
out["PredMargin_adj"] = a + b * out["PredMargin"]
out["PredHomeScore_adj"] = 0.5 * (out["PredTotalPoints"] + out["PredMargin_adj"])
out["PredAwayScore_adj"] = 0.5 * (out["PredTotalPoints"] - out["PredMargin_adj"])

# Option: overwrite original score columns (comment out if you prefer to keep both)
out["PredMargin"] = out["PredMargin_adj"]
out["PredHomeScore"] = out["PredHomeScore_adj"]
out["PredAwayScore"] = out["PredAwayScore_adj"]

# Drop helper cols
out = out.drop(columns=["PredMargin_adj","PredHomeScore_adj","PredAwayScore_adj"])

out.to_parquet(PRED_OUT, index=False)

print("fit a,b =", float(a), float(b))
print("wrote", PRED_OUT)
