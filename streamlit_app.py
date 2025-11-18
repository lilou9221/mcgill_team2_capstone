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
import yaml

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

@st.cache_data
def load_config():
    with open(PROJECT_ROOT / "configs" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# FINAL CSS 
# ============================================================
# ============================================================
# FINAL CSS – ONLY CATARINA'S 5 COLORS + FIX WHITE TEXT
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* FORCE ALL TEXT TO BE DARK – THIS FIXES "Suitability Scores" disappearing */
    .stMarkdown, h1, h2, h3, h4, h5, h6, p, div, span, label, .css-1d391kg, .css-1cpxqw2 {
        color: #333333 !important;
    }
    /* Also fix subheaders specifically */
    h2, h3 {color: #173a30 !important; font-weight: 600 !important;}

    html, body, .stApp {font-family: 'Inter', sans-serif;}
    .stApp {background-color: #f0f0f0;}

    /* Header */
    .header-title {
        font-size: 3rem; font-weight: 700; text-align: center;
        color: #173a30; margin: 2rem 0 0.5rem 0; letter-spacing: -0.8px;
    }
    .header-subtitle {text-align: center; color: #333333; font-size: 1.15rem; margin-bottom: 3rem;}

    /* Sidebar – dark teal */
    section[data-testid="stSidebar"] {background-color: #173a30 !important; padding-top: 2rem;}
    section[data-testid="stSidebar"] * {color: #FFFFFF !important;}

    /* Sidebar buttons → purple */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #4f1c53 !important; color: #FFFFFF !important;
        border-radius: 999px !important; font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {background-color: #3d163f !important;}

    /* Main buttons & download → fresh green */
    .stButton > button, .stDownloadButton > button {
        background-color: #64955d !important; color: #FFFFFF !important;
        border-radius: 999px !important; font-weight: 600 !important; border: none !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {background-color: #527a48 !important;}

    /* Metric cards */
    .metric-card {
        background: #FFFFFF; padding: 1.8rem; border-radius: 12px;
        border-left: 6px solid #64955d; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .metric-card:hover {transform: translateY(-4px);}
    .metric-card h4 {margin: 0 0 0.8rem 0; color: #173a30; font-weight: 600; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 0.8px;}
    .metric-card p {margin: 0; font-size: 2.5rem; font-weight: 700; color: #333333;}

    /* Footer */
    .footer {text-align: center; padding: 3rem 0 2rem; color: #333333; font-size: 0.95rem;
             border-top: 1px solid #ddd; margin-top: 4rem;}
    .footer strong {color: #173a30;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze area around a point", value=False)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.4500, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0000, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)

    h3_res = st.slider("H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# ============================================================
# MAIN PIPELINE (your original code – untouched)
# ============================================================
if run_btn:
    # ← Paste your full analysis block exactly as you had it before
    # (downloads, subprocess, results loading, etc.)
    # I kept it out here for brevity, but it stays 100% the same
    pass

    # Example results section (replace with your real one)
    df = pd.DataFrame({"suitability_score": [8.5, 7.2, 9.1]})  # placeholder
    st.success("Analysis completed successfully!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><h4>Total Hexagons</h4><p>{len(df):,}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h4>Mean Score</h4><p>{df["suitability_score"].mean():.2f}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h4>High Suitability (≥8)</h4><p>{(df["suitability_score"] >= 8).sum():,}</p></div>', unsafe_allow_html=True)

    st.subheader("Suitability Scores")
    st.dataframe(df.sort_values("suitability_score", ascending=False), use_container_width=True)

    st.download_button(
        "Download Results as CSV",
        data=df.to_csv(index=False).encode(),
        file_name="biochar_suitability_scores.csv",
        mime="text/csv",
        use_container_width=True
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Data-driven biochar deployment for ecological impact.
</div>
""", unsafe_allow_html=True)
