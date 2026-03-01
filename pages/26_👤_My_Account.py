import streamlit as st
import streamlit.components.v1 as components
from auth import (
    get_user,
    get_profile,
    get_supabase,
    create_checkout_url,
    create_portal_url,
    logout_button,
)
from layout import (
    apply_global_layout_tweaks,
    render_logo,
    render_page_header,
    render_footer,
)
from sidebar_auth import render_sidebar_auth

# ── Must be first Streamlit call ──
st.set_page_config(page_title="My Account", page_icon="👤", layout="wide")

render_sidebar_auth()
apply_global_layout_tweaks()

user = get_user()
profile = (get_profile() or {}) if user else {}
sub_status = profile.get("subscription_status", "free") if profile else "free"
sub_type = profile.get("subscription_type", "") if profile else ""
stripe_id = profile.get("stripe_customer_id", "") if profile else ""

# ── Header ──
render_logo()
render_page_header(
    title="My Account",
    definition="Account (n.): Your profile, subscription, and settings",
    subtitle="Manage your plan, view features, and access premium content.",
)
st.write("")

# ── Login / Signup (not logged in) ──
if not user:
    st.subheader("Sign In / Sign Up")
    st.caption("Sign in to manage your account or subscribe to a plan.")

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        sb = get_supabase()
        email = st.text_input("Email", key="acct_login_email")
        password = st.text_input("Password", type="password", key="acct_login_pw")
        if st.button("Log In", key="acct_login_btn"):
            try:
                res = sb.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                st.session_state["user"] = res.user
                st.session_state["session"] = res.session
                st.session_state["profile"] = None
                st.rerun()
                st.stop()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_signup:
        sb = get_supabase()
        new_email = st.text_input("Email", key="acct_signup_email")
        display_name = st.text_input("Display Name", key="acct_signup_name")
        new_password = st.text_input("Password", type="password", key="acct_signup_pw")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="acct_signup_pw2"
        )
        if st.button("Sign Up", key="acct_signup_btn"):
            if new_password != confirm_password:
                st.error("Passwords don't match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            elif not display_name.strip():
                st.error("Display name required")
            else:
                try:
                    res = sb.auth.sign_up(
                        {
                            "email": new_email,
                            "password": new_password,
                            "options": {
                                "data": {"display_name": display_name.strip()}
                            },
                        }
                    )
                    st.success("Check your email to confirm, then log in.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

    st.markdown("---")

# ── Account Details (logged in only) ──
if user:
    name = profile.get("display_name") or (
        getattr(user, "user_metadata", None) or {}
    ).get("display_name", "") or getattr(user, "email", "User")
    email = getattr(user, "email", "")

    col_info, col_status = st.columns([2, 1])
    with col_info:
        st.subheader("Account Details")
        st.markdown(f"**Name:** {name}")
        st.markdown(f"**Email:** {email}")

    with col_status:
        st.subheader("Current Plan")
        if sub_status == "active":
            if sub_type == "season_pass":
                st.success("🏆 Season Pass — Active")
            else:
                st.success("Pro Monthly — Active")
        elif sub_status == "past_due":
            st.warning("Past Due — Please update payment")
        elif sub_status == "cancelled":
            st.error("Cancelled")
        else:
            st.info("Free Plan")

    # Extra plan messaging to differentiate tiers
    if sub_status == "active" and sub_type == "season_pass":
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(245,158,11,0.18) 0%, rgba(251,191,36,0.08) 100%);
                        border: 1px solid rgba(245,158,11,0.5); border-radius: 16px; padding: 24px; margin-top: 12px;
                        text-align: center;">
                <div style="font-size: 32px; margin-bottom: 6px;">🏆</div>
                <div style="font-size: 18px; font-weight: 900; color: #fbbf24; letter-spacing: 0.05em;">
                    SEASON PASS MEMBER
                </div>
                <div style="font-size: 13px; color: #94a3b8; margin-top: 6px;">
                    You have full access to every feature for the entire 2025–26 season.
                    You’re part of the inner circle of fans powering Analytics207.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <ul style="font-size:13px; color:#cbd5e1; margin-top:8px; margin-bottom:16px;">
                <li>Full-season access to every prediction, ranking, and bracket tool.</li>
                <li>Early access to new features as they roll out.</li>
                <li>Priority consideration for feedback and feature requests.</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            "You’re seeing the complete playbook. All features are unlocked for this season."
        )

    elif sub_status == "active" and sub_type != "season_pass":
        st.info(
            "You’re a Pro Monthly member with full access while your subscription is active."
        )

    elif sub_status != "active":
        # Specifically highlight free logged-in users
        st.info(
            "You’re on the free scouting report. "
            "You can see select ratings and tonight’s games. Upgrade to unlock full rankings, projections, and tournament tools."
        )

    st.markdown("---")

    # ── Manage Subscription ──
    if sub_status == "active":
        st.subheader("Manage Subscription")
        if sub_type == "season_pass":
            st.markdown(
                "You have a **Season Pass** — no recurring billing. You're all set for the 2025–26 season!"
            )
        else:
            st.markdown("You have an active **Monthly** subscription.")
            st.markdown(
                """
                <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
                     border-radius:12px; padding:16px; margin:8px 0;">
                    <span style="font-size:14px; font-weight:700; color:#fbbf24;">
                        ⬆ Upgrade to Season Pass — $19.99
                    </span><br>
                    <span style="font-size:12px; color:#94a3b8;">
                        One-time payment for the full 2025–26 season.
                        Your monthly subscription will be cancelled and remaining time prorated.
                        Season Pass locks in the entire season for less than paying month-to-month.
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Upgrade to Season Pass",
                key="upgrade_season",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner("Redirecting to checkout..."):
                    url = create_checkout_url(
                        user,
                        price_id="price_1T60C5LWG769Pv4aJ7beMvHg",
                        mode="payment",
                    )
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0;url={url}">',
                        unsafe_allow_html=True,
                    )
                    st.stop()

        if stripe_id:
            if st.button(
                "Manage Billing", key="manage_billing", use_container_width=True
            ):
                with st.spinner("Redirecting to Stripe..."):
                    url = create_portal_url(stripe_id)
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0;url={url}">',
                        unsafe_allow_html=True,
                    )
                    st.stop()
            st.caption(
                "Update payment method, view invoices, or cancel your subscription."
            )

        st.markdown("---")

# ── Plan Comparison (everyone sees this) ──
st.subheader("Plan Comparison")

current_col = "free"
if sub_status == "active":
    current_col = sub_type if sub_type else "monthly"

features = [
    ("Home Dashboard & Tonight's Games", True, True, True),
    ("Power Index Ratings (Top 5)", True, True, True),
    ("Heal Points (Top 5)", True, True, True),
    ("Model Record / Report Card", True, True, True),
    ("Full Power Index Rankings", False, True, True),
    ("Full Heal Point Rankings", False, True, True),
    ("The Slate - Full Game Predictions", False, True, True),
    ("The Aftermath - Full Results", False, True, True),
    ("Team Center - Deep Team Analytics", False, True, True),
    ("Bracketology", False, True, True),
    ("The Model - Prediction Engine", False, True, True),
    ("The Projector", False, True, True),
    ("Milestones & Records", False, True, True),
    ("The Press Box", False, True, True),
    ("Road Trip Planner", False, True, True),
    ("Insights & Trends", False, True, True),
    ("Pick 5 Challenge", False, True, True),
    ("Trophy Room", False, True, True),
    ("All-State Analytics Team", False, True, True),
    ("Mover Board", False, True, True),
    ("Priority Support", False, False, True),
]


def icon(val):
    return (
        '<span style="color:#22c55e;font-size:16px;">&#10003;</span>'
        if val
        else '<span style="color:rgba(148,163,184,0.3);font-size:16px;">&#8212;</span>'
    )


rows_html = ""
for feat, free, monthly, season in features:
    rows_html += f"""
    <tr>
        <td>{feat}</td>
        <td>{icon(free)}</td>
        <td>{icon(monthly)}</td>
        <td>{icon(season)}</td>
    </tr>"""


def hdr(label, col_key):
    # Add trophy to Season Pass label
    if col_key == "season_pass":
        label = "🏆 " + label
    if current_col == col_key:
        return f'{label}<br><span style="font-size:9px;color:#22c55e;">&#10003; CURRENT</span>'
    return label


row_height = 38
header_height = 60
padding = 40
computed_height = header_height + (len(features) * row_height) + padding

table_html = f"""
<html>
<head>
<style>
body {{ margin:0; background:transparent; }}
.plan-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
}}
.plan-table th {{
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 12px 16px;
    text-align: center;
    border-bottom: 2px solid rgba(245, 158, 11, 0.3);
}}
.plan-table th:first-child {{
    text-align: left;
    color: #e2e8f0;
}}
.plan-table td {{
    padding: 10px 16px;
    font-size: 13px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #cbd5e1;
}}
.plan-table td:first-child {{
    text-align: left;
    font-weight: 600;
    color: #e2e8f0;
}}
.plan-table tr:hover {{
    background: rgba(255,255,255,0.03);
}}
</style>
</head>
<body>
<table class="plan-table">
    <thead>
        <tr>
            <th>Feature</th>
            <th>{hdr("Free", "free")}</th>
            <th>{hdr("Monthly — $6.99/mo", "monthly")}</th>
            <th>{hdr("Season Pass — $19.99", "season_pass")}</th>
        </tr>
    </thead>
    <tbody>
        {rows_html}
    </tbody>
