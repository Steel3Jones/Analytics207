import streamlit as st
import pandas as pd
from pathlib import Path
import os

# ============================================================
# AAU BASKETBALL — Stat Leaders
# Location: C:\ANALYTICS207\pages\aau_leaders.py
# ============================================================

st.set_page_config(page_title="AAU Stat Leaders", page_icon="👑", layout="wide")

# Root/data config (aligned with main app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT    = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "aau" / "data"))
AAU_SUMMARY_PATH = DATA_ROOT / "aau_player_season_summary.parquet"

# --- Custom CSS ---
st.markdown("""
<style>
    .leader-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 14px;
        padding: 20px 16px;
        text-align: center;
        margin-bottom: 10px;
        position: relative;
        overflow: hidden;
    }
    .leader-card-gold {
        border: 2px solid #ffd700;
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.15);
    }
    .leader-card-silver {
        border: 2px solid #c0c0c0;
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.1);
    }
    .leader-card-bronze {
        border: 2px solid #cd7f32;
        box-shadow: 0 0 15px rgba(205, 127, 50, 0.1);
    }
    .leader-rank {
        position: absolute;
        top: 8px;
        left: 12px;
        font-size: 1.4rem;
    }
    .leader-jersey {
        font-size: 2.8rem;
        font-weight: 900;
        color: #e94560;
        opacity: 0.2;
        margin-bottom: -15px;
    }
    .leader-name {
        font-size: 1.2rem;
        font-weight: 800;
        color: #fff;
        margin: 4px 0 2px 0;
    }
    .leader-info {
        font-size: 0.75rem;
        color: #8892b0;
        margin-bottom: 8px;
    }
    .leader-stat {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 6px 0;
        line-height: 1;
    }
    .leader-stat-gold { color: #ffd700; }
    .leader-stat-silver { color: #c0c0c0; }
    .leader-stat-bronze { color: #cd7f32; }
    .leader-label {
        font-size: 0.65rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .category-header {
        background: linear-gradient(90deg, #e94560 0%, transparent 100%);
        padding: 8px 16px;
        border-radius: 6px;
        margin: 24px 0 14px 0;
        font-size: 1rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 1px;
    }
    .honorable-mention {
        background: #1a1a2e;
        border-radius: 8px;
        padding: 8px 14px;
        margin: 4px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 3px solid #333;
    }
    .hm-name { color: #ccc; font-weight: 600; font-size: 0.85rem; }
    .hm-stat { color: #e94560; font-weight: 800; font-size: 1rem; }
    .hm-rank { color: #555; font-weight: 700; font-size: 0.8rem; min-width: 25px; }
</style>
""", unsafe_allow_html=True)

def leader_card(rank, player, stat_val, stat_label, fmt_str=".1f", is_pct=False):
    medal = ["🥇", "🥈", "🥉"][rank-1]
    border = ["leader-card-gold", "leader-card-silver", "leader-card-bronze"][rank-1]
    stat_color = ["leader-stat-gold", "leader-stat-silver", "leader-stat-bronze"][rank-1]
    if is_pct:
        val_str = f"{stat_val:.1%}" if pd.notna(stat_val) else "—"
    else:
        val_str = f"{stat_val:{fmt_str}}" if pd.notna(stat_val) else "—"
    return f'''<div class="leader-card {border}">
        <div class="leader-rank">{medal}</div>
        <div class="leader-jersey">#{int(player['jersey_number'])}</div>
        <div class="leader-name">{player['first_name']} {player['last_name']}</div>
        <div class="leader-info">{player['position']} | Class of {int(player['grad_class'])} | {player['high_school']}</div>
        <div class="leader-stat {stat_color}">{val_str}</div>
        <div class="leader-label">{stat_label}</div>
    </div>'''

def honorable_mentions(df, stat_col, start_rank=4, fmt_str=".1f", is_pct=False):
    html = ""
    for i, (_, row) in enumerate(df.iterrows()):
        val = row[stat_col]
        if is_pct:
            val_str = f"{val:.1%}" if pd.notna(val) else "—"
        else:
            val_str = f"{val:{fmt_str}}" if pd.notna(val) else "—"
        html += f'''<div class="honorable-mention">
            <span class="hm-rank">{start_rank + i}.</span>
            <span class="hm-name">{row['first_name']} {row['last_name']} <span style="color:#555;">({row['position']})</span></span>
            <span class="hm-stat">{val_str}</span>
        </div>'''
    return html

