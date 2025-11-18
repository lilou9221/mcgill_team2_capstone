# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import os
import json
import io
import time

# Check for required dependencies and install if missing (for Streamlit Cloud)
def ensure_dependency(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name, "--quiet"
            ])
            __import__(import_name)
            return True
        except Exception:
            return False

# Check for PyYAML
if not ensure_dependency("PyYAML", "yaml"):
    st.error("Missing dependency PyYAML.\nAdd it to requirements.txt:\nPyYAML>=6.0")
    st.stop()

import yaml

# Project setup
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Load config
@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path, encoding='utf-8') as f:
        return yaml.safe_load(f)
config = load_config()

# Page config
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
#                      CUSTOM CSS
# ============================================================
st.markdown("""
<style>

    /* ------------------------------------------------------- */
    /* BODY + GENERAL */
    /* ------------------------------------------------------- */
    .main > div { padding-top: 2rem; }
    body, .stApp {
        background-color: #ffffff !important;
        color: #333333 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* ------------------------------------------------------- */
    /* BUTTONS */
    /* ------------------------------------------------------- */
    .stButton > button {
        background-color: #5D7B6A !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    .stButton > button:hover {
        background-color: #4A5F54 !important;
        box-shadow: 0 4px 8px rgba(93,123,106,0.3) !important;
    }

    /* ------------------------------------------------------- */
    /* METRIC CARDS */
    /* ------------------------------------------------------- */
    .metric-card {
        background-color: #f8f9fa !important;
        padding: 1.2rem !important;
        border-radius: 12px !important;
        border-left: 4px solid #5D7B6A !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
    }

    /* ------------------------------------------------------- */
    /* HEADER */
    /* ------------------------------------------------------- */
    .header-title {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        color: #2d3a3a !important;
        margin-bottom: 0.5rem !important;
    }
    .header-subtitle {
        text-align: center !important;
        color: #6c757d !important;
        font-size: 1.1rem !important;
        margin-bottom: 2rem !important;
    }

    /* ------------------------------------------------------- */
    /* SIDEBAR — RESIDUAL CARBON GREEN */
    /* ------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        background-color: #0F4A41 !important;
        color: #FFFFFF !important;
        padding-top: 2rem !important;
    }

    /* Make ALL sidebar text white */
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
        font-size: 0.95rem !important;
    }

    /* CHECKBOX text */
    section[data-testid="stSidebar"] .stCheckbox label {
        color: #FFFFFF !important;
    }

    /* INPUT BOXES - readable on green */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] textarea {
        background-color: #13584E !important;
        color: #FFFFFF !important;
        border: 1px solid #88BFB3 !important;
        border-radius: 8px !important;
    }

    /* Placeholder text */
    section[data-testid="stSidebar"] input::placeholder {
        color: #D1E7E2 !important;
    }

    /* SLIDER text */
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stSlider span {
        color: #FFFFFF !important;
    }

    /* SLIDER track */
    section[data-testid="stSidebar"] .stSlider > div > div > div {
        background-color: #FFFFFF !important;
    }

    /* SLIDER handle */
    section[data-testid="stSidebar"] .stSlider [role="slider"] {
        background-color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        height: 18px !important;
        width: 18px !important;
    }

    /* SIDEBAR BUTTON (Run Analysis) */
    section[data-testid="stSidebar"] button {
        background-color: #561E59 !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background-color: #3E1441 !important;
    }

    /* ------------------------------------------------------- */
    /* CODE / LOG BLOCKS */
    /* ------------------------------------------------------- */
    .stCodeBlock, .stCode, code, pre {
        color: #1a1a1a !important;
        background-color: #f5f5f5 !important;
        border: 1px solid #ddd !important;
        border-radius: 6px !important;
        padding: 0.5rem !important;
        font-family: 'Courier New', monospace !important;
    }

    /* ------------------------------------------------------- */
    /* FOOTER */
    /* ------------------------------------------------------- */
    .footer {
        text-align: center !important;
        padding: 2rem 0 !important;
        color: #6c757d !important;
        font-size: 0.9rem !important;
        border-top: 1px solid #dee2e6 !important;
        margin-top: 3rem !important;
    }

</style>
""",
    unsafe_allow_html=True
)

# -------------------------------------------------------
# HEADER
# -------------------------------------------------------
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# -------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze radius around a point", value=False)

    lat = lon = radius = None
