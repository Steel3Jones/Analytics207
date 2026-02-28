import streamlit as st

@st.dialog("Privacy policy")
def privacy_dialog():
    st.markdown("""
    Your privacy policy text here.
    Keep it readable and factual.
    """)

@st.dialog("Terms of use")
def terms_dialog():
    st.markdown("""
    Your terms of use text here.
    """)

@st.dialog("Analytics policy")
def analytics_dialog():
    st.markdown("""
    Analytics are provided for informational purposes only.
    No wagering, gambling, or betting use.
    """)