def render_category(data, stat_col, category_label, emoji, fmt_str=".1f", is_pct=False, ascending=False):
    sorted_df = data.sort_values(stat_col, ascending=ascending).reset_index(drop=True)
    st.markdown(f'<div class="category-header">{emoji} {category_label}</div>', unsafe_allow_html=True)

    # Top 3 podium
    cols = st.columns(3)
    for i in range(min(3, len(sorted_df))):
        player = sorted_df.iloc[i]
        with cols[i]:
            st.markdown(
                leader_card(i+1, player, player[stat_col], category_label, fmt_str, is_pct),
                unsafe_allow_html=True,
            )

    # Honorable mentions (4th onward)
    if len(sorted_df) > 3:
        with st.expander(f"Full rankings ({len(sorted_df)} players)"):
            st.markdown(
                honorable_mentions(sorted_df.iloc[3:], stat_col, 4, fmt_str, is_pct),
                unsafe_allow_html=True,
            )

@st.cache_data
def load_data():
    return pd.read_parquet(AAU_SUMMARY_PATH)

summary = load_data()

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div style="text-align:center; padding: 0.5rem 0;">
    <h1 style="margin:0; font-size:2.8rem; font-weight:900; letter-spacing:-1px;">
        👑 STAT LEADERS
    </h1>
    <p style="margin:0; font-size:1rem; color:#ffd700; letter-spacing:4px; font-weight:600;">
        AAU BASKETBALL — WHO RUNS THE FLOOR
    </p>
</div>
""", unsafe_allow_html=True)

# --- Team selector ---
teams = summary['aau_team'].dropna().unique().tolist()
if len(teams) > 1:
    teams = ["All Teams"] + teams
    selected_team = st.selectbox("Filter by Team", teams, index=0)
    if selected_team == "All Teams":
        data = summary.copy()
    else:
        data = summary[summary['aau_team'] == selected_team].copy()
else:
    data = summary.copy()
    st.markdown(f"**{teams[0]}** — {len(data)} Players")

# --- Min games filter ---
max_gp = int(data['games_played'].max()) if len(data) > 0 else 1
if max_gp > 1:
    min_games = st.slider("Minimum Games Played", 1, max_gp, 1)
    data = data[data['games_played'] >= min_games]

st.markdown(
    f"<p style='color:#888; font-size:0.8rem; text-align:center;'>{len(data)} players qualified</p>",
    unsafe_allow_html=True,
)

# ============================================================
# SCORING
# ============================================================
render_category(data, 'ppg', 'POINTS PER GAME', '🔥')
render_category(data, 'season_ts_pct', 'TRUE SHOOTING %', '🎯', is_pct=True)

# ============================================================
# REBOUNDING
# ============================================================
render_category(data, 'rpg', 'REBOUNDS PER GAME', '💪')

# ============================================================
# PLAYMAKING
# ============================================================
render_category(data, 'apg', 'ASSISTS PER GAME', '🎯')
render_category(data, 'avg_ast_to', 'ASSIST-TO-TURNOVER RATIO', '🧠', fmt_str=".2f")

# ============================================================
# DEFENSE
# ============================================================
render_category(data, 'spg', 'STEALS PER GAME', '🔒')
render_category(data, 'bpg', 'BLOCKS PER GAME', '🚫')

# ============================================================
# ADVANCED
# ============================================================
render_category(data, 'avg_per', 'PLAYER EFFICIENCY RATING', '📊')
render_category(data, 'avg_usage_rate', 'USAGE RATE', '⚡')
render_category(data, 'avg_off_rating', 'OFFENSIVE RATING', '💰')
render_category(data, 'avg_def_rating', 'DEFENSIVE RATING', '🛡️', ascending=True)
render_category(data, 'net_rating', 'NET RATING', '📈')
render_category(data, 'avg_game_score', 'GAME SCORE', '🏅')

# ============================================================
# SHOOTING
# ============================================================
render_category(data, 'season_fg_pct', 'FIELD GOAL %', '🏀', is_pct=True)
render_category(data, 'season_3pt_pct', 'THREE-POINT %', '☄️', is_pct=True)
render_category(data, 'season_ft_pct', 'FREE THROW %', '✅', is_pct=True)

# ============================================================
# PACE-ADJUSTED
# ============================================================
render_category(data, 'avg_pts_per36', 'POINTS PER 36 MIN', '⏱️')
render_category(data, 'avg_reb_per36', 'REBOUNDS PER 36 MIN', '⏱️')
render_category(data, 'avg_ast_per36', 'ASSISTS PER 36 MIN', '⏱️')

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.8rem; padding: 10px;">
    AAU Basketball Stat Leaders — Powered by Analytics207 🏀
</div>
""", unsafe_allow_html=True)
