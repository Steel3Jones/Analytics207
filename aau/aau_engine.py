import pandas as pd
import numpy as np
import os

# ============================================================
# AAU STATS ENGINE — aau_engine.py
# Location: C:\ANALYTICS207\aau\
# Run from anywhere:  python aau\aau_engine.py
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Load raw inputs ---
players = pd.read_csv(os.path.join(SCRIPT_DIR, "aau_players.csv"))
game_stats = pd.read_csv(os.path.join(SCRIPT_DIR, "aau_game_stats.csv"))

# ============================================================
# PER-GAME ADVANCED STATS
# ============================================================
gs = game_stats.copy()

# Shooting percentages
gs['fg_pct'] = np.where(gs['fga'] > 0, gs['fgm'] / gs['fga'], np.nan)
gs['three_pct'] = np.where(gs['3pa'] > 0, gs['3pm'] / gs['3pa'], np.nan)
gs['ft_pct'] = np.where(gs['fta'] > 0, gs['ftm'] / gs['fta'], np.nan)
gs['ts_pct'] = np.where((gs['fga'] + 0.44 * gs['fta']) > 0,
    gs['pts'] / (2 * (gs['fga'] + 0.44 * gs['fta'])), np.nan)
gs['efg_pct'] = np.where(gs['fga'] > 0,
    (gs['fgm'] + 0.5 * gs['3pm']) / gs['fga'], np.nan)

# 2-point field goals
gs['2pm'] = gs['fgm'] - gs['3pm']
gs['2pa'] = gs['fga'] - gs['3pa']

# Playmaking & efficiency
gs['ast_to_ratio'] = np.where(gs['tov'] > 0, gs['ast'] / gs['tov'],
    np.where(gs['ast'] > 0, gs['ast'], 0))
gs['stocks'] = gs['stl'] + gs['blk']
gs['pts_responsible'] = gs['pts'] + (gs['ast'] * 2.5)
gs['poss_used'] = gs['fga'] + 0.44 * gs['fta'] + gs['tov']

# Game Score (Hollinger)
gs['game_score'] = (gs['pts'] + 0.4*gs['fgm'] - 0.7*gs['fga']
    - 0.4*(gs['fta'] - gs['ftm']) + 0.7*gs['oreb'] + 0.3*gs['dreb']
    + gs['stl'] + 0.7*gs['ast'] + 0.7*gs['blk'] - 0.4*gs['pf'] - gs['tov'])

# --- TEAM TOTALS per game (needed for usage rate, off/def rating) ---
team_game = gs.groupby('game_id').agg(
    tm_min=('min','sum'), tm_fga=('fga','sum'), tm_fta=('fta','sum'),
    tm_tov=('tov','sum'), tm_pts=('pts','sum'), tm_fgm=('fgm','sum'),
    tm_oreb=('oreb','sum'), tm_dreb=('dreb','sum'), tm_reb=('reb','sum'),
    tm_ast=('ast','sum'), tm_3pm=('3pm','sum'), tm_ftm=('ftm','sum'),
    tm_blk=('blk','sum'), tm_stl=('stl','sum'), tm_pf=('pf','sum'),
    opp_score=('opp_score','first'), team_score=('team_score','first')
).reset_index()

gs = gs.merge(team_game, on='game_id', suffixes=('','_tm'))

# --- USAGE RATE ---
# USG% = 100 * ((FGA + 0.44*FTA + TOV) * (Tm_MIN / 5)) / (MIN * (Tm_FGA + 0.44*Tm_FTA + Tm_TOV))
gs['usage_rate'] = np.where(
    gs['min'].notna() & (gs['min'] > 0) & ((gs['tm_fga'] + 0.44*gs['tm_fta'] + gs['tm_tov']) > 0),
    100 * ((gs['fga'] + 0.44*gs['fta'] + gs['tov']) * (gs['tm_min'] / 5)) /
    (gs['min'] * (gs['tm_fga'] + 0.44*gs['tm_fta'] + gs['tm_tov'])),
    np.nan
)

# --- POINTS PER MINUTE ---
gs['pts_per_min'] = np.where(
    gs['min'].notna() & (gs['min'] > 0), gs['pts'] / gs['min'], np.nan)

# --- TEAM POSSESSIONS (estimated) ---
# Poss ≈ FGA - OREB + TOV + 0.44*FTA
gs['tm_poss'] = gs['tm_fga'] - gs['tm_oreb'] + gs['tm_tov'] + 0.44 * gs['tm_fta']
gs['opp_poss'] = gs['tm_poss']  # approximate

