# streamlit_app/src/state.py
import streamlit as st

DEFAULT_USER = "dung123"

def init_state():
    for k, v in {
        "session_id": "",
        "user_id": DEFAULT_USER,
        "sheet_name": "",
        "sections": [],
        "used_rule": False,
        "confirmed": False,
        "final_result": {},
        "_preview_fetched": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v
