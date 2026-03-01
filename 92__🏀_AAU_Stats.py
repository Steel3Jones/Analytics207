import streamlit as st
import pandas as pd
from pathlib import Path
import os

# ============================================================
# AAU BASKETBALL — Player Stats Dashboard
# Location: C:\ANALYTICS207\pages\aau_stats.py
# ============================================================


from sidebar_auth import render_sidebar_auth
render_sidebar_auth()

st.set_page_config(page_title="AAU Basketball Stats", page_icon="🏀", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT    = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "aau" / "data"))
SUMMARY_PATH = DATA_ROOT / "aau_player_season_summary.parquet"
GAMES_PATH   = DATA_ROOT / "aau_game_stats_advanced.parquet"

# --- Custom CSS for ESPN-style cards ---
st.markdown("""
<style>
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 18px 14px;
        text-align: center;
        border-left: 4px solid #e94560;
        margin-bottom: 8px;
    }
    .stat-card .stat-value {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        margin: 4px 0;
        line-height: 1;
    }
    .stat-card .stat-label {
        font-size: 0.7rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .stat-card-green { border-left-color: #00d4aa; }
    .stat-card-blue { border-left-color: #0095ff; }
    .stat-card-gold { border-left-color: #ffd700; }
    .stat-card-purple { border-left-color: #a855f7; }
    .stat-card-orange { border-left-color: #ff6b35; }
    .stat-card-cyan { border-left-color: #00d4ff; }

    .hero-card {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        border: 1px solid #333;
        margin-bottom: 12px;
    }
    .hero-card .player-name {
        font-size: 1.8rem;
        font-weight: 800;
        color: #fff;
        margin: 0;
    }
    .hero-card .player-info {
        font-size: 0.9rem;
        color: #a0aec0;
        margin-top: 4px;
    }
    .hero-card .player-number {
        font-size: 3.5rem;
        font-weight: 900;
        color: #e94560;
        opacity: 0.3;
        position: relative;
        top: -10px;
        margin-bottom: -30px;
    }

    .section-header {
        background: linear-gradient(90deg, #e94560 0%, transparent 100%);
        padding: 8px 16px;
        border-radius: 6px;
        margin: 20px 0 12px 0;
        font-size: 1rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 1px;
    }

    .tier-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 1px;
    }
    .tier-elite { background: linear-gradient(135deg, #ffd700, #ff8c00); }
    .tier-star { background: linear-gradient(135deg, #a855f7, #6366f1); }
    .tier-starter { background: linear-gradient(135deg, #0095ff, #00d4ff); }
    .tier-rotation { background: linear-gradient(135deg, #4a5568, #718096); }
    .tier-bench { background: linear-gradient(135deg, #2d3748, #4a5568); }

    .comparison-win { color: #00d4aa; font-weight: 800; }
    .comparison-lose { color: #666; }
</style>
""", unsafe_allow_html=True)

def stat_card(label, value, color_class=""):
    return f'''<div class="stat-card {color_class}">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
    </div>'''

def per_tier(per_val):
    if pd.isna(per_val): return '<span class="tier-badge tier-bench">N/A</span>'
    if per_val >= 25: return f'<span class="tier-badge tier-elite">ELITE {per_val:.1f}</span>'
    if per_val >= 20: return f'<span class="tier-badge tier-star">ALL-STAR {per_val:.1f}</span>'
    if per_val >= 15: return f'<span class="tier-badge tier-starter">STARTER {per_val:.1f}</span>'
    if per_val >= 10: return f'<span class="tier-badge tier-rotation">ROTATION {per_val:.1f}</span>'
    return f'<span class="tier-badge tier-bench">BENCH {per_val:.1f}</span>'

def fmt(val, fmt_str=".1f", pct=False):
    if pd.isna(val): return "—"
    if pct: return f"{val:.1%}"
    return f"{val:{fmt_str}}"

@st.cache_data
def load_data():
    summary = pd.read_parquet(SUMMARY_PATH)
    games   = pd.read_parquet(GAMES_PATH)
    return summary, games

summary, games = load_data()

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div style="text-align:center; padding: 0.5rem 0;">
    <h1 style="margin:0; font-size:2.8rem; font-weight:900; letter-spacing:-1px;">
        🏀 AAU BASKETBALL
    </h1>
    <p style="margin:0; font-size:1rem; color:#e94560; letter-spacing:4px; font-weight:600;">
        PLAYER STATS & ADVANCED ANALYTICS
    </p>