# --- OFFENSIVE RATING (simplified individual) ---
# ORtg ≈ (PTS / individual possessions used) * 100
gs['ind_poss'] = gs['fga'] - gs['oreb'] + gs['tov'] + 0.44 * gs['fta']
gs['off_rating'] = np.where(
    gs['ind_poss'] > 0,
    (gs['pts'] / gs['ind_poss']) * 100,
    np.nan
)

# --- DEFENSIVE RATING (simplified individual estimate) ---
# DRtg ≈ opponent points * (player_min / team_min) scaled to per-100-poss
gs['def_rating'] = np.where(
    gs['min'].notna() & (gs['min'] > 0) & (gs['tm_min'] > 0) & (gs['tm_poss'] > 0),
    (gs['opp_score_tm'] / gs['tm_poss']) * 100,
    np.nan
)

# --- PER (Simplified Hollinger) ---
# uPER = (1/MIN) * [3P + (2/3)*AST + (2-1.07*(Tm_AST/Tm_FGM))*FGM + FTM*0.5*(1+(1-(Tm_AST/Tm_FGM))+(2/3)*(Tm_AST/Tm_FGM))
#         - VOP*TOV - VOP*DRB%*(FGA-FGM) - VOP*0.44*(0.44+(0.56*DRB%))*(FTA-FTM)
#         + VOP*(1-DRB%)*(TRB-OREB) + VOP*DRB%*OREB + VOP*STL + VOP*DRB%*BLK
#         - PF*((lg_FT/lg_PF)-0.44*(lg_FTA/lg_PF)*VOP)]
# Simplified version that works without league averages:
# EFF-based PER = (PTS + REB + AST + STL + BLK - (FGA-FGM) - (FTA-FTM) - TOV) / MIN * adjustment

# We'll use a practical simplified PER that's meaningful for AAU level
gs['tm_ast_rate'] = np.where(gs['tm_fgm'] > 0, gs['tm_ast'] / gs['tm_fgm'], 0.5)

# Value of possession (VOP) = team_pts / (team_fga - team_oreb + team_tov + 0.44*team_fta)
gs['vop'] = np.where(gs['tm_poss'] > 0, gs['tm_pts'] / gs['tm_poss'], np.nan)

# Defensive rebound % estimate (league-level approximation)
drb_pct = 0.75  # typical

gs['uper'] = np.where(
    gs['min'].notna() & (gs['min'] > 0) & gs['vop'].notna(),
    (1 / gs['min']) * (
        gs['3pm']
        + (2/3) * gs['ast']
        + (2 - 1.07 * gs['tm_ast_rate']) * gs['fgm']
        + gs['ftm'] * 0.5 * (1 + (1 - gs['tm_ast_rate']) + (2/3) * gs['tm_ast_rate'])
        - gs['vop'] * gs['tov']
        - gs['vop'] * drb_pct * (gs['fga'] - gs['fgm'])
        - gs['vop'] * 0.44 * (0.44 + 0.56 * drb_pct) * (gs['fta'] - gs['ftm'])
        + gs['vop'] * (1 - drb_pct) * (gs['reb'] - gs['oreb'])
        + gs['vop'] * drb_pct * gs['oreb']
        + gs['vop'] * gs['stl']
        + gs['vop'] * drb_pct * gs['blk']
        - gs['pf'] * ((gs['tm_ftm'] / np.maximum(gs['tm_pf'], 1)) - 0.44 * (gs['tm_fta'] / np.maximum(gs['tm_pf'], 1)) * gs['vop'])
    ),
    np.nan
)

# Normalize PER to league average of 15
avg_uper = gs['uper'].mean()
gs['per'] = np.where(gs['uper'].notna() & (avg_uper > 0),
    gs['uper'] * (15 / avg_uper), np.nan)

# Per-36 and Per-40 normalized stats
for base, label in [(36, 'per36'), (40, 'per40')]:
    for col in ['pts','reb','ast','stl','blk','tov','fgm','fga','3pm','3pa','ftm','fta','oreb','dreb','stocks']:
        gs[f'{col}_{label}'] = np.where(
            gs['min'].notna() & (gs['min'] > 0),
            gs[col] / gs['min'] * base, np.nan)

# Double-double detection
stat_dd = ['pts', 'reb', 'ast', 'stl', 'blk']
gs['dd_count'] = sum((gs[c] >= 10).astype(int) for c in stat_dd)
gs['is_double_double'] = gs['dd_count'] >= 2

