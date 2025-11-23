# ============================================================
# STREAMLIT APP – FIXED VERSION WITH ORIGINAL COLORS PRESERVED
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
# PAGE CONFIG (must be first)
# ============================================================
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SESSION STATE INIT
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
        cfg = load_config()
        cfg.setdefault("data", {"raw": "data/raw", "processed": "data/processed"})
        cfg.setdefault("output", {"html": "output/html"})
        cfg.setdefault("processing", {"h3_resolution": 7})
        return cfg
    except:
        return {
            "data": {"raw": "data/raw", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7},
        }

config = get_config()

# ============================================================
# SIMPLE HEADER (unchanged)
# ============================================================
st.title("Biochar Suitability Mapper")
st.markdown("### Farmer & Investor Perspectives for Sustainable Biochar Deployment")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Settings")
    use_coords = st.checkbox("Analyze around a point", value=True)

    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0)
        with c2: lon = st.number_input("Longitude", value=-56.0)
        radius = st.slider("Radius (km)", 25, 150, 100)

    h3_res = st.slider("H3 Resolution", 5, 9, 7)

    run_btn = st.button("Run Analysis", type="primary")

    if st.button("Reset App"):
        st.session_state.clear()
        st.rerun()

# ============================================================
# RUN PIPELINE (unchanged)
# ============================================================
if run_btn:

    st.session_state.analysis_results = None

    if st.session_state.analysis_running:
        st.warning("Analysis already running.")
        st.stop()

    st.session_state.analysis_running = True

    raw_dir = PROJECT_ROOT / config["data"]["raw"]
    tif_files = list(raw_dir.glob("*.tif"))
    if len(tif_files) < 5:
        st.error("Not enough GeoTIFF files found.")
        st.stop()

    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    cli = [sys.executable, str(wrapper_script), "--h3-resolution", str(h3_res)]

    if PROJECT_ROOT.joinpath("configs/config.yaml").exists():
        cli += ["--config", "configs/config.yaml"]

    if use_coords:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    logs = []
    status = st.empty()

    try:
        proc = subprocess.Popen(
            cli, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT), text=True
        )
        st.session_state.current_process = proc

        start = time.time()
        for line in proc.stdout:
            logs.append(line)
            status.write(f"Running… {int(time.time()-start)}s")

        rc = proc.wait()
        if rc != 0:
            st.error("Pipeline failed.")
            st.code("".join(logs))
            st.stop()

        csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
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

    except Exception:
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
    # FARMER POV TAB
    # ========================================================
    with farmer_tab:

        st.markdown("## Soil Health, Suitability & Biochar Recommendations")

        # ----------------------------------------------------
        # Sub-tabs for each soil property layer
        # ----------------------------------------------------
        t1, t2, t3, t4, t5 = st.tabs([
            "Suitability",
            "SOC",
            "pH",
            "Moisture",
            "Top 10 Recommendations"
        ])

        # ---- Utility to load HTML maps ----
        def load_map(path):
            if Path(path).exists():
                html = Path(path).read_text(encoding="utf-8")
                st.components.v1.html(html, height=700, scrolling=False)
            else:
                st.warning("Map not found.")

        # ---- ORIGINAL COLORS LEGENDS (unchanged) ----

        suitability_legend = """
        <div class="legend-box">
        <b>Suitability Score (0–10)</b>
        <div class="legend-row">
            <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>Very Low (0–2)</div>
            <div class="legend-item"><span class="legend-color" style="background:#FF4500;"></span>Low (2–4)</div>
            <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>Moderate (4–6)</div>
            <div class="legend-item"><span class="legend-color" style="background:#90EE90;"></span>High (6–8)</div>
            <div class="legend-item"><span class="legend-color" style="background:#006400;"></span>Very High (8–10)</div>
        </div>
        <p>Higher score = more suitable for biochar</p>
        </div>
        """

        soc_legend = """
        <div class="legend-box">
        <b>SOC (g/kg)</b>
        <div class="legend-row">
            <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span>&lt;10</div>
            <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>10–20</div>
            <div class="legend-item"><span class="legend-color" style="background:#7FCDBB;"></span>20–30</div>
            <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>30–40</div>
            <div class="legend-item"><span class="legend-color" style="background:#253494;"></span>&gt;50</div>
        </div>
        </div>
        """

        ph_legend = """
        <div class="legend-box">
        <b>Soil pH</b>
        <div class="legend-row">
            <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>&lt;5</div>
            <div class="legend-item"><span class="legend-color" style="background:#FF6347;"></span>5–5.5</div>
            <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>5.5–7</div>
            <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>7–8</div>
        </div>
        </div>
        """

        moisture_legend = """
        <div class="legend-box">
        <b>Soil Moisture (%)</b>
        <div class="legend-row">
            <div class="legend-item"><span class="legend-color" style="background:#8B4513;"></span>&lt;10%</div>
            <div class="legend-item"><span class="legend-color" style="background:#D2691E;"></span>10–20%</div>
            <div class="legend-item"><span class="legend-color" style="background:#F4A460;"></span>20–30%</div>
            <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>30–40%</div>
            <div class="legend-item"><span class="legend-color" style="background:#1E90FF;"></span>&gt;40%</div>
        </div>
        </div>
        """

        # ---- MAPS ----
        with t1:
            st.subheader("Biochar Suitability Map")
            load_map(map_paths["suitability"])
            st.markdown(suitability_legend, unsafe_allow_html=True)

        with t2:
            st.subheader("Soil Organic Carbon (SOC)")
            load_map(map_paths["soc"])
            st.markdown(soc_legend, unsafe_allow_html=True)

        with t3:
            st.subheader("Soil pH")
            load_map(map_paths["ph"])
            st.markdown(ph_legend, unsafe_allow_html=True)

        with t4:
            st.subheader("Soil Moisture (%)")
            load_map(map_paths["moisture"])
            st.markdown(moisture_legend, unsafe_allow_html=True)

        # ---- TOP 10 RECOMMENDATIONS ----
        with t5:
            st.subheader("Top 10 Recommended Locations")

            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)

            if feed_col and reason_col:
                cols = [
                    "h3_index", "suitability_score", "mean_soc",
                    "mean_ph", "mean_moisture", feed_col, reason_col
                ]
                cols = [c for c in cols if c in df.columns]

                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10)
                st.dataframe(top10, use_container_width=True)
            else:
                st.info("Feedstock recommendations not found in CSV.")

    # ========================================================
    # INVESTOR POV TAB
    # ========================================================
    with investor_tab:

        st.markdown("## Crop Area, Production & Residue Maps")

        boundaries_dir = PROJECT_ROOT / "data/boundaries/BR_Municipios_2024"
        crop_csv = PROJECT_ROOT / "data/crop_data/Updated_municipality_crop_production_data.csv"

        if not boundaries_dir.exists() or not crop_csv.exists():
            st.error("Investor data not found.")
        else:
            from src.map_generators.pydeck_maps.municipality_waste_map import (
                prepare_investor_crop_area_geodata,
                create_municipality_waste_deck,
            )

            @st.cache_data
            def load_investor_data():
                return prepare_investor_crop_area_geodata(
                    boundaries_dir,
                    crop_csv,
                    simplify_tolerance=0.05
                )

            gdf = load_investor_data()

            dtype = st.radio(
                "Select dataset:",
                ["area", "production", "residue"],
                horizontal=True,
                format_func=lambda x: {"area":"Area", "production":"Production", "residue":"Residue"}[x]
            )

            deck = create_municipality_waste_deck(gdf, data_type=dtype)
            st.pydeck_chart(deck, use_container_width=True)

            # ---- ORIGINAL INVESTOR COLORS ----
            investor_legend = """
            <div class="legend-box">
            <b>Biomass Availability</b>
            <div class="legend-row">
                <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span>Low</div>
                <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>Moderate</div>
                <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>High</div>
                <div class="legend-item"><span class="legend-color" style="background:#225EA8;"></span>Very High</div>
            </div>
            </div>
            """

            st.markdown(investor_legend, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Area (ha)", f"{gdf['total_crop_area_ha'].sum():,.0f}")
            with c2: st.metric("Total Production (t)", f"{gdf['total_crop_production_ton'].sum():,.0f}")
            with c3: st.metric("Total Residue (t)", f"{gdf['total_crop_residue_ton'].sum():,.0f}")
