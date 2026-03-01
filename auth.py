import streamlit as st
from supabase import create_client


SUPABASE_URL = "https://lofxbafahfogptdkjhhv.supabase.co"
SUPABASE_KEY = "sb_publishable_FpCxSeMXvTU3MhfD1qrTnQ_eCKaaySR"



@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)



def get_user():
    """Returns the current user or None if not logged in."""
    return st.session_state.get("user", None)



def get_profile():
    """Returns the current user's profile from Supabase or None."""
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
    # BETA: all logged-in users get premium access
    return is_logged_in()



def is_admin():
    profile = get_profile()
    return profile is not None and profile.get("role") == "admin"



def login_gate(required=True):
    """
    If required=True, forces login before page loads.
    If required=False, shows login in sidebar but lets anonymous users see the page.
    Returns the user object or None.
    """
    user = get_user()


    if user is not None:
        return user


    if not required:
        _sidebar_login()
        return None


    st.title("🏀 Maine Hoops Analytics")
    st.subheader("Sign in to continue")
    _login_form()
    st.stop()



def _sidebar_login():
    """Shows a compact login in the sidebar for public pages."""
    with st.sidebar:
        if is_logged_in():
            return
        with st.expander("🔐 Log In / Sign Up"):
            mode = st.radio("", ["Log In", "Sign Up"], horizontal=True, key="sidebar_auth_mode")
            if mode == "Log In":
                _do_login(prefix="sb_")
            else:
                _do_signup(prefix="sb_")



def _login_form():
    """Full-page login/signup form."""
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
    if not is_logged_in():
        return
    user = get_user()
    profile = get_profile()
    name = (
        (profile.get("display_name") if profile else None)
        or user.user_metadata.get("display_name", None)
        or user.email
    )
    st.sidebar.markdown(f"👤 **{name}**")
    if st.sidebar.button("Log Out"):
        sb = get_supabase()
        try:
            sb.auth.sign_out()
        except Exception:
            pass
        st.session_state["user"] = None
        st.session_state["session"] = None
        st.session_state["profile"] = None
        st.rerun()




def require_subscription(message="🔒 Subscribe to unlock this content!"):
    """Call this before premium sections. Blocks content if not subscribed."""
    # BETA: allow all logged-in users to see premium content
    if is_logged_in():
        return True
    st.info(message)
    return False
