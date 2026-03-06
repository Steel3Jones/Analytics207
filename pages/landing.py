import streamlit as st
import streamlit.components.v1 as components

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

# Hide Streamlit default chrome for a clean full-screen experience
st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
.block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"] { padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

components.html("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #020617;
    --gold: #fbbf24;
    --basketball: #f97316;
  }

  html, body {
    width: 100%; height: 100%;
    background: var(--bg);
    overflow: hidden;
    font-family: 'Barlow', sans-serif;
    color: #e2e8f0;
  }

  /* GRID */
  body::after {
    content: '';
    position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none; z-index: 0;
  }

  /* AMBIENT GLOW */
  .ambient {
    position: fixed; inset: 0;
    background: radial-gradient(ellipse 60% 60% at 50% 50%, rgba(251,191,36,0.06), transparent);
    pointer-events: none; z-index: 0;
    transition: background 0.6s ease;
  }

  /* STAGE */
  .stage {
    position: relative; z-index: 1;
    width: 100vw; height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }

  /* HEADER */
  .header {
    text-align: center;
    margin-bottom: 2rem;
    animation: fadeUp 0.7s ease both;
  }
  .eyebrow {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.68rem; letter-spacing: 0.25em;
    text-transform: uppercase; color: var(--gold);
    margin-bottom: 0.35rem;
  }
  .title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3rem; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.03em;
    color: #f8fafc; line-height: 1;
  }
  .title span {
    background: linear-gradient(135deg, var(--gold), #fb7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .subtitle {
    font-size: 0.85rem; color: #475569;
    margin-top: 0.35rem; letter-spacing: 0.04em;
  }

  /* WHEEL */
  .wheel-wrap {
    position: relative;
    width: 500px; height: 500px;
    animation: fadeUp 0.7s 0.15s ease both;
  }

  /* SPOKES */
  .spokes {
    position: absolute; inset: 0; pointer-events: none;
  }
  .spokes svg { width: 100%; height: 100%; }

  /* HUB */
  .hub {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 115px; height: 115px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(251,191,36,0.12), rgba(2,6,23,0.97));
    border: 2px solid rgba(251,191,36,0.4);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    z-index: 10;
    box-shadow: 0 0 0 8px rgba(251,191,36,0.05), 0 0 40px rgba(251,191,36,0.12);
    transition: border-color 0.3s, box-shadow 0.3s;
  }
  .hub-eyebrow {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.55rem; font-weight: 800;
    letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold);
  }
  .hub-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.05rem; font-weight: 900;
    color: #f8fafc; line-height: 1.1; text-align: center;
  }

  /* SPORT NODES */
  .sport-node {
    position: absolute;
    width: 108px; height: 108px;
    border-radius: 50%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    transform: translate(-50%, -50%);
    transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.3s;
    text-decoration: none;
  }
  .sport-node.live {
    background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.1), rgba(2,6,23,0.92));
    border: 2px solid rgba(249,115,22,0.6);
    box-shadow: 0 0 0 4px rgba(249,115,22,0.12), 0 0 28px rgba(249,115,22,0.18);
    cursor: pointer;
  }
  .sport-node.live:hover {
    transform: translate(-50%, -50%) scale(1.18);
    box-shadow: 0 0 0 8px rgba(249,115,22,0.18), 0 0 50px rgba(249,115,22,0.38);
  }
  .sport-node.coming {
    background: rgba(15,23,42,0.75);
    border: 1px solid rgba(148,163,184,0.1);
    cursor: not-allowed;
    opacity: 0.45;
  }

  /* PULSE RINGS */
  .pulse-ring {
    position: absolute; inset: -8px;
    border-radius: 50%;
    border: 2px solid rgba(249,115,22,0.35);
    animation: pulse-expand 2.5s ease-out infinite;
    pointer-events: none;
  }
  .pulse-ring:nth-child(2) { animation-delay: 0.9s; }
  @keyframes pulse-expand {
    0%   { transform: scale(1);   opacity: 0.5; }
    100% { transform: scale(1.6); opacity: 0;   }
  }

  .sport-icon { font-size: 1.9rem; line-height: 1; margin-bottom: 0.25rem; }
  .sport-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.68rem; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #f8fafc; text-align: center; line-height: 1.2;
  }
  .sport-badge {
    margin-top: 0.25rem;
    padding: 0.08rem 0.45rem;
    border-radius: 999px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.52rem; font-weight: 800;
    letter-spacing: 0.1em; text-transform: uppercase;
  }
  .badge-live {
    background: rgba(249,115,22,0.18);
    border: 1px solid rgba(249,115,22,0.5);
    color: #f97316;
  }
  .badge-soon {
    background: rgba(148,163,184,0.07);
    border: 1px solid rgba(148,163,184,0.18);
    color: #475569;
  }

  /* INFO PANEL */
  .info-panel {
    margin-top: 1.6rem;
    height: 52px;
    text-align: center;
    animation: fadeUp 0.7s 0.3s ease both;
  }
  .info-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.5rem; font-weight: 900;
    text-transform: uppercase; letter-spacing: 0.05em;
    color: #f8fafc; transition: color 0.3s;
  }
  .info-desc { font-size: 0.78rem; color: #475569; }

  /* ENTER BUTTON */
  .enter-btn {
    display: inline-flex; align-items: center; gap: 0.5rem;
    margin-top: 1.1rem;
    padding: 0.65rem 1.8rem; border-radius: 999px;
    background: linear-gradient(135deg, #f97316, #fb7185);
    color: #0f172a; text-decoration: none;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.95rem; font-weight: 800;
    letter-spacing: 0.08em; text-transform: uppercase;
    box-shadow: 0 4px 18px rgba(249,115,22,0.38);
    animation: fadeUp 0.7s 0.4s ease both;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .enter-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(249,115,22,0.52);
  }
  .enter-btn.hidden { opacity: 0; pointer-events: none; }

  /* FOOTER NOTE */
  .foot {
    position: fixed; bottom: 1.2rem; left: 50%; transform: translateX(-50%);
    font-size: 0.65rem; color: #1e293b;
    letter-spacing: 0.1em; text-transform: uppercase;
    white-space: nowrap; z-index: 2;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
</head>
<body>

<div class="ambient" id="ambient"></div>

<div class="stage">

  <div class="header">
    <div class="eyebrow">Maine High School Athletics</div>
    <div class="title">Analytics<span>207</span></div>
    <div class="subtitle">Choose your sport to get started</div>
  </div>

  <div class="wheel-wrap">

    <!-- SPOKES -->
    <div class="spokes">
      <svg viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
        <line x1="250" y1="250" x2="250" y2="60"  stroke="rgba(249,115,22,0.35)" stroke-width="1.5" stroke-dasharray="4 5"/>
        <line x1="250" y1="250" x2="440" y2="148" stroke="rgba(34,197,94,0.15)"  stroke-width="1"   stroke-dasharray="4 5"/>
        <line x1="250" y1="250" x2="440" y2="352" stroke="rgba(59,130,246,0.15)" stroke-width="1"   stroke-dasharray="4 5"/>
        <line x1="250" y1="250" x2="60"  y2="352" stroke="rgba(167,139,250,0.15)" stroke-width="1"  stroke-dasharray="4 5"/>
        <line x1="250" y1="250" x2="60"  y2="148" stroke="rgba(251,113,133,0.15)" stroke-width="1"  stroke-dasharray="4 5"/>
      </svg>
    </div>

    <!-- HUB -->
    <div class="hub" id="hub">
      <div class="hub-eyebrow">Analytics</div>
      <div class="hub-name">207</div>
    </div>

    <!-- BASKETBALL — top, LIVE -->
    <a class="sport-node live"
       href="http://localhost:8501/Home"
       id="node-basketball"
       style="top:60px; left:250px;"
       data-name="Basketball"
       data-desc="Power rankings, predictions, trophy room &amp; more — live now"
       data-color="#f97316"
       data-live="true">
      <div class="pulse-ring"></div>
      <div class="pulse-ring"></div>
      <div class="sport-icon">🏀</div>
      <div class="sport-name">Basketball</div>
      <div class="sport-badge badge-live">● Live</div>
    </a>

    <!-- FOOTBALL — top right -->
    <div class="sport-node coming"
         style="top:148px; left:440px;"
         data-name="Football"
         data-desc="Rankings, standings &amp; predictions — coming fall 2025"
         data-color="#22c55e">
      <div class="sport-icon">🏈</div>
      <div class="sport-name">Football</div>
      <div class="sport-badge badge-soon">Coming Soon</div>
    </div>

    <!-- SOCCER — bottom right -->
    <div class="sport-node coming"
         style="top:352px; left:440px;"
         data-name="Soccer"
         data-desc="Standings, predictions &amp; analytics — coming fall 2025"
         data-color="#3b82f6">
      <div class="sport-icon">⚽</div>
      <div class="sport-name">Soccer</div>
      <div class="sport-badge badge-soon">Coming Soon</div>
    </div>

    <!-- HOCKEY — bottom left -->
    <div class="sport-node coming"
         style="top:352px; left:60px;"
         data-name="Hockey"
         data-desc="Full season analytics — coming winter 2026"
         data-color="#a78bfa">
      <div class="sport-icon">🏒</div>
      <div class="sport-name">Hockey</div>
      <div class="sport-badge badge-soon">Coming Soon</div>
    </div>

    <!-- CROSS COUNTRY — top left -->
    <div class="sport-node coming"
         style="top:148px; left:60px;"
         data-name="Cross Country"
         data-desc="Race results &amp; performance tracking — coming fall 2025"
         data-color="#fb7185">
      <div class="sport-icon">🏃</div>
      <div class="sport-name">Cross Country</div>
      <div class="sport-badge badge-soon">Coming Soon</div>
    </div>

  </div>

  <!-- INFO -->
  <div class="info-panel">
    <div class="info-name" id="infoName">Select a sport</div>
    <div class="info-desc" id="infoDesc">Hover over any sport to learn more</div>
  </div>

  <!-- ENTER -->
  <a href="http://localhost:8501/Home" class="enter-btn" id="enterBtn">
    Enter Basketball →
  </a>

</div>

<div class="foot">Analytics207.com · Maine High School Athletics</div>

<script>
  const nodes    = document.querySelectorAll('.sport-node');
  const infoName = document.getElementById('infoName');
  const infoDesc = document.getElementById('infoDesc');
  const enterBtn = document.getElementById('enterBtn');
  const ambient  = document.getElementById('ambient');
  const hub      = document.getElementById('hub');

  // Detect if we're on production or local
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const base    = isLocal ? 'http://localhost:8501' : 'https://analytics207.com';

  // Update basketball link dynamically
  document.getElementById('node-basketball').href = base + '/Home';
  enterBtn.href = base + '/Home';

  nodes.forEach(node => {
    node.addEventListener('mouseenter', () => {
      const name  = node.dataset.name;
      const desc  = node.dataset.desc;
      const color = node.dataset.color || '#fbbf24';
      const live  = node.dataset.live === 'true';

      infoName.textContent = name;
      infoName.style.color = color;
      infoDesc.textContent = desc;

      ambient.style.background =
        `radial-gradient(ellipse 60% 60% at 50% 50%, ${color}12, transparent)`;
      hub.style.borderColor = color + '90';
      hub.style.boxShadow   =
        `0 0 0 8px ${color}08, 0 0 40px ${color}22`;

      if (live) {
        enterBtn.classList.remove('hidden');
        enterBtn.textContent = `Enter ${name} →`;
        enterBtn.href = base + '/Home';
      } else {
        enterBtn.classList.add('hidden');
      }
    });

    node.addEventListener('mouseleave', () => {
      infoName.textContent   = 'Select a sport';
      infoName.style.color   = '#f8fafc';
      infoDesc.textContent   = 'Hover over any sport to learn more';
      ambient.style.background =
        'radial-gradient(ellipse 60% 60% at 50% 50%, rgba(251,191,36,0.06), transparent)';
      hub.style.borderColor  = 'rgba(251,191,36,0.4)';
      hub.style.boxShadow    =
        '0 0 0 8px rgba(251,191,36,0.05), 0 0 40px rgba(251,191,36,0.12)';
      enterBtn.classList.remove('hidden');
      enterBtn.textContent   = 'Enter Basketball →';
      enterBtn.href          = base + '/Home';
    });
  });
</script>
</body>
</html>
""", height=820, scrolling=False)
