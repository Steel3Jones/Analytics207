from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\ANALYTICS207")
CATALOG_PATH = ROOT / "core" / "metrics_catalog.csv"

_catalog = pd.read_csv(CATALOG_PATH)

# Indexes for lookups
_by_col = _catalog.set_index("column")
_by_key = _catalog.set_index("metric_key")


def _first_or_none(val):
    """Return first scalar value if Series/array, else val."""
    if isinstance(val, pd.Series):
        return val.iloc[0]
    if isinstance(val, (list, tuple)):
        return val[0]
    return val


def label_for_column(col: str) -> str:
    """Display label for a dataframe column."""
    if col in _by_col.index:
        raw = _by_col.loc[col, "label"]
        value = _first_or_none(raw)
        if pd.notna(value) and str(value).strip():
            return str(value)
    return col


def label_for_key(metric_key: str) -> str:
    if metric_key in _by_key.index:
        raw = _by_key.loc[metric_key, "label"]
        value = _first_or_none(raw)
        if pd.notna(value) and str(value).strip():
            return str(value)
    return metric_key


def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with columns renamed to their labels."""
    mapping = {c: label_for_column(c) for c in df.columns}
    return df.rename(columns=mapping)


def active_columns(source: str) -> list[str]:
    """All active columns for a given source table."""
    subset = _catalog[
        (_catalog["source"] == source) & (_catalog["active"] == 1)
    ]
    return subset["column"].tolist()


def active_metrics_for_source(source: str) -> list[str]:
    """Metric keys/columns that are active for a given source."""
    return active_columns(source)
