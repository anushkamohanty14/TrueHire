"""TrueHire — main entry point.

Streamlit navigates here first. We immediately redirect to the dashboard.
If the user has no profile yet they can navigate via the sidebar.
"""
import streamlit as st

st.set_page_config(
    page_title="TrueHire",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.switch_page("pages/00_dashboard.py")
