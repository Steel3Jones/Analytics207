# pages/coach_dashboard.py
# ─────────────────────────────────────────────────────────────
# COACH PRIVATE DASHBOARD
# Place this file in your pages/ folder alongside your other
# Streamlit pages. It will appear in your sidebar automatically.
#
# pip install supabase anthropic plotly pandas
# ─────────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import anthropic
import base64
import json
import re
from datetime import datetime
from auth import get_user, get_supabase

supabase = get_supabase()

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Coach Dashboard",
    page_icon="🏀",
    layout="wide"
)

# ── Custom CSS to blend with your existing site ───────────────
st.markdown("""
<style>
  /* Metric cards */
  .metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
  }
  .metric-val {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
  }
  .metric-label {
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.45;
  }
  .win  { color: #4ade80; }
  .loss { color: #f87171; }
  .gold { color: #f0a500; }

  /* Review flag */
  .review-badge {
    background: rgba(251,191,36,0.15);
    border: 1px solid rgba(251,191,36,0.4);
    color: #fbbf24;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
  }

  /* Section headers */
  .section-title {
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    opacity: 0.4;
    margin-bottom: 8px;
  }

  /* Hide default Streamlit top padding */
  .block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Auth helpers ──────────────────────────────────────────────
def get_current_coach():
    """Fetch the verified coach record for the logged-in user."""
    user = get_user()
    if not user:
        return None
    user_id = user.id
    result = supabase.table("coaches") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("verified", True) \
        .execute()
    return result.data[0] if result.data else None


# ── Data loaders ──────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_teams(coach_id: str):
    result = supabase.table("teams") \
        .select("*") \
        .eq("coach_id", coach_id) \
        .order("season", desc=True) \
        .execute()
    return result.data or []


@st.cache_data(ttl=30)
def load_player_metrics(team_id: str):
    result = supabase.table("player_advanced_metrics") \
        .select("*") \
        .eq("team_id", team_id) \
        .execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame()


@st.cache_data(ttl=30)
def load_games(team_id: str):
    result = supabase.table("games") \
        .select("*") \
        .eq("team_id", team_id) \
        .order("game_date", desc=True) \
        .execute()
    return result.data or []


@st.cache_data(ttl=30)
def load_game_stats(team_id: str):
    """All per-game stats for every player on this team."""
    try:
        result = supabase.rpc("get_team_game_stats", {"p_team_id": team_id}).execute()
        if result.data:
            return pd.DataFrame(result.data)
    except Exception:
        pass
    # Fallback: join via Python if RPC not set up yet
    games_res = supabase.table("games").select("id,opponent,game_date").eq("team_id", team_id).execute()
    stats_res  = supabase.table("player_stats").select("*").eq("team_id", team_id).execute()
    players_res = supabase.table("players").select("id,name,jersey_number").eq("team_id", team_id).execute()
    if not stats_res.data:
        return pd.DataFrame()
    df = pd.DataFrame(stats_res.data)
    games_df   = pd.DataFrame(games_res.data).rename(columns={"id": "game_id"})
    players_df = pd.DataFrame(players_res.data).rename(columns={"id": "player_id", "name": "player_name"})
    df = df.merge(games_df, on="game_id", how="left")
    df = df.merge(players_df, on="player_id", how="left")
    return df


# ── Claude extraction ─────────────────────────────────────────
def extract_scorebook(image_bytes: bytes, mime_type: str, existing_players: list) -> dict:
    """Send scorebook image to Claude, return parsed stats dict."""
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    roster_hint = ""
    if existing_players:
        names = ", ".join([f"#{p.get('jersey_number','?')} {p['name']}" for p in existing_players])
        roster_hint = f"Known roster: {names}"
    else:
        roster_hint = "No existing roster — create players from scorebook."

    prompt = f"""Extract basketball statistics from this scorebook image.
{roster_hint}

Return ONLY valid JSON, no markdown or explanation:
{{
  "team_score": number | null,
  "opponent_score": number | null,
  "overall_confidence": float (0-1),
  "notes": "string",
  "players": [
    {{
      "name": "string",
      "jersey_number": "string",
      "minutes_played": number | null,
      "points": number,
      "rebounds": number,
      "offensive_reb": number,
      "defensive_reb": number,
      "assists": number,
      "steals": number,
      "blocks": number,
      "turnovers": number,
      "fouls": number,
      "fg_made": number,
      "fg_attempted": number,
      "three_made": number,
      "three_attempted": number,
      "ft_made": number,
      "ft_attempted": number,
      "confidence": float (0-1)
    }}
  ]
}}
Use 0 for illegible stats. Flag confidence < 0.75 for review."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                    "media_type": mime_type, "data": b64}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    raw = response.content[0].text
    clean = re.sub(r"```json|```", "", raw).strip()
    return json.loads(clean)


def save_extracted_stats(game_id: str, team_id: str, extracted: dict, existing_players: list):
    """Write extracted stats to Supabase, create players if needed."""
    # Update game scores
    if extracted.get("team_score") is not None:
        supabase.table("games").update({
            "team_score": extracted["team_score"],
            "opponent_score": extracted["opponent_score"],
            "processed": True
        }).eq("id", game_id).execute()

    player_map = {p["name"].lower(): p for p in existing_players}
    player_map.update({str(p.get("jersey_number","")): p for p in existing_players})

    for pd_row in extracted.get("players", []):
        # Match or create player
        player = (player_map.get(pd_row["name"].lower()) or
                  player_map.get(str(pd_row.get("jersey_number", ""))))

        if not player:
            res = supabase.table("players").insert({
                "team_id": team_id,
                "name": pd_row["name"],
                "jersey_number": str(pd_row.get("jersey_number", "")),
            }).execute()
            player = res.data[0] if res.data else {"id": None}

        if not player.get("id"):
            continue

        supabase.table("player_stats").upsert({
            "game_id":        game_id,
            "player_id":      player["id"],
            "team_id":        team_id,
            "minutes_played": pd_row.get("minutes_played"),
            "points":         pd_row.get("points", 0),
            "rebounds":       pd_row.get("rebounds", 0),
            "offensive_reb":  pd_row.get("offensive_reb", 0),
            "defensive_reb":  pd_row.get("defensive_reb", 0),
            "assists":        pd_row.get("assists", 0),
            "steals":         pd_row.get("steals", 0),
            "blocks":         pd_row.get("blocks", 0),
            "turnovers":      pd_row.get("turnovers", 0),
            "fouls":          pd_row.get("fouls", 0),
            "fg_made":        pd_row.get("fg_made", 0),
            "fg_attempted":   pd_row.get("fg_attempted", 0),
            "three_made":     pd_row.get("three_made", 0),
            "three_attempted":pd_row.get("three_attempted", 0),
            "ft_made":        pd_row.get("ft_made", 0),
            "ft_attempted":   pd_row.get("ft_attempted", 0),
            "ai_confidence":  pd_row.get("confidence", 1.0),
            "needs_review":   pd_row.get("confidence", 1.0) < 0.75,
        }, on_conflict="game_id,player_id").execute()


# ══════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════
coach = get_current_coach()

if not coach:
    st.warning("You need a verified coach account to access this page.")
    st.stop()

# ── Sidebar: team selector ────────────────────────────────────
teams = load_teams(coach["id"])

if not teams:
    st.info("No teams found. Ask your admin to set up your team.")
    st.stop()

# ── Page Header ───────────────────────────────────────────────
hdr_left, hdr_right = st.columns([2, 1])
with hdr_left:
    st.markdown(f"## 🏀 {coach['name']}")
    st.caption(coach["school"] + "  ·  Private Dashboard")
with hdr_right:
    team_names = [f"{t['name']} ({t['season']})" for t in teams]
    selected_idx = st.selectbox("Team", range(len(teams)), format_func=lambda i: team_names[i])
    selected_team = teams[selected_idx]
st.divider()

# ── Load data ─────────────────────────────────────────────────
metrics_df  = load_player_metrics(selected_team["id"])
games       = load_games(selected_team["id"])
game_stats  = load_game_stats(selected_team["id"])

wins   = sum(1 for g in games if g.get("team_score") and g["team_score"] > g["opponent_score"])
losses = sum(1 for g in games if g.get("team_score") and g["team_score"] < g["opponent_score"])
logged = sum(1 for g in games if g.get("processed"))

# ── Metrics Banner ────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
avg_ppg = round(metrics_df["ppg"].mean(), 1) if not metrics_df.empty else "—"

with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val">{len(metrics_df) or len(games)}</div>
        <div class="metric-label">Players</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val win">{wins}</div>
        <div class="metric-label">Wins</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val loss">{losses}</div>
        <div class="metric-label">Losses</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val">{logged}</div>
        <div class="metric-label">Games Logged</div></div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-val gold">{avg_ppg}</div>
        <div class="metric-label">Team Avg PPG</div></div>""", unsafe_allow_html=True)

st.write("")

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Player Metrics",
    "📈 Charts",
    "🗓 Game Breakdown",
    "📷 Upload Scorebook"
])


# ══════════════ TAB 1: PLAYER METRICS TABLE ═══════════════════
with tab1:
    if metrics_df.empty:
        st.info("No stats yet. Upload a scorebook in the Upload tab to get started.")
    else:
        st.markdown('<p class="section-title">Season Averages — click any column header to sort</p>',
                    unsafe_allow_html=True)

        sort_col = st.selectbox("Sort by", ["ppg","rpg","apg","spg","bpg","fg_pct","three_pct",
                                             "ft_pct","true_shooting_pct","ast_to_ratio"],
                                 format_func=lambda x: {
                                     "ppg":"PPG","rpg":"RPG","apg":"APG","spg":"SPG","bpg":"BPG",
                                     "fg_pct":"FG%","three_pct":"3P%","ft_pct":"FT%",
                                     "true_shooting_pct":"True Shooting %","ast_to_ratio":"AST/TO"
                                 }[x], label_visibility="collapsed")

        display_df = metrics_df.sort_values(sort_col, ascending=False).copy()
        display_df["#"] = display_df["jersey_number"].apply(lambda x: f"#{x}" if x else "—")

        # Flag needs_review players
        review_ids = []
        if "player_id" in display_df.columns:
            stats_check = supabase.table("player_stats") \
                .select("player_id") \
                .eq("team_id", selected_team["id"]) \
                .eq("needs_review", True) \
                .execute()
            review_ids = [r["player_id"] for r in (stats_check.data or [])]

        cols_to_show = ["#","player_name","games_played","ppg","rpg","apg","spg","bpg",
                        "topg","fg_pct","three_pct","ft_pct","true_shooting_pct","ast_to_ratio"]
        col_labels   = {"#":"#","player_name":"Player","games_played":"GP","ppg":"PPG",
                        "rpg":"RPG","apg":"APG","spg":"SPG","bpg":"BPG","topg":"TO/G",
                        "fg_pct":"FG%","three_pct":"3P%","ft_pct":"FT%",
                        "true_shooting_pct":"TS%","ast_to_ratio":"AST/TO"}

        show_df = display_df[[c for c in cols_to_show if c in display_df.columns]].rename(columns=col_labels)
        st.dataframe(show_df, use_container_width=True, hide_index=True,
                     column_config={
                         "TS%": st.column_config.ProgressColumn("TS%", min_value=0, max_value=100, format="%.1f"),
                         "FG%": st.column_config.ProgressColumn("FG%", min_value=0, max_value=100, format="%.1f"),
                         "3P%": st.column_config.ProgressColumn("3P%", min_value=0, max_value=100, format="%.1f"),
                         "FT%": st.column_config.ProgressColumn("FT%", min_value=0, max_value=100, format="%.1f"),
                         "PPG": st.column_config.NumberColumn("PPG", format="%.1f"),
                     })

        if review_ids:
            st.warning(f"⚠️ {len(set(review_ids))} player(s) have low-confidence stats that need your review.")


# ══════════════ TAB 2: CHARTS ═════════════════════════════════
with tab2:
    if metrics_df.empty:
        st.info("Charts will appear once stats are uploaded.")
    else:
        col_a, col_b = st.columns(2)

        # ── Scoring leaders bar chart
        with col_a:
            st.markdown("**Scoring Leaders**")
            top_scorers = metrics_df.nlargest(10, "ppg")
            fig = go.Figure(go.Bar(
                x=top_scorers["ppg"],
                y=top_scorers["player_name"],
                orientation="h",
                marker_color="#f0a500",
                text=top_scorers["ppg"].apply(lambda x: f"{x:.1f}"),
                textposition="outside",
            ))
            fig.update_layout(
                height=320, margin=dict(l=0, r=30, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, zeroline=False, visible=False),
                yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
                font=dict(color="#ccc"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Shooting efficiency scatter
        with col_b:
            st.markdown("**Scoring vs Efficiency (TS%)**")
            scatter_df = metrics_df.dropna(subset=["ppg","true_shooting_pct"])
            fig2 = px.scatter(
                scatter_df, x="ppg", y="true_shooting_pct",
                text="player_name", size_max=12,
                color="ppg", color_continuous_scale=["#1a3a5c","#f0a500"],
            )
            fig2.update_traces(textposition="top center", textfont_size=10,
                               marker=dict(size=10, line=dict(width=0)))
            fig2.update_layout(
                height=320, margin=dict(l=0, r=0, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="PPG", gridcolor="#1a1a1a", zeroline=False),
                yaxis=dict(title="True Shooting %", gridcolor="#1a1a1a", zeroline=False),
                font=dict(color="#ccc"), showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Radar chart for selected player
        st.markdown("**Player Radar — Advanced Profile**")
        player_names = metrics_df["player_name"].tolist()
        selected_players = st.multiselect("Compare players (max 3)", player_names,
                                           default=player_names[:1] if player_names else [])

        if selected_players:
            radar_cols = ["ppg","rpg","apg","spg","bpg","true_shooting_pct"]
            radar_labels = ["PPG","RPG","APG","SPG","BPG","TS%"]
            fig3 = go.Figure()
            colors = ["#f0a500", "#4ade80", "#60a5fa"]

            for i, pname in enumerate(selected_players[:3]):
                row = metrics_df[metrics_df["player_name"] == pname].iloc[0]
                # Normalize each stat to 0-100 scale relative to team max
                vals = []
                for col in radar_cols:
                    team_max = metrics_df[col].max()
                    vals.append(round((row[col] / team_max * 100) if team_max > 0 else 0, 1))
                vals.append(vals[0])  # close the polygon

                fig3.add_trace(go.Scatterpolar(
                    r=vals, theta=radar_labels + [radar_labels[0]],
                    fill="toself", name=pname,
                    line_color=colors[i],
                    fillcolor=colors[i].replace("#", "rgba(").replace(")", ",0.15)") if False else colors[i],
                    opacity=0.8,
                ))

            fig3.update_layout(
                height=380,
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100],
                                    gridcolor="#1a1a1a", tickfont=dict(color="#444")),
                    angularaxis=dict(gridcolor="#1a1a1a"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccc"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=40, r=40, t=20, b=20),
            )
            st.plotly_chart(fig3, use_container_width=True)


# ══════════════ TAB 3: GAME BREAKDOWN ═════════════════════════
with tab3:
    if not games:
        st.info("No games logged yet.")
    else:
        game_options = {g["id"]: f"{g['game_date']}  vs  {g['opponent']}" for g in games}
        selected_game_id = st.selectbox("Select a game", list(game_options.keys()),
                                         format_func=lambda x: game_options[x])
        selected_game = next(g for g in games if g["id"] == selected_game_id)

        # Score header
        if selected_game.get("team_score") is not None:
            col_home, col_vs, col_away = st.columns([2,1,2])
            with col_home:
                won = selected_game["team_score"] > selected_game["opponent_score"]
                color = "#4ade80" if won else "#f87171"
                st.markdown(f"""<div style="text-align:center">
                    <div style="font-size:3rem;font-weight:800;color:{color}">{selected_game['team_score']}</div>
                    <div style="opacity:.4;font-size:.8rem;letter-spacing:.1em">YOUR TEAM</div>
                </div>""", unsafe_allow_html=True)
            with col_vs:
                st.markdown('<div style="text-align:center;font-size:1.5rem;opacity:.3;padding-top:1rem">VS</div>',
                            unsafe_allow_html=True)
            with col_away:
                st.markdown(f"""<div style="text-align:center">
                    <div style="font-size:3rem;font-weight:800;color:{'#f87171' if won else '#4ade80'}">{selected_game['opponent_score']}</div>
                    <div style="opacity:.4;font-size:.8rem;letter-spacing:.1em">{selected_game['opponent'].upper()}</div>
                </div>""", unsafe_allow_html=True)
            st.write("")

        # Per-game player stats
        if not game_stats.empty and "game_id" in game_stats.columns:
            this_game = game_stats[game_stats["game_id"] == selected_game_id].copy()
            if not this_game.empty:
                show_cols = ["player_name","points","rebounds","assists","steals","blocks",
                             "turnovers","fg_made","fg_attempted","three_made","three_attempted",
                             "ft_made","ft_attempted","ai_confidence"]
                existing = [c for c in show_cols if c in this_game.columns]
                display = this_game[existing].rename(columns={
                    "player_name":"Player","points":"PTS","rebounds":"REB","assists":"AST",
                    "steals":"STL","blocks":"BLK","turnovers":"TO",
                    "fg_made":"FGM","fg_attempted":"FGA",
                    "three_made":"3PM","three_attempted":"3PA",
                    "ft_made":"FTM","ft_attempted":"FTA",
                    "ai_confidence":"AI Conf"
                })
                st.dataframe(display.sort_values("PTS", ascending=False),
                             use_container_width=True, hide_index=True,
                             column_config={
                                 "AI Conf": st.column_config.ProgressColumn(
                                     "AI Conf", min_value=0, max_value=1, format="%.2f")
                             })

                # Top performers
                st.markdown("**Top Performers**")
                tp1, tp2, tp3 = st.columns(3)
                top_pts = this_game.loc[this_game["points"].idxmax()]
                top_reb = this_game.loc[this_game["rebounds"].idxmax()]
                top_ast = this_game.loc[this_game["assists"].idxmax()]
                with tp1:
                    st.metric("Leading Scorer", top_pts.get("player_name","—"), f"{int(top_pts['points'])} pts")
                with tp2:
                    st.metric("Top Rebounder", top_reb.get("player_name","—"), f"{int(top_reb['rebounds'])} reb")
                with tp3:
                    st.metric("Assists Leader", top_ast.get("player_name","—"), f"{int(top_ast['assists'])} ast")
            else:
                st.info("No player stats logged for this game yet. Upload the scorebook below.")
        else:
            st.info("Upload a scorebook to see this game's player breakdown.")


# ══════════════ TAB 4: UPLOAD SCOREBOOK ═══════════════════════
with tab4:
    st.markdown("Upload a photo of your scorebook and AI will read the stats automatically.")
    st.write("")

    unprocessed = [g for g in games if not g.get("processed")]
    all_games_labeled = {g["id"]: f"{g['game_date']}  vs  {g['opponent']}" for g in games}

    upload_game_id = st.selectbox(
        "Which game is this scorebook for?",
        list(all_games_labeled.keys()),
        format_func=lambda x: all_games_labeled[x]
    )

    uploaded_file = st.file_uploader(
        "Scorebook photo",
        type=["jpg","jpeg","png","webp"],
        help="Clear, well-lit photos give the best results. Landscape orientation works best."
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Preview — does this look clear and readable?", width=500)

        col_up, col_cancel = st.columns([1, 3])
        with col_up:
            if st.button("🤖 Extract Stats", type="primary", use_container_width=True):
                with st.spinner("Claude is reading your scorebook..."):
                    try:
                        # Load existing players for this team
                        players_res = supabase.table("players") \
                            .select("id,name,jersey_number") \
                            .eq("team_id", selected_team["id"]) \
                            .execute()
                        existing_players = players_res.data or []

                        # Call Claude
                        image_bytes = uploaded_file.read()
                        mime_type   = uploaded_file.type or "image/jpeg"
                        extracted   = extract_scorebook(image_bytes, mime_type, existing_players)

                        # Save to DB
                        save_extracted_stats(upload_game_id, selected_team["id"],
                                             extracted, existing_players)

                        # Upload image to Supabase Storage
                        img_path = f"{coach['id']}/{upload_game_id}/{uploaded_file.name}"
                        supabase.storage.from_("scorebooks").upload(
                            img_path, image_bytes,
                            file_options={"content-type": mime_type, "upsert": "true"}
                        )
                        supabase.table("games").update(
                            {"scorebook_image": img_path}
                        ).eq("id", upload_game_id).execute()

                        # Clear cache so tables refresh
                        load_player_metrics.clear()
                        load_games.clear()
                        load_game_stats.clear()

                        # Show result
                        conf = extracted.get("overall_confidence", 1.0)
                        players_found = len(extracted.get("players", []))
                        needs_review  = sum(1 for p in extracted.get("players",[])
                                           if p.get("confidence", 1.0) < 0.75)

                        if conf >= 0.85 and needs_review == 0:
                            st.success(f"✅ Successfully extracted {players_found} players. All stats look good!")
                        else:
                            st.warning(
                                f"Extracted {players_found} players. "
                                f"{'⚠️ ' + str(needs_review) + ' rows flagged for review — check the Player Metrics tab.' if needs_review else ''}"
                                f"\nImage confidence: {conf:.0%}"
                            )
                        if extracted.get("notes"):
                            st.caption(f"AI note: {extracted['notes']}")

                    except json.JSONDecodeError:
                        st.error("Could not parse Claude's response. Try a clearer photo.")
                    except Exception as e:
                        st.error(f"Something went wrong: {e}")

    st.divider()
    st.markdown("**Tips for best results**")
    st.markdown("""
- 📸 Take the photo straight-on, not at an angle
- 💡 Make sure the scorebook is well-lit with no shadows
- 🔍 All columns and player names should be clearly visible
- 📄 One page at a time — don't try to capture two pages at once
    """)