# Round all floats
for col in gs.select_dtypes(include=[np.floating]).columns:
    gs[col] = gs[col].round(3)

# ============================================================
# SEASON PLAYER SUMMARIES
# ============================================================
agg = gs.groupby('player_id').agg(
    games_played=('game_id', 'nunique'),
    total_min=('min', 'sum'),
    total_pts=('pts','sum'), total_fgm=('fgm','sum'), total_fga=('fga','sum'),
    total_3pm=('3pm','sum'), total_3pa=('3pa','sum'),
    total_ftm=('ftm','sum'), total_fta=('fta','sum'),
    total_oreb=('oreb','sum'), total_dreb=('dreb','sum'), total_reb=('reb','sum'),
    total_ast=('ast','sum'), total_stl=('stl','sum'), total_blk=('blk','sum'),
    total_tov=('tov','sum'), total_pf=('pf','sum'), total_stocks=('stocks','sum'),
    ppg=('pts','mean'), rpg=('reb','mean'), apg=('ast','mean'),
    spg=('stl','mean'), bpg=('blk','mean'), topg=('tov','mean'),
    mpg=('min','mean'), fpg=('pf','mean'),
    avg_game_score=('game_score','mean'), avg_ts_pct=('ts_pct','mean'),
    avg_efg_pct=('efg_pct','mean'), avg_ast_to=('ast_to_ratio','mean'),
    avg_pts_per_min=('pts_per_min','mean'),
    avg_usage_rate=('usage_rate','mean'),
    avg_off_rating=('off_rating','mean'),
    avg_def_rating=('def_rating','mean'),
    avg_per=('per','mean'),
    avg_pts_per36=('pts_per36','mean'), avg_reb_per36=('reb_per36','mean'),
    avg_ast_per36=('ast_per36','mean'), avg_stl_per36=('stl_per36','mean'),
    avg_blk_per36=('blk_per36','mean'),
    avg_pts_per40=('pts_per40','mean'), avg_reb_per40=('reb_per40','mean'),
    avg_ast_per40=('ast_per40','mean'), avg_stl_per40=('stl_per40','mean'),
    avg_blk_per40=('blk_per40','mean'),
    pts_high=('pts','max'), reb_high=('reb','max'), ast_high=('ast','max'),
    stl_high=('stl','max'), blk_high=('blk','max'),
    game_score_high=('game_score','max'), per_high=('per','max'),
    double_doubles=('is_double_double','sum'),
    wins=('result', lambda x: (x=='W').sum()),
    losses=('result', lambda x: (x=='L').sum()),
).reset_index()

# Season shooting from totals
agg['season_fg_pct'] = np.where(agg['total_fga']>0, agg['total_fgm']/agg['total_fga'], np.nan)
agg['season_3pt_pct'] = np.where(agg['total_3pa']>0, agg['total_3pm']/agg['total_3pa'], np.nan)
agg['season_ft_pct'] = np.where(agg['total_fta']>0, agg['total_ftm']/agg['total_fta'], np.nan)
agg['season_ts_pct'] = np.where(
    (agg['total_fga'] + 0.44*agg['total_fta']) > 0,
    agg['total_pts'] / (2*(agg['total_fga'] + 0.44*agg['total_fta'])), np.nan)
agg['season_efg_pct'] = np.where(
    agg['total_fga']>0, (agg['total_fgm'] + 0.5*agg['total_3pm'])/agg['total_fga'], np.nan)

# Net rating
agg['net_rating'] = agg['avg_off_rating'] - agg['avg_def_rating']

for col in agg.select_dtypes(include=[np.floating]).columns:
    agg[col] = agg[col].round(3)

# Merge with player bio
final = agg.merge(players, on='player_id', how='left')
bio_cols = ['player_id','first_name','last_name','jersey_number','aau_team','position',
            'grad_class','height','weight','high_school','hometown','gpa',
            'highlight_video_url','profile_photo_url']
stat_cols = [c for c in final.columns if c not in bio_cols]
final = final[bio_cols + stat_cols]

# ============================================================
# WRITE PARQUETS
# ============================================================
gs.to_parquet(os.path.join(DATA_DIR, "aau_game_stats_advanced.parquet"), index=False)
final.to_parquet(os.path.join(DATA_DIR, "aau_player_season_summary.parquet"), index=False)

print(f"✅ data/aau_game_stats_advanced.parquet  — {gs.shape[0]} rows x {gs.shape[1]} cols")
print(f"✅ data/aau_player_season_summary.parquet — {final.shape[0]} rows x {final.shape[1]} cols")
print("Done.")
