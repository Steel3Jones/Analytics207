import streamlit as st
import pandas as pd
from pathlib import Path
import os
import urllib.parse

# ============================================================
# AAU BASKETBALL — Recruiting Profile
# Location: C:\ANALYTICS207\pages\aau_recruiting.py
# ============================================================

st.set_page_config(page_title="AAU Recruiting Profile", page_icon="🎓", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT    = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "aau" / "data"))
SUMMARY_PATH = DATA_ROOT / "aau_player_season_summary.parquet"
GAMES_PATH   = DATA_ROOT / "aau_game_stats_advanced.parquet"

# --- Custom CSS ---
st.markdown("""
<style>
    .recruit-hero {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        border: 1px solid #444;
        margin-bottom: 16px;
        position: relative;
    }
    .recruit-hero .big-number {
        font-size: 5rem;
        font-weight: 900;
        color: #e94560;
        opacity: 0.15;
        margin-bottom: -40px;
        line-height: 1;
    }
    .recruit-hero .player-name {
        font-size: 2.4rem;
        font-weight: 900;
        color: #fff;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .recruit-hero .player-tagline {
        font-size: 1rem;
        color: #ffd700;
        font-weight: 600;
        letter-spacing: 2px;
        margin: 4px 0 8px 0;
    }
    .recruit-hero .player-bio {
        font-size: 0.9rem;
        color: #a0aec0;
        line-height: 1.6;
    }

    .recruit-stat-row {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 16px 12px;
        text-align: center;
        margin-bottom: 6px;
    }
    .recruit-stat-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #fff;
        line-height: 1;
    }
    .recruit-stat-label {
        font-size: 0.6rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 4px;
    }

    .section-bar {
        background: linear-gradient(90deg, #e94560 0%, transparent 100%);
        padding: 6px 14px;
        border-radius: 4px;
        margin: 18px 0 10px 0;
        font-size: 0.85rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 1px;
    }

    .tier-badge-lg {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 800;
        color: #fff;
        letter-spacing: 2px;
        margin-top: 8px;
    }
    .tier-elite { background: linear-gradient(135deg, #ffd700, #ff8c00); }
    .tier-star { background: linear-gradient(135deg, #a855f7, #6366f1); }
    .tier-starter { background: linear-gradient(135deg, #0095ff, #00d4ff); }
    .tier-rotation { background: linear-gradient(135deg, #4a5568, #718096); }

    .highlight-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
        border: 1px solid #e94560;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .highlight-box a {
        color: #e94560;
        font-weight: 700;
        font-size: 1.1rem;
        text-decoration: none;
    }

    .strengths-item {
        background: #1a1a2e;
        border-left: 4px solid #00d4aa;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        color: #ccc;
        font-size: 0.9rem;
    }
    .growth-item {
        background: #1a1a2e;
        border-left: 4px solid #ffa500;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        color: #ccc;
        font-size: 0.9rem;
    }

    .contact-card {
        background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #333;
        text-align: center;
    }
    .contact-card .contact-label {
        font-size: 0.7rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .contact-card .contact-value {
        font-size: 1rem;
        color: #fff;
        font-weight: 600;
    }

    @media print {
        .stApp header, .stSidebar, .stToolbar, footer { display: none !important; }
        .recruit-hero { break-inside: avoid; }
    }
</style>
""", unsafe_allow_html=True)

def stat_box(label, value):
    return f'''<div class="recruit-stat-row">
        <div class="recruit-stat-value">{value}</div>
        <div class="recruit-stat-label">{label}</div>
    </div>'''

def per_tier_badge(per_val):
    if pd.isna(per_val): return ""
    if per_val >= 25: return f'<span class="tier-badge-lg tier-elite">⭐ ELITE — PER {per_val:.1f}</span>'
    if per_val >= 20: return f'<span class="tier-badge-lg tier-star">🌟 ALL-STAR — PER {per_val:.1f}</span>'
    if per_val >= 15: return f'<span class="tier-badge-lg tier-starter">🏀 STARTER — PER {per_val:.1f}</span>'
    return f'<span class="tier-badge-lg tier-rotation">💪 ROTATION — PER {per_val:.1f}</span>'

def fmt(val, fmt_str=".1f", pct=False):
    if pd.isna(val): return "—"
    if pct: return f"{val:.1%}"
    return f"{val:{fmt_str}}"

