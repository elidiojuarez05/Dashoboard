"""Sistema visual global del dashboard Streamlit."""
import streamlit as st


GLOBAL_CSS = r"""
<style>
[data-testid="stHorizontalBlock"] .stButton > button { min-height:42px; border-radius:8px !important; font-weight:700 !important; letter-spacing:.2px; }
div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { border-radius:7px !important; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div { border-radius:7px !important; }
div[data-testid="stRadio"] > div { gap:8px; }
.stTabs [data-baseweb="tab-list"] { background-color:#1b263b; border-radius:10px 10px 0 0; padding:5px; }
div[data-testid="stMetricValue"] { background-color:#1b263b; border-radius:10px; padding:10px; border:1px solid #415a77; }
h1,h2,h3 { color:#778da9 !important; }
[data-testid="stSidebar"] { background-color:#0b132b; }
.assign-hero { background:linear-gradient(135deg,#111827 0%,#172554 55%,#0f172a 100%); border:1px solid #334155; border-radius:16px; padding:20px 22px; margin:6px 0 16px; box-shadow:0 8px 28px rgba(0,0,0,.20); }
.assign-kicker { font-size:11px; font-weight:800; letter-spacing:1.3px; color:#93c5fd; text-transform:uppercase; margin-bottom:5px; }
.assign-title { font-size:25px; line-height:1.15; font-weight:800; color:#f8fafc; margin:0; }
.assign-subtitle { margin-top:7px; color:#94a3b8; font-size:13px; }
.time-summary { background:linear-gradient(135deg,#0f2742,#132f4c); border:1px solid #24527a; border-radius:14px; padding:15px 18px; margin:14px 0 16px; }
.time-summary-label { color:#93c5fd; font-size:11px; font-weight:800; letter-spacing:.8px; text-transform:uppercase; margin-bottom:5px; }
.time-summary-main { color:#f8fafc; font-size:23px; font-weight:800; }
.time-summary-detail { color:#cbd5e1; font-size:13px; margin-top:3px; }
.odp-active-id { color:#f8fafc; font-size:17px; font-weight:800; }
.odp-active-meta { color:#94a3b8; font-size:12px; margin-top:3px; }
.odp-active-state { display:inline-block; padding:4px 9px; border-radius:999px; background:#172554; border:1px solid #1d4ed8; color:#bfdbfe; font-size:11px; font-weight:800; }
.route-note { color:#64748b; font-size:11px; margin-top:3px; }
.station-time { display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:8px; background:#0b1625; border:1px solid #26384d; color:#dbeafe; font-weight:800; }
.process-time { color:#93c5fd; font-size:12px; font-weight:800; }
</style>
"""


def inject_global_styles():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
