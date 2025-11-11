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
# 2. Load config (cached)
# --------------------------------------------------------------
@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)

config = load_config()

# --------------------------------------------------------------
# 3. UI
# --------------------------------------------------------------
st.set_page_config(page_title="Biochar Suitability Mapper", page_icon="leaf", layout="wide")
st.title("Biochar Suitability Mapping Tool")
st.markdown("Enter coordinates for a **100 km radius** analysis, or leave blank for **full Mato Grosso state**.")

# ---- Sidebar: Coordinates (optional) ----
st.sidebar.header("Analysis Scope")
use_coords = st.sidebar.checkbox("Analyze 100 km radius around a point", value=False)

lat = lon = None
if use_coords:
    col1, col2 = st.sidebar.columns(2)
    lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f", key="lat_input")
    lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f", key="lon_input")
    st.sidebar.info("Radius is **fixed at 100 km**")
else:
    st.sidebar.info("Running analysis for **entire Mato Grosso state**")

h3_res = st.sidebar.slider(
    "H3 resolution", 5, 9, config["processing"].get("h3_resolution", 7)
)

# ---- Run button ----
if st.sidebar.button("Run Analysis", type="primary"):
    with st.spinner("Preparing workspace …"):
        # Temporary copy of raw GeoTIFFs
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        src_raw = PROJECT_ROOT / config["data"]["raw"]
        if src_raw.exists():
            shutil.copytree(src_raw, tmp_raw, dirs_exist_ok=True)
        else:
            st.error("Raw GeoTIFF folder not found. Run GEE export first.")
            st.stop()

        # Build CLI args
        cli = [
            "python", str(PROJECT_ROOT / "src" / "main.py"),
            "--config", str(PROJECT_ROOT / "configs" / "config.yaml"),
            "--h3-resolution", str(h3_res),
        ]
        if lat is not None and lon is not None:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", "100"]  # 100 km fixed

        # Run pipeline
        proc = subprocess.run(cli, cwd=PROJECT_ROOT, capture_output=True, text=True)
        shutil.rmtree(tmp_raw, ignore_errors=True)

        if proc.returncode != 0:
            st.error("Pipeline failed")
            st.code(proc.stderr)
            st.stop()

    # --------------------------------------------------------------
    # 4. Load results
    # --------------------------------------------------------------
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Score CSV missing.")
        st.stop()

    df = pd.read_csv(csv_path)

    # --------------------------------------------------------------
    # 5. Show results
    # --------------------------------------------------------------
    st.success("Analysis complete!")

    col1, col2, col3 = st.columns(3)
    col1.metric("Hexagons", len(df))
    col2.metric("Mean score", f"{df['suitability_score'].mean():.2f}/10")
    col3.metric("High-suitability (≥8)", (df['suitability_score'] >= 8).sum())

    st.subheader("Aggregated hexagon scores")
    st.dataframe(df.sort_values("suitability_score", ascending=False), use_container_width=True)

    # CSV download
    csv_bytes = df.to_csv(index=False).encode()
    st.download_button(
        "Download scores (CSV)",
        data=csv_bytes,
        file_name="biochar_suitability_scores.csv",
        mime="text/csv",
    )

    # Interactive map
    html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if html_path.exists():
        st.subheader("Interactive suitability map")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        st.components.v1.html(html, height=680, scrolling=True)
    else:
        st.warning("Map HTML not generated – check logs.")

st.markdown("---")
st.caption(
    "McGill Capstone – Residual Carbon | "
    "Data: NASA SMAP, OpenLandMap, ESA WorldCover | "
    "Deployed on Streamlit Community Cloud"
)
