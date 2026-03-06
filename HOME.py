import streamlit as st
from sidebar_auth import render_sidebar_auth
from auth import logout_button

st.set_page_config(
    page_title="Analytics207 — Choose Your Sport",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_sidebar_auth()
logout_button()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&display=swap');

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
.block-container { padding: 2rem 2rem 0 2rem !important; }

body, .stApp {
    background: #020617 !important;
}

/* Grid background */
.stApp::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none; z-index: 0;
}

.wheel-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 85vh;
    font-family: 'Barlow', sans-serif;
}

.wheel-eyebrow {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem; letter-spacing: 0.25em;
    text-transform: uppercase; color: #fbbf24;
    text-align: center; margin-bottom: 0.3rem;
}
.wheel-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3.2rem; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.03em;
    color: #f8fafc; line-height: 1; text-align: center;
}
.wheel-title span {
    background: linear-gradient(135deg, #fbbf24, #fb7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.wheel-sub {
    font-size: 0.88rem; color: #475569;
    margin-top: 0.3rem; text-align: center;
    letter-spacing: 0.04em; margin-bottom: 2.5rem;
}

/* Sport cards grid */
.sports-grid {
    display: grid;
    grid-template-columns: repeat(3, 160px);
    grid-template-rows: repeat(2, 160px);
    gap: 1.2rem;
    position: relative;
    margin-bottom: 2rem;
}

.sport-card {
    width: 160px; height: 160px;
    border-radius: 50%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    position: relative;
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);
}
.sport-card.live {
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.1), rgba(2,6,23,0.92));
    border: 2px solid rgba(249,115,22,0.7);
    box-shadow: 0 0 0 6px rgba(249,115,22,0.1), 0 0 30px rgba(249,115,22,0.2);
    cursor: pointer;
}
.sport-card.coming {
    background: rgba(15,23,42,0.7);
    border: 1px solid rgba(148,163,184,0.1);
    opacity: 0.4;
}
.sport-card.center-hub {
    background: radial-gradient(circle, rgba(251,191,36,0.12), rgba(2,6,23,0.97));
    border: 2px solid rgba(251,191,36,0.4);
    box-shadow: 0 0 0 8px rgba(251,191,36,0.05);
    grid-column: 2; grid-row: 1 / 3;
    align-self: center;
    width: 130px; height: 130px;
    border-radius: 50%;
    cursor: default;
}

.pulse-ring {
    position: absolute; inset: -10px;
    border-radius: 50%;
    border: 2px solid rgba(249,115,22,0.3);
    animation: pulse 2.5s ease-out infinite;
    pointer-events: none;
}
.pulse-ring-2 { animation-delay: 0.9s; }
@keyframes pulse {
    0%   { transform: scale(1);   opacity: 0.5; }
    100% { transform: scale(1.5); opacity: 0; }
}

.sport-icon { font-size: 2rem; margin-bottom: 0.3rem; }
.sport-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.72rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #f8fafc; text-align: center;
}
.sport-badge {
    margin-top: 0.25rem;
    padding: 0.1rem 0.5rem; border-radius: 999px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.55rem; font-weight: 800;
    letter-spacing: 0.1em; text-transform: uppercase;
}
.badge-live {
    background: rgba(249,115,22,0.2);
    border: 1px solid rgba(249,115,22,0.5);
    color: #f97316;
}
.badge-soon {
    background: rgba(148,163,184,0.07);
    border: 1px solid rgba(148,163,184,0.15);
    color: #475569;
}
.hub-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.55rem; font-weight: 800;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: #fbbf24; text-align: center;
}
.hub-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.3rem; font-weight: 900;
    color: #f8fafc; text-align: center;
}

/* Enter button */
.enter-wrap { text-align: center; }
.enter-link {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.7rem 2rem; border-radius: 999px;
    background: linear-gradient(135deg, #f97316, #fb7185);
    color: #0f172a; text-decoration: none;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem; font-weight: 800;
    letter-spacing: 0.08em; text-transform: uppercase;
    box-shadow: 0 4px 20px rgba(249,115,22,0.4);
}

.foot-note {
    margin-top: 1.5rem;
    font-size: 0.65rem; color: #1e293b;
    letter-spacing: 0.1em; text-transform: uppercase;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ──
st.markdown("""
<div class="wheel-page">
  <div class="wheel-eyebrow">Maine High School Athletics</div>
  <div class="wheel-title">Analytics<span>207</span></div>
  <div class="wheel-sub">Choose your sport to get started</div>
</div>
""", unsafe_allow_html=True)

# ── SPORT SELECTOR — 3 columns ──
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1], gap="large")

with col1:
    st.markdown("""
<div style="display:flex;flex-direction:column;gap:1.2rem;align-items:center;margin-top:80px;">
  <div class="sport-card coming">
    <div class="sport-icon">🏃</div>
    <div class="sport-name">Cross Country</div>
    <div class="sport-badge badge-soon">Coming Soon</div>
  </div>
  <div class="sport-card coming">
    <div class="sport-icon">🏒</div>
    <div class="sport-name">Hockey</div>
    <div class="sport-badge badge-soon">Coming Soon</div>
  </div>
</div>
""", unsafe_allow_html=True)

with col3:
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;">
  <div class="sport-card center-hub">
    <div class="hub-label">Analytics</div>
    <div class="hub-name">207</div>
  </div>
</div>
""", unsafe_allow_html=True)

with col5:
    st.markdown("""
<div style="display:flex;flex-direction:column;gap:1.2rem;align-items:center;margin-top:80px;">
  <div class="sport-card coming">
    <div class="sport-icon">🏈</div>
    <div class="sport-name">Football</div>
    <div class="sport-badge badge-soon">Coming Soon</div>
  </div>
  <div class="sport-card coming">
    <div class="sport-icon">⚽</div>
    <div class="sport-name">Soccer</div>
    <div class="sport-badge badge-soon">Coming Soon</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── BASKETBALL — center top using native Streamlit button ──
_, center, _ = st.columns([2, 1, 2])
with center:
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;margin-bottom:0.5rem;">
  <div class="sport-card live" style="margin-bottom:1rem;">
    <div class="pulse-ring"></div>
    <div class="pulse-ring pulse-ring-2"></div>
    <div class="sport-icon">🏀</div>
    <div class="sport-name">Basketball</div>
    <div class="sport-badge badge-live">● Live</div>
  </div>
</div>
""", unsafe_allow_html=True)
    if st.button("Enter Basketball →", type="primary", use_container_width=True):
        st.switch_page("pages/00_Basketball.py")

st.markdown("""
<div class="foot-note">Analytics207.com · Maine High School Athletics</div>
""", unsafe_allow_html=True)
