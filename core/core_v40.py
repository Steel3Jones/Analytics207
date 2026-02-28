"""
core_v40.py
Core v40: Facts + Enrichment + (separate) Predictions integration.

RULES:
- Facts: games + teams base tables
- Predictions: only imported from walk_forward output, never recomputed here
- Derived: performance tables etc. derived from facts+preds
"""

# ======================================================================================
#-------------HEADER: Imports & Constants
# ======================================================================================
# imports
# paths
# version ids
# constants (HCA points, etc.)
#-------------FOOTER: Imports & Constants
# ======================================================================================


# ======================================================================================
#-------------HEADER: Schema Catalogs
# ======================================================================================
# TEAM_COLUMNS_V40 = [...]
# GAME_COLUMNS_V40 = [...]
# PRED_COLUMNS_V40 = [...]
# ensure_team_schema(df)
# ensure_game_schema(df)
# ensure_pred_schema(df)
#-------------FOOTER: Schema Catalogs
# ======================================================================================


# ======================================================================================
#-------------HEADER: I/O Helpers (Atomic writes, path helpers)
# ======================================================================================
# read_parquet_safe(path)
# atomic_write_parquet(df, path)  (temp file + replace)
#-------------FOOTER: I/O Helpers
# ======================================================================================


# ======================================================================================
#-------------HEADER: Core Facts Builders (NO predictions)
# ======================================================================================
# build_games_core_v40(raw_games_df) -> games_df
# build_teams_core_v40(raw_teams_df, games_df) -> teams_df
# enrich_games_facts_v40(games_df, teams_df) -> games_df (still no Pred*)
#-------------FOOTER: Core Facts Builders
# ======================================================================================


# ======================================================================================
#-------------HEADER: Predictions (Single source of truth)
# ======================================================================================
# load_predictions_current() -> preds_df  (reads games_predictions_current.parquet)
# validate_predictions(preds_df, games_df)  (1 row per GameID, coverage, dtypes)
# merge_predictions_into_games(games_df, preds_df) -> games_plus_preds_df
# NOTE: This section never computes PredHomeWinProb/PredMargin; it only imports/merges.
#-------------FOOTER: Predictions
# ======================================================================================


# ======================================================================================
#-------------HEADER: Derived Tables (Performance, calibration, etc.)
# ======================================================================================
# build_performance_tables_v40(games_plus_preds_df) -> summary, per_game, calib, spread
# write_derived_outputs(...)
#-------------FOOTER: Derived Tables
# ======================================================================================


# ======================================================================================
#-------------HEADER: Main Orchestration
# ======================================================================================
# main():
#   build facts
#   load preds from walk-forward output
#   merge facts+preds
#   build derived tables
#   write outputs
#-------------FOOTER: Main Orchestration
# ======================================================================================