def auto_strengths(player):
    strengths = []
    if pd.notna(player['ppg']) and player['ppg'] >= 15:
        strengths.append("Elite scorer — generates consistent offense at a high volume")
    elif pd.notna(player['ppg']) and player['ppg'] >= 10:
        strengths.append("Reliable scoring option with ability to fill it up on any given night")
    if pd.notna(player['apg']) and player['apg'] >= 5:
        strengths.append("True floor general — sees the court and creates for teammates at a high rate")
    elif pd.notna(player['apg']) and player['apg'] >= 3:
        strengths.append("Good court vision with willingness to make the extra pass")
    if pd.notna(player['rpg']) and player['rpg'] >= 7:
        strengths.append("Dominant rebounder who controls the glass on both ends")
    elif pd.notna(player['rpg']) and player['rpg'] >= 5:
        strengths.append("Active on the boards — crashes hard and cleans up possessions")
    if pd.notna(player['spg']) and player['spg'] >= 2:
        strengths.append("Disruptive defender with active hands and quick anticipation")
    if pd.notna(player['bpg']) and player['bpg'] >= 1.5:
        strengths.append("Rim protector who alters shots and anchors the defense")
    if pd.notna(player['season_ts_pct']) and player['season_ts_pct'] >= 0.55:
        strengths.append("Highly efficient scorer — converts at an elite true shooting percentage")
    if pd.notna(player['avg_ast_to']) and player['avg_ast_to'] >= 2.5:
        strengths.append("Takes care of the ball — excellent assist-to-turnover ratio")
    if pd.notna(player['avg_usage_rate']) and player['avg_usage_rate'] >= 25:
        strengths.append("Trusted with heavy usage — team leans on them in clutch moments")
    return strengths if strengths else ["Developing player with a solid foundation and upside"]

def auto_growth(player):
    areas = []
    if pd.notna(player['season_3pt_pct']) and player['season_3pt_pct'] < 0.30:
        areas.append("Expanding three-point range and shot consistency from beyond the arc")
    if pd.notna(player['season_ft_pct']) and player['season_ft_pct'] < 0.65:
        areas.append("Free throw consistency — an area of focus for continued development")
    if pd.notna(player['topg']) and player['topg'] >= 3:
        areas.append("Ball security and reducing live-ball turnovers under pressure")
    if pd.notna(player['avg_ast_to']) and player['avg_ast_to'] < 1.0:
        areas.append("Improving decision-making and playmaking for teammates")
    return areas if areas else ["Continuing to round out an already strong all-around game"]

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
<div style="text-align:center; padding: 0.5rem 0 0.2rem 0;">
    <h1 style="margin:0; font-size:2.4rem; font-weight:900; letter-spacing:-1px;">
        🎓 RECRUITING PROFILE
    </h1>
    <p style="margin:0; font-size:0.9rem; color:#e94560; letter-spacing:4px; font-weight:600;">
        AAU BASKETBALL — PLAYER INTELLIGENCE FOR COLLEGE COACHES
    </p>
