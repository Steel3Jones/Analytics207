import streamlit as st
from supabase import create_client


SUPABASE_URL = "https://lofxbafahfogptdkjhhv.supabase.co"
SUPABASE_KEY = "sb_publishable_FpCxSeMXvTU3MhfD1qrTnQ_eCKaaySR"


@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user():
    user = st.session_state.get("user", None)
    if user is None:
        return None
    session = st.session_state.get("session", None)
    if session and hasattr(session, "refresh_token") and session.refresh_token:
        try:
            sb = get_supabase()
            res = sb.auth.refresh_session(session.refresh_token)
            st.session_state["user"] = res.user
            st.session_state["session"] = res.session
            return res.user
        except Exception:
            st.session_state["user"] = None
            st.session_state["session"] = None
            st.session_state["profile"] = None
            return None
    return user


def get_profile():
    user = get_user()
    if not user:
        return None
    if "profile" not in st.session_state or st.session_state["profile"] is None:
        sb = get_supabase()
        res = sb.table("profiles").select("*").eq("id", user.id).single().execute()
        st.session_state["profile"] = res.data
    return st.session_state["profile"]


def is_logged_in():
    return get_user() is not None


def is_subscribed():
    """Returns True if user has ANY active paid subscription."""
    if not is_logged_in():
        return False
    profile = get_profile()
    return profile is not None and profile.get("subscription_status") == "active"


def is_premium():
    """Returns True only for Annual Pass holders."""
    if not is_logged_in():
        return False
    profile = get_profile()
    return (
        profile is not None
        and profile.get("subscription_status") == "active"
        and profile.get("subscription_type") == "annual_pass"
    )


def is_admin():
    profile = get_profile()
    return profile is not None and profile.get("role") == "admin"


def login_gate(required=True):
    user = get_user()

    if user is not None:
        return user

    if not required:
        _sidebar_login()
        return None

    st.title("\U0001f3c0 Maine Hoops Analytics")
    st.subheader("Sign in to continue")
    _login_form()
    st.stop()


def _sidebar_login():
    """Auth handled on My Account page — no sidebar login."""
    pass


def _login_form():
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
    with tab_login:
        _do_login(prefix="fp_")
    with tab_signup:
        _do_signup(prefix="fp_")


def _do_login(prefix=""):
    sb = get_supabase()
    email = st.text_input("Email", key=f"{prefix}login_email")
    password = st.text_input("Password", type="password", key=f"{prefix}login_pw")
    if st.button("Log In", key=f"{prefix}login_btn"):
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["user"] = res.user
            st.session_state["session"] = res.session
            st.session_state["profile"] = None
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")


def _do_signup(prefix=""):
    sb = get_supabase()
    new_email = st.text_input("Email", key=f"{prefix}signup_email")
    display_name = st.text_input("Display Name", key=f"{prefix}signup_name")
    new_password = st.text_input("Password", type="password", key=f"{prefix}signup_pw")
    confirm_password = st.text_input("Confirm Password", type="password", key=f"{prefix}signup_pw2")
    if st.button("Sign Up", key=f"{prefix}signup_btn"):
        if new_password != confirm_password:
            st.error("Passwords don't match")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters")
        elif not display_name.strip():
            st.error("Display name required")
        else:
            try:
                res = sb.auth.sign_up({
                    "email": new_email,
                    "password": new_password,
                    "options": {"data": {"display_name": display_name.strip()}}
                })
                st.success("Check your email to confirm, then log in.")
            except Exception as e:
                st.error(f"Signup failed: {e}")


def logout_button():
    """Show user status in sidebar via CSS injection."""
    if not is_logged_in():
        return
    user = get_user()
    profile = get_profile()
    name = (
        (profile.get("display_name") if profile else None)
        or user.user_metadata.get("display_name", None)
        or user.email
    )
    sub_status = profile.get("subscription_status", "free") if profile else "free"
    sub_type = profile.get("subscription_type", "") if profile else ""

    if sub_status == "active":
        if sub_type == "annual_pass":
            badge = "🌟 Annual Pass"
        elif sub_type == "season_pass":
            badge = "🏆 Season Pass"
        else:
            badge = "⭐ Pro"
        status_text = f"👤 {name} · {badge}"
    else:
        status_text = f"👤 {name} · Free"

    st.markdown(f"""
    <style>
    [data-testid="stSidebarNav"]::after {{
        content: "{status_text}";
        display: block;
        font-size: 11px;
        color: rgba(148,163,184,0.6);
        padding: 6px 12px 0 12px;
        pointer-events: none;
    }}
    </style>
    """, unsafe_allow_html=True)


def require_subscription(message="\U0001f512 Subscribe to unlock this content!"):
    """Blocks content if user has no active subscription."""
    if is_subscribed():
        return True
    st.info(message)
    return False


def require_premium(message="\U0001f31f Annual Pass required to access this content."):
    """Blocks content unless user has Annual Pass."""
    if is_premium():
        return True
    st.info(message)
    return False


def create_checkout_url(user, price_id: str, mode: str = "subscription"):
    """Create a Stripe Checkout session and return the URL."""
    import stripe
    import os
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    profile = get_profile()
    stripe_customer_id = profile.get("stripe_customer_id") if profile else None

    session_params = {
        "success_url": "https://analytics207.com/My_Account?checkout=success",
        "cancel_url": "https://analytics207.com/My_Account?checkout=cancel",
        "mode": mode,
        "metadata": {"supabase_user_id": user.id},
        "line_items": [{"price": price_id, "quantity": 1}],
    }

    if stripe_customer_id:
        session_params["customer"] = stripe_customer_id
    else:
        session_params["customer_email"] = user.email

    session = stripe.checkout.Session.create(**session_params)
    return session.url


def create_portal_url(customer_id: str):
    """Create a Stripe Customer Portal session and return the URL."""
    import stripe
    import os
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://analytics207.com/My_Account",
    )
    return session.url