</table>
</body>
</html>
"""

components.html(table_html, height=computed_height, scrolling=False)

# ── Upgrade / Pricing (not active subscribers) ──
if sub_status != "active":
    st.markdown("---")
    st.subheader("Upgrade Your Plan")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.3);
                 border-radius:16px; padding:24px; text-align:center;">
                <div style="font-size:24px; font-weight:900; color:#60a5fa;">$6.99</div>
                <div style="font-size:12px; color:#94a3b8; margin-bottom:12px;">per month — cancel anytime</div>
                <div style="font-size:13px; color:#cbd5e1;">
                    Full access to all analytics, predictions, and tools while active. Billed monthly.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if user:
            if st.button(
                "Subscribe Monthly",
                key="buy_monthly",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner("Redirecting to checkout..."):
                    url = create_checkout_url(
                        user,
                        price_id="price_1T60BQLWG769Pv4apChlmFls",
                        mode="subscription",
                    )
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0;url={url}">',
                        unsafe_allow_html=True,
                    )
                    st.stop()
        else:
            st.caption("Sign in above to subscribe.")

    with col2:
        st.markdown(
            """
            <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
                 border-radius:16px; padding:24px; text-align:center;">
                <div style="font-size:24px; font-weight:900; color:#fbbf24;">$19.99</div>
                <div style="font-size:12px; color:#94a3b8; margin-bottom:12px;">one-time — full 2025–26 season</div>
                <div style="font-size:13px; color:#cbd5e1;">
                    Lock in the entire season. Best value for dedicated fans who want every projection and bracket edge.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if user:
            if st.button(
                "Buy Season Pass", key="buy_season", use_container_width=True
            ):
                with st.spinner("Redirecting to checkout..."):
                    url = create_checkout_url(
                        user,
                        price_id="price_1T60C5LWG769Pv4aJ7beMvHg",
                        mode="payment",
                    )
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0;url={url}">',
                        unsafe_allow_html=True,
                    )
                    st.stop()
        else:
            st.caption("Sign in above to purchase.")

# ── Log Out (logged in only) ──
if user:
    st.markdown("---")
    if st.button("Log Out", key="acct_logout", use_container_width=True):
        try:
            get_supabase().auth.sign_out()
        except Exception:
            pass
        for k in ["user", "session", "profile"]:
            st.session_state[k] = None
        st.rerun()
        st.stop()

render_footer()
