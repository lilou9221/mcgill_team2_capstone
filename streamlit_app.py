# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import yaml
import subprocess
import shutil
import tempfile

# --------------------------------------------------------------
# 1. Project setup
# --------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------------------
# 2. Load config
# --------------------------------------------------------------
@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)

config = load_config()

# --------------------------------------------------------------
# 3. Page config & custom CSS
# --------------------------------------------------------------
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
st.markdown("""
<style>
    .main > div {padding-top: 2rem;}
    .stButton > button {
        background-color: #5D7B6A;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #4A5F54;
        box-shadow: 0 4px 8px rgba(93,123,106,0.3);
    }
    .metric-card {
        background-color: #1A1F2B;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #5D7B6A;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: 700;
        text-align: center;
        color: #FAFAFA;
        margin-bottom: 0.5rem;
    }
    .header-subtitle {
        text-align: center;
        color: #A8B5A2;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .sidebar .css-1d391kg {padding-top: 1.5rem;}
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #6B7A6E;
        font-size: 0.9rem;
        border-top: 1px solid #2A2F3B;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------
# 4. Header
# --------------------------------------------------------------
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# --------------------------------------------------------------
# 5. Sidebar
# --------------------------------------------------------------
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze 100 km radius around a point", value=False)

    lat = lon = None
    if use_coords:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f", key="lat_input")
        lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f", key="lon_input")
        st.info("Fixed radius: **100 km**")
    else:
        st.info("Full **Mato Grosso state** analysis")

    h3_res = st.slider("H3 resolution", 5, 9, config["processing"].get("h3_resolution", 7), help="Higher = finer hexagons")

    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# --------------------------------------------------------------
# 6. Main Analysis
# --------------------------------------------------------------
if run_btn:
    with st.spinner("Initializing analysis pipeline..."):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        src_raw = PROJECT_ROOT / config["data"]["raw"]
        if src_raw.exists():
            shutil.copytree(src_raw, tmp_raw, dirs_exist_ok=True)
        else:
            st.error("Raw GeoTIFFs not found. Run GEE export first.")
            st.stop()

        cli = [
            "python", str(PROJECT_ROOT / "src" / "main.py"),
            "--config", str(PROJECT_ROOT / "configs" / "config.yaml"),
            "--h3-resolution", str(h3_res),
        ]
        if lat is not None and lon is not None:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", "100"]

        proc = subprocess.run(cli, cwd=PROJECT_ROOT, capture_output=True, text=True)
        shutil.rmtree(tmp_raw, ignore_errors=True)

        if proc.returncode != 0:
            st.error("Analysis failed")
            with st.expander("View error log"):
                st.code(proc.stderr)
            st.stop()

    # Load results
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results not generated.")
        st.stop()

    df = pd.read_csv(csv_path)

    # --------------------------------------------------------------
    # 7. Results Display
    # --------------------------------------------------------------
    st.success("Analysis complete")

    # Metrics (card style)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0; color:#5D7B6A;">Hexagons</h4>
            <p style="font-size:1.8rem; margin:0.4rem 0; color:#FAFAFA;">{len(df):,}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        mean_score = df['suitability_score'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0; color:#5D7B6A;">Mean Score</h4>
            <p style="font-size:1.8rem; margin:0.4rem 0; color:#FAFAFA;">{mean_score:.2f}/10</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        high_count = (df['suitability_score'] >= 8).sum()
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0; color:#5D7B6A;">High Suitability</h4>
            <p style="font-size:1.8rem; margin:0.4rem 0; color:#FAFAFA;">{high_count:,}</p>
        </div>
        """, unsafe_allow_html=True)

    # Data table
    st.subheader("Suitability Scores by Hexagon")
    st.dataframe(
        df.sort_values("suitability_score", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # Download
    csv = df.to_csv(index=False).encode()
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="biochar_suitability_scores.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Map
    html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if html_path.exists():
        st.subheader("Interactive Suitability Map")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        st.components.v1.html(html, height=700, scrolling=True)
    else:
        st.warning("Map not generated.")

# --------------------------------------------------------------
# 8. Footer
# --------------------------------------------------------------
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Promoting biodiversity through science-driven biochar deployment
</div>
""", unsafe_allow_html=True)