</div>
""", unsafe_allow_html=True)

teams = summary['aau_team'].dropna().unique().tolist()
selected_team = st.selectbox("Select Team", teams, index=0)
team_data = summary[summary['aau_team'] == selected_team].copy()
team_games = games[games['aau_team'] == selected_team].copy()

# --- Team overview cards ---
total_games = team_games['game_id'].nunique()
total_wins = team_games.drop_duplicates('game_id')['result'].eq('W').sum()
total_losses = total_games - total_wins
team_ppg = team_games.groupby('game_id')['pts'].sum().mean()
team_avg_per = team_data['avg_per'].mean()
team_avg_usage = team_data['avg_usage_rate'].mean()

cols = st.columns(6)
cols[0].markdown(stat_card("Games", total_games, "stat-card-green"), unsafe_allow_html=True)
cols[1].markdown(stat_card("Record", f"{total_wins}-{total_losses}", "stat-card-blue"), unsafe_allow_html=True)
cols[2].markdown(stat_card("Team PPG", f"{team_ppg:.1f}", "stat-card-gold"), unsafe_allow_html=True)
cols[3].markdown(stat_card("Roster", len(team_data), "stat-card-purple"), unsafe_allow_html=True)
cols[4].markdown(stat_card("Avg PER", f"{team_avg_per:.1f}", "stat-card-orange"), unsafe_allow_html=True)
cols[5].markdown(stat_card("Avg USG%", f"{team_avg_usage:.1f}", "stat-card-cyan"), unsafe_allow_html=True)

# ============================================================
# SEASON LEADERBOARD
# ============================================================
st.markdown('<div class="section-header">📊 SEASON LEADERBOARD</div>', unsafe_allow_html=True)

sort_col = st.selectbox(
    "Sort by",
    ["ppg","avg_per","avg_usage_rate","rpg","apg","avg_game_score",
     "season_ts_pct","avg_off_rating","net_rating","mpg"],
    index=0,
)

leaderboard = team_data[[
    'first_name','last_name','position','grad_class','games_played',
    'ppg','rpg','apg','spg','bpg','topg','mpg','avg_per','avg_usage_rate',
    'avg_off_rating','avg_def_rating','net_rating','avg_game_score',
    'season_fg_pct','season_3pt_pct','season_ft_pct','season_ts_pct'
]].sort_values(sort_col, ascending=False).reset_index(drop=True)

for col in ['season_fg_pct','season_3pt_pct','season_ft_pct','season_ts_pct']:
    leaderboard[col] = leaderboard[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—")
for col in [
    'ppg','rpg','apg','spg','bpg','topg','mpg','avg_per','avg_usage_rate',
    'avg_off_rating','avg_def_rating','net_rating','avg_game_score'
]:
    leaderboard[col] = leaderboard[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

leaderboard.columns = [
    'First','Last','Pos','Class','GP','PPG','RPG','APG','SPG','BPG',
    'TOPG','MPG','PER','USG%','ORtg','DRtg','NET','GmScore',
    'FG%','3PT%','FT%','TS%',
]
leaderboard.index = leaderboard.index + 1
st.dataframe(leaderboard, use_container_width=True, height=420)

# ============================================================
# PLAYER PROFILE
# ============================================================
st.markdown('<div class="section-header">🎯 PLAYER PROFILE</div>', unsafe_allow_html=True)

player_list = team_data.apply(lambda r: f"{r['first_name']} {r['last_name']}", axis=1).tolist()
selected_player_name = st.selectbox("Select Player", player_list)

first, last = selected_player_name.split(" ", 1)
player = team_data[(team_data['first_name'] == first) & (team_data['last_name'] == last)].iloc[0]
player_games = team_games[team_games['player_id'] == player['player_id']].sort_values('date')

# --- Hero card ---
st.markdown(f'''
<div class="hero-card">
    <div class="player-number">#{int(player['jersey_number'])}</div>
    <div class="player-name">{player['first_name']} {player['last_name']}</div>
    <div class="player-info">
        {player['position']} | Class of {int(player['grad_class'])} | {player['height']} | {int(player['weight'])} lbs<br>
        {player['high_school']} — {player['hometown']}
    </div>
    <div style="margin-top:12px;">{per_tier(player['avg_per'])}</div>
</div>
''', unsafe_allow_html=True)

# --- Core averages row ---
st.markdown("##### 📈 Season Averages")
ac = st.columns(8)
ac[0].markdown(stat_card("PPG", fmt(player['ppg']), "stat-card-green"), unsafe_allow_html=True)
ac[1].markdown(stat_card("RPG", fmt(player['rpg']), "stat-card-blue"), unsafe_allow_html=True)
ac[2].markdown(stat_card("APG", fmt(player['apg']), "stat-card-gold"), unsafe_allow_html=True)
ac[3].markdown(stat_card("SPG", fmt(player['spg']), "stat-card-purple"), unsafe_allow_html=True)
ac[4].markdown(stat_card("BPG", fmt(player['bpg']), "stat-card-orange"), unsafe_allow_html=True)
ac[5].markdown(stat_card("TOPG", fmt(player['topg']), "stat-card-cyan"), unsafe_allow_html=True)
ac[6].markdown(stat_card("MPG", fmt(player['mpg'])), unsafe_allow_html=True)
ac[7].markdown(stat_card("GP", int(player['games_played'])), unsafe_allow_html=True)

# --- Advanced analytics row ---
st.markdown("##### 🧠 Advanced Analytics")
ad = st.columns(7)
ad[0].markdown(stat_card("PER", fmt(player['avg_per']), "stat-card-gold"), unsafe_allow_html=True)
ad[1].markdown(stat_card("USG%", fmt(player['avg_usage_rate']), "stat-card-purple"), unsafe_allow_html=True)
ad[2].markdown(stat_card("ORtg", fmt(player['avg_off_rating']), "stat-card-green"), unsafe_allow_html=True)
ad[3].markdown(stat_card("DRtg", fmt(player['avg_def_rating']), "stat-card-blue"), unsafe_allow_html=True)
ad[4].markdown(stat_card("NET", fmt(player.get('net_rating', None)), "stat-card-orange"), unsafe_allow_html=True)
ad[5].markdown(stat_card("GmScore", fmt(player['avg_game_score']), "stat-card-cyan"), unsafe_allow_html=True)
ad[6].markdown(stat_card("AST/TO", fmt(player['avg_ast_to'], '.2f')), unsafe_allow_html=True)

# --- Shooting splits ---
st.markdown("##### 🎯 Shooting Splits")
sh = st.columns(5)
sh[0].markdown(stat_card("FG%", fmt(player['season_fg_pct'], pct=True), "stat-card-green"), unsafe_allow_html=True)
sh[1].markdown(stat_card("3PT%", fmt(player['season_3pt_pct'], pct=True), "stat-card-blue"), unsafe_allow_html=True)
sh[2].markdown(stat_card("FT%", fmt(player['season_ft_pct'], pct=True), "stat-card-gold"), unsafe_allow_html=True)
sh[3].markdown(stat_card("TS%", fmt(player['season_ts_pct'], pct=True), "stat-card-purple"), unsafe_allow_html=True)
sh[4].markdown(stat_card("eFG%", fmt(player['avg_efg_pct'], pct=True), "stat-card-orange"), unsafe_allow_html=True)

# --- Per-36 / Per-40 toggle ---
st.markdown("##### ⏱️ Pace-Adjusted Stats")
pace_mode = st.radio("Normalize to", ["Per 36 Minutes", "Per 40 Minutes"], horizontal=True)
suffix = "per36" if "36" in pace_mode else "per40"

pc = st.columns(5)
pc[0].markdown(stat_card("PTS", fmt(player[f'avg_pts_{suffix}']), "stat-card-green"), unsafe_allow_html=True)
pc[1].markdown(stat_card("REB", fmt(player[f'avg_reb_{suffix}']), "stat-card-blue"), unsafe_allow_html=True)
pc[2].markdown(stat_card("AST", fmt(player[f'avg_ast_{suffix}']), "stat-card-gold"), unsafe_allow_html=True)
pc[3].markdown(stat_card("STL", fmt(player[f'avg_stl_{suffix}']), "stat-card-purple"), unsafe_allow_html=True)
pc[4].markdown(stat_card("BLK", fmt(player[f'avg_blk_{suffix}']), "stat-card-orange"), unsafe_allow_html=True)

# --- Career Highs ---
st.markdown("##### 🏆 Career Highs")
ch = st.columns(7)
ch[0].markdown(stat_card("PTS", int(player['pts_high']), "stat-card-gold"), unsafe_allow_html=True)
ch[1].markdown(stat_card("REB", int(player['reb_high']), "stat-card-blue"), unsafe_allow_html=True)
ch[2].markdown(stat_card("AST", int(player['ast_high']), "stat-card-green"), unsafe_allow_html=True)
ch[3].markdown(stat_card("STL", int(player['stl_high']), "stat-card-purple"), unsafe_allow_html=True)
ch[4].markdown(stat_card("BLK", int(player['blk_high']), "stat-card-orange"), unsafe_allow_html=True)
ch[5].markdown(stat_card("GmScore", fmt(player['game_score_high']), "stat-card-cyan"), unsafe_allow_html=True)
ch[6].markdown(stat_card("PER", fmt(player.get('per_high', None)), "stat-card-gold"), unsafe_allow_html=True)

# ============================================================
# GAME LOG
# ============================================================
st.markdown('<div class="section-header">📋 GAME LOG</div>', unsafe_allow_html=True)

gamelog = player_games[[
    'date','opponent','result','min','pts','reb','ast','stl','blk','tov','pf',
    'fg_pct','three_pct','ft_pct','ts_pct','usage_rate','off_rating','per','game_score'
]].copy()

gamelog['result'] = player_games.apply(
    lambda r: f"{'W' if r['result']=='W' else 'L'} {int(r['team_score'])}-{int(r['opp_score'])}", axis=1,
)

for col in ['fg_pct','three_pct','ft_pct','ts_pct']:
    gamelog[col] = gamelog[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—")
for col in ['usage_rate','off_rating','per','game_score']:
    gamelog[col] = gamelog[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

gamelog.columns = [
    'Date','Opponent','Result','MIN','PTS','REB','AST','STL','BLK','TOV','PF',
    'FG%','3PT%','FT%','TS%','USG%','ORtg','PER','GmScore',
]

st.dataframe(gamelog.reset_index(drop=True), use_container_width=True, hide_index=True)

# ============================================================
# PLAYER COMPARISON
# ============================================================
st.markdown('<div class="section-header">🔬 PLAYER COMPARISON</div>', unsafe_allow_html=True)

comp_cols = st.columns(2)
with comp_cols[0]:
    p1_name = st.selectbox("Player 1", player_list, index=0, key="comp1")
with comp_cols[1]:
    p2_name = st.selectbox("Player 2", player_list, index=min(1, len(player_list)-1), key="comp2")

f1, l1 = p1_name.split(" ", 1)
f2, l2 = p2_name.split(" ", 1)
p1_data = team_data[(team_data['first_name']==f1) & (team_data['last_name']==l1)].iloc[0]
p2_data = team_data[(team_data['first_name']==f2) & (team_data['last_name']==l2)].iloc[0]

compare_stats = [
    'ppg','rpg','apg','spg','bpg','topg','mpg','avg_per','avg_usage_rate',
    'avg_game_score','avg_off_rating','avg_def_rating','net_rating',
    'season_fg_pct','season_3pt_pct','season_ts_pct','avg_ast_to',
    'avg_pts_per36','avg_reb_per36','avg_ast_per36',
]
labels = [
    'PPG','RPG','APG','SPG','BPG','TOPG','MPG','PER','USG%',
    'Game Score','ORtg','DRtg','Net Rating',
    'FG%','3PT%','TS%','AST/TO','PTS/36','REB/36','AST/36',
]
# Lower is better for: TOPG, DRtg
lower_better = {'topg', 'avg_def_rating'}

comp_rows = []
for stat, label in zip(compare_stats, labels):
    v1, v2 = p1_data[stat], p2_data[stat]
    is_pct = 'pct' in stat
    v1_str = fmt(v1, pct=is_pct)
    v2_str = fmt(v2, pct=is_pct)
    if pd.notna(v1) and pd.notna(v2):
        if stat in lower_better:
            winner = "◀" if v1 < v2 else ("▶" if v2 < v1 else "—")
        else:
            winner = "◀" if v1 > v2 else ("▶" if v2 > v1 else "—")
    else:
        winner = ""
    comp_rows.append({"Stat": label, p1_name: v1_str, " ": winner, p2_name: v2_str})

comp_df = pd.DataFrame(comp_rows)
st.dataframe(comp_df, use_container_width=True, hide_index=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.8rem; padding: 10px;">
    AAU Basketball Analytics — Powered by Analytics207 🏀
</div>
""", unsafe_allow_html=True)