</div>
""", unsafe_allow_html=True)

# --- Player selector ---
player_list = summary.apply(lambda r: f"{r['first_name']} {r['last_name']}", axis=1).tolist()
selected = st.selectbox("Select Player", player_list)
first, last = selected.split(" ", 1)
player = summary[(summary['first_name'] == first) & (summary['last_name'] == last)].iloc[0]
player_games = games[games['player_id'] == player['player_id']].sort_values('date')

# ============================================================
# HERO CARD
# ============================================================
st.markdown(f'''
<div class="recruit-hero">
    <div class="big-number">#{int(player['jersey_number'])}</div>
    <div class="player-name">{player['first_name'].upper()} {player['last_name'].upper()}</div>
    <div class="player-tagline">{player['aau_team'].upper()}</div>
    <div class="player-bio">
        {player['position']} | Class of {int(player['grad_class'])} | {player['height']} | {int(player['weight'])} lbs<br>
        {player['high_school']} — {player['hometown']}
    </div>
    <div>{per_tier_badge(player['avg_per'])}</div>
</div>
''', unsafe_allow_html=True)

# ============================================================
# SEASON AVERAGES
# ============================================================
st.markdown('<div class="section-bar">📈 SEASON AVERAGES</div>', unsafe_allow_html=True)
c = st.columns(8)
c[0].markdown(stat_box("PPG", fmt(player['ppg'])), unsafe_allow_html=True)
c[1].markdown(stat_box("RPG", fmt(player['rpg'])), unsafe_allow_html=True)
c[2].markdown(stat_box("APG", fmt(player['apg'])), unsafe_allow_html=True)
c[3].markdown(stat_box("SPG", fmt(player['spg'])), unsafe_allow_html=True)
c[4].markdown(stat_box("BPG", fmt(player['bpg'])), unsafe_allow_html=True)
c[5].markdown(stat_box("MPG", fmt(player['mpg'])), unsafe_allow_html=True)
c[6].markdown(stat_box("GP", int(player['games_played'])), unsafe_allow_html=True)
c[7].markdown(stat_box("REC", f"{int(player['wins'])}-{int(player['losses'])}"), unsafe_allow_html=True)

# ============================================================
# SHOOTING & EFFICIENCY
# ============================================================
st.markdown('<div class="section-bar">🎯 SHOOTING & EFFICIENCY</div>', unsafe_allow_html=True)
s = st.columns(8)
s[0].markdown(stat_box("FG%", fmt(player['season_fg_pct'], pct=True)), unsafe_allow_html=True)
s[1].markdown(stat_box("3PT%", fmt(player['season_3pt_pct'], pct=True)), unsafe_allow_html=True)
s[2].markdown(stat_box("FT%", fmt(player['season_ft_pct'], pct=True)), unsafe_allow_html=True)
s[3].markdown(stat_box("TS%", fmt(player['season_ts_pct'], pct=True)), unsafe_allow_html=True)
s[4].markdown(stat_box("PER", fmt(player['avg_per'])), unsafe_allow_html=True)
s[5].markdown(stat_box("USG%", fmt(player['avg_usage_rate'])), unsafe_allow_html=True)
s[6].markdown(stat_box("ORtg", fmt(player['avg_off_rating'])), unsafe_allow_html=True)
s[7].markdown(stat_box("AST/TO", fmt(player['avg_ast_to'], '.2f')), unsafe_allow_html=True)

# ============================================================
# SCOUTING REPORT (auto-generated)
# ============================================================
st.markdown('<div class="section-bar">🔍 SCOUTING REPORT</div>', unsafe_allow_html=True)

col_l, col_r = st.columns(2)

with col_l:
    st.markdown("**Strengths**")
    for s_item in auto_strengths(player):
        st.markdown(f'<div class="strengths-item">✅ {s_item}</div>', unsafe_allow_html=True)

with col_r:
    st.markdown("**Development Areas**")
    for g_item in auto_growth(player):
        st.markdown(f'<div class="growth-item">📈 {g_item}</div>', unsafe_allow_html=True)

# ============================================================
# CAREER HIGHS
# ============================================================
st.markdown('<div class="section-bar">🏆 CAREER HIGHS</div>', unsafe_allow_html=True)
ch = st.columns(6)
ch[0].markdown(stat_box("PTS", int(player['pts_high'])), unsafe_allow_html=True)
ch[1].markdown(stat_box("REB", int(player['reb_high'])), unsafe_allow_html=True)
ch[2].markdown(stat_box("AST", int(player['ast_high'])), unsafe_allow_html=True)
ch[3].markdown(stat_box("STL", int(player['stl_high'])), unsafe_allow_html=True)
ch[4].markdown(stat_box("BLK", int(player['blk_high'])), unsafe_allow_html=True)
ch[5].markdown(stat_box("GMSCORE", fmt(player['game_score_high'])), unsafe_allow_html=True)

# ============================================================
# HIGHLIGHT VIDEO
# ============================================================
st.markdown('<div class="section-bar">🎥 HIGHLIGHT VIDEO</div>', unsafe_allow_html=True)
if pd.notna(player.get('highlight_video_url')) and str(player['highlight_video_url']).startswith('http'):
    st.video(player['highlight_video_url'])
else:
    st.markdown('<div class="highlight-box"><p style="color:#888; margin:0;">No highlight video uploaded yet</p></div>', unsafe_allow_html=True)

# ============================================================
# GAME LOG
# ============================================================
st.markdown('<div class="section-bar">📋 GAME LOG</div>', unsafe_allow_html=True)

gamelog = player_games[[
    'date','opponent','tournament','result','min','pts','reb','ast','stl','blk','tov',
    'fg_pct','ts_pct','per','game_score'
]].copy()

gamelog['result'] = player_games.apply(
    lambda r: f"{'W' if r['result']=='W' else 'L'} {int(r['team_score'])}-{int(r['opp_score'])}", axis=1)

for col in ['fg_pct','ts_pct']:
    gamelog[col] = gamelog[col].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—")
for col in ['per','game_score']:
    gamelog[col] = gamelog[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

gamelog.columns = [
    'Date','Opponent','Tournament','Result','MIN','PTS','REB','AST','STL','BLK','TOV',
    'FG%','TS%','PER','GmScore'
]

st.dataframe(gamelog.reset_index(drop=True), use_container_width=True, hide_index=True)

# ============================================================
# SHAREABLE LINK & PRINT
# ============================================================
st.markdown('<div class="section-bar">📤 SHARE THIS PROFILE</div>', unsafe_allow_html=True)

col_share1, col_share2 = st.columns(2)
with col_share1:
    st.markdown("""
    **For College Coaches:**  
    Use your browser's **Print → Save as PDF** (Ctrl+P) to generate  
    a clean one-page recruiting sheet to email or hand out at showcases.
    """)
with col_share2:
    st.markdown(f"""
    **Player Details:**  
    {player['first_name']} {player['last_name']} | #{int(player['jersey_number'])}  
    {player['aau_team']} | Class of {int(player['grad_class'])}  
    {player['position']} | {player['height']} | {int(player['weight'])} lbs  
    {player['high_school']} — {player['hometown']}
    """)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.8rem; padding: 10px;">
    AAU Recruiting Profiles — Powered by Analytics207 🏀🎓
</div>
""", unsafe_allow_html=True)
