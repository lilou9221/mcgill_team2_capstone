# ============================================================
# STREAMLIT APP – FIXED, CLEANED, 2-TAB VERSION
# ============================================================

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import os
import time
import traceback

# ============================================================
# BEFORE ANYTHING — PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SESSION STATE — MUST BE INITIALIZED EARLY
# ============================================================
for key, default in [
    ("analysis_running", False),
    ("current_process", None),
    ("analysis_results", None),
    ("investor_checked", False),
    ("investor_map_available", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config_loader import load_config

@st.cache_data
def get_config():
    try:
        config = load_config()
        defaults = {
            "data": {"raw": "data/raw", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }
        for k, v in defaults.items():
            config.setdefault(k, v)
        return config
    except:
        return {
            "data": {"raw": "data/raw", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }

config = get_config()

# ============================================================
# STYLING
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, .stApp { font-family: 'Inter', sans-serif; }
    .header-title { font-size: 3rem; font-weight: 700; text-align: center; color: #173a30; margin-top: 1.5rem; }
    .header-subtitle { text-align: center; color: #555; font-size: 1.2rem; margin-bottom: 2rem; }
    .legend-box {
        background: #fff; padding: 18px; border-radius: 12px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.1);
        max-width: 700px; margin: 25px auto;
        border: 1px solid #eee;
    }
    .legend-row { display: flex; justify-content: center; flex-wrap: wrap; gap: 12px; }
    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-color { width: 26px; height: 18px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Farmer + Investor Perspective • Soil & Crop Intelligence for Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Settings")
    use_coords = st.checkbox("Analyze around a location", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 150, 100)

    h3_res = st.slider("H3 Resolution", 5, 9, 7)

    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

    if st.button("Reset Cache"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# ============================================================
# RUN ANALYSIS PIPELINE
# ============================================================
if run_btn:

    st.session_state.analysis_results = None

    if st.session_state.analysis_running:
        st.warning("Analysis already running. Please wait…")
        st.stop()

    st.session_state.analysis_running = True

    raw_dir = PROJECT_ROOT / config["data"]["raw"]
    tif_files = list(raw_dir.glob("*.tif"))
    if len(tif_files) < 5:
        st.error("Not enough GeoTIFF files in data/raw/.")
        st.stop()

    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    cli = [sys.executable, str(wrapper_script), "--h3-resolution", str(h3_res)]

    config_file = PROJECT_ROOT / "configs" / "config.yaml"
    if config_file.exists():
        cli += ["--config", str(config_file)]

    if use_coords:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    logs = []

    try:
        env = os.environ.copy()
        process = subprocess.Popen(
            cli, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT), text=True, bufsize=1
        )
        st.session_state.current_process = process

        start = time.time()
        for line in process.stdout:
            logs.append(line)
            status.write(f"Running… {int(time.time() - start)}s elapsed")

        rc = process.wait()
        if rc != 0:
            st.error("Pipeline failed.")
            st.code("".join(logs))
            st.session_state.analysis_running = False
            st.stop()

        csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
        if not csv_path.exists():
            st.error("Results CSV missing.")
            st.stop()

        map_paths = {
            "suitability": str(PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"),
            "soc": str(PROJECT_ROOT / config["output"]["html"] / "soc_map_streamlit.html"),
            "ph": str(PROJECT_ROOT / config["output"]["html"] / "ph_map_streamlit.html"),
            "moisture": str(PROJECT_ROOT / config["output"]["html"] / "moisture_map_streamlit.html"),
        }

        st.session_state.analysis_results = {
            "csv_path": str(csv_path),
            "map_paths": map_paths
        }

        st.success("Analysis completed!")

    except Exception as e:
        st.error("Pipeline crashed.")
        st.code(traceback.format_exc())
    finally:
        st.session_state.analysis_running = False

# ============================================================
# DISPLAY RESULTS — TWO MAIN TABS
# ============================================================
if st.session_state.get("analysis_results"):

    csv_path = Path(st.session_state["analysis_results"]["csv_path"])
    df = pd.read_csv(csv_path)
    map_paths = st.session_state["analysis_results"]["map_paths"]

    farmer_tab, investor_tab = st.tabs(["🌱 Farmer Perspective", "📊 Investor Perspective"])

    # ========================================================
    # FARMER TAB
    # ========================================================
    with farmer_tab:

        st.markdown("### Soil Health & Biochar Suitability")

        tab1, tab2, tab3, tab4, rec_tab = st.tabs([
            "Suitability",
            "Soil Organic Carbon (SOC)",
            "Soil pH",
            "Soil Moisture",
            "Top 10 Recommendations"
        ])

        # ---- LEGENDS ----
        suitability_legend = """
            <div class="legend-box">
            <strong>Suitability Score (0–10)</strong>
            <div class="legend-row">
                <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>0–2</div>
                <div class="legend-item"><span class="legend-color" style="background:#FF4500;"></span>2–4</div>
                <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>4–6</div>
                <div class="legend-item"><span class="legend-color" style="background:#90EE90;"></span>6–8</div>
                <div class="legend-item"><span class="legend-color" style="background:#006400;"></span>8–10</div>
            </div>
            Higher score = higher biochar impact
            </div>
        """

        soc_legend = """
            <div class="legend-box">
            <strong>Soil Organic Carbon (g/kg)</strong>
            <div class="legend-row">
                <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span><10</div>
                <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>10–20</div>
                <div class="legend-item"><span class="legend-color" style="background:#7FCDBB;"></span>20–30</div>
                <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>30–40</div>
                <div class="legend-item"><span class="legend-color" style="background:#253494;"></span>>50</div>
            </div>
            </div>
        """

        ph_legend = """
            <div class="legend-box">
            <strong>Soil pH</strong>
            <div class="legend-row">
                <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span><5</div>
                <div class="legend-item"><span class="legend-color" style="background:#FF6347;"></span>5–5.5</div>
                <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>5.5–7</div>
                <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>7–8</div>
            </div>
            </div>
        """

        moisture_legend = """
            <div class="legend-box">
            <strong>Soil Moisture (%)</strong>
            <div class="legend-row">
                <div class="legend-item"><span class="legend-color" style="background:#8B4513;"></span><10%</div>
                <div class="legend-item"><span class="legend-color" style="background:#D2691E;"></span>10–20%</div>
                <div class="legend-item"><span class="legend-color" style="background:#F4A460;"></span>20–30%</div>
                <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>30–40%</div>
                <div class="legend-item"><span class="legend-color" style="background:#1E90FF;"></span>>40%</div>
            </div>
            </div>
        """

        # ---- MAP LOADER ----
        def load_map(path):
            if Path(path).exists():
                with open(path, "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=700, scrolling=False)
            else:
                st.warning("Map not generated.")

        with tab1:
            st.subheader("Biochar Suitability Map")
            load_map(map_paths["suitability"])
            st.markdown(suitability_legend, unsafe_allow_html=True)

        with tab2:
            st.subheader("Soil Organic Carbon (SOC)")
            load_map(map_paths["soc"])
            st.markdown(soc_legend, unsafe_allow_html=True)

        with tab3:
            st.subheader("Soil pH")
            load_map(map_paths["ph"])
            st.markdown(ph_legend, unsafe_allow_html=True)

        with tab4:
            st.subheader("Soil Moisture (%)")
            load_map(map_paths["moisture"])
            st.markdown(moisture_legend, unsafe_allow_html=True)

        # ---- TOP RECOMMENDATIONS ----
        with rec_tab:
            st.subheader("Top 10 Recommended Hexagons")

            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)

            if feed_col and reason_col:
                cols = ["h3_index", "suitability_score", "mean_soc", "mean_ph", "mean_moisture", feed_col, reason_col]
                cols = [c for c in cols if c in df.columns]
                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10)
                st.dataframe(top10, use_container_width=True)
            else:
                st.info("Feedstock recommendations not available.")

    # ========================================================
    # INVESTOR TAB
    # ========================================================
    with investor_tab:

        st.markdown("### National Crop Residue & Biomass Potential")

        # check data
        boundaries_dir = PROJECT_ROOT / "data/boundaries/BR_Municipios_2024"
        csv_path = PROJECT_ROOT / "data/crop_data/Updated_municipality_crop_production_data.csv"

        if not boundaries_dir.exists() or not csv_path.exists():
            st.warning("Investor map data missing.")
        else:
            from src.map_generators.pydeck_maps.municipality_waste_map import (
                prepare_investor_crop_area_geodata,
                create_municipality_waste_deck,
            )

            @st.cache_data
            def get_gdf():
                return prepare_investor_crop_area_geodata(
                    boundaries_dir,
                    csv_path,
                    simplify_tolerance=0.05
                )

            gdf = get_gdf()

            data_type = st.radio(
                "Choose dataset:",
                ["area", "production", "residue"],
                horizontal=True,
                format_func=lambda x: {"area":"Area (ha)", "production":"Production (t)", "residue":"Residue (t)"}[x]
            )

            deck = create_municipality_waste_deck(gdf, data_type=data_type)
            st.pydeck_chart(deck, use_container_width=True)

            # legend
            st.markdown("""
                <div class="legend-box">
                <strong>Biomass Availability</strong>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span>Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>High</div>
                    <div class="legend-item"><span class="legend-color" style="background:#225EA8;"></span>Very High</div>
                </div>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")
