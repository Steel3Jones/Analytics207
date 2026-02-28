from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\ANALYTICS207")
travel_path = ROOT / "data" / "travel_core_v30.parquet"

df = pd.read_parquet(travel_path)

hodgdon = df[(df["Home"] == "Hodgdon HS") | (df["Away"] == "Hodgdon HS")].copy()

cols = ["Date", "Home", "Away", "MilesOneWay", "MilesRoundTrip"]
print(hodgdon[cols].sort_values("Date").to_string(index=False))
