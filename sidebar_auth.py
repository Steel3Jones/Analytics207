# sidebar_auth.py
import streamlit as st

def render_sidebar_auth():
    st.markdown("""
    <style>
    [data-testid="stSidebarHeader"] {
        height: 0px !important;
        min-height: 0px !important;
        max-height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    [data-testid="stSidebarContent"] {
        display: flex !important;
        flex-direction: column !important;
        padding-top: 0.3rem !important;
        gap: 0 !important;
    }
    [data-testid="stSidebarContent"] > * {
        margin: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    [data-testid="stSidebarNav"] {
        order: 2 !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    [data-testid="stSidebarContent"] > div:not([data-testid="stSidebarNav"]) {
        order: 1 !important;
    }
    [data-testid="stSidebarUserContent"] {
        padding: 0 0.5rem !important;
        margin: 0 !important;
    }
    [data-testid="stSidebarUserContent"] > div {
        gap: 0 !important;
    }
    /* Kill block container gap inside sidebar */
    [data-testid="stSidebar"] .block-container,
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
        padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
