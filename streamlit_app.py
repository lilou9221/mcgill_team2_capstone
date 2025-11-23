# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import os
import time
import traceback

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
            "data": {"raw": "data/raw", "processed": "data/processed", "external": "data/external"},
            "output": {"maps": "output/maps", "html": "output/html"},
            "processing": {"h3_resolution": 7, "enable_clipping": True},
            "gee": {}, "drive": {}
        }
        for key, val in defaults.items():
            if key not in config:
                config[key] = val
        return config
    except Exception as e:
        st.warning(f"Using default config: {e}")
        return {
            "data": {"raw": "data/raw", "processed": "data/processed", "external": "data/external"},
            "output": {"maps": "output/maps", "html": "output/html"},
            "processing": {"h3_resolution": 7, "enable_clipping": True},
            "gee": {}, "drive": {}
        }

config = get_config()

st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# BEAUTIFUL CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, .stApp, h1, h2, h3, p, div, span, label {font-family: 'Inter', sans-serif; color: #333 !important;}
    h1, h2, h3 {color: #173a30 !important; font-weight: 600;}
    .stApp {background-color: #f8f9fa;}
    .header-title {font-size: 3.2rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem;}
    .header-subtitle {text-align: center; color: #555; font-size: 1.2rem; margin-bottom: 3rem;}
    section[data-testid="stSidebar"] {background-color: #173a30 !important; padding-top: 2rem;}
    section[data-testid="stSidebar"] * {color: white !important;}
    .stButton > button {background-color: #64955d !important; color: white !important; border-radius: 999px; font-weight: 600; height: 3em;}
    .stButton > button:hover {background-color: #527a48 !important;}
    .metric-card {
        background: white; padding: 1.8rem; border-radius: 12px;
        border-left: 6px solid #64955d; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: all 0.2s;
    }
    .metric-card:hover {transform: translateY(-4px);}
    .legend-box {
        background: white; padding: 28px; border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12); max-width: 760px;
        margin: 50px auto; text-align: center; border: 1px solid #eee;
    }
    .legend-title {font-size: 1.4rem; font-weight: 700; color: #173a30; margin-bottom: 16px;}
    .legend-row {display: flex; justify-content: center; flex-wrap: wrap; gap: 24px; margin: 16px 0;}
    .legend-item {display: flex; align-items: center; gap: 12px; font-size: 1rem; font-weight: 500;}
    .legend-color {width: 36px; height: 22px; border-radius: 6px; display: inline-block;}
    .footer {text-align: center; padding: 6rem 0 3rem; color: #666; border-top: 1px solid #eee; margin-top: 8rem;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil health & crop residue mapping for sustainable biochar in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Area")
    use_coords = st.checkbox("Analyze around a point", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 150, 100, 25)
    
    h3_res = st.slider("H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)
    
    if st.button("Clear Cache & Restart", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.clear()
        st.success("Cache cleared! Reloading...")
        st.rerun()

# ============================================================
# SESSION STATE
# ============================================================
for key in ["analysis_running", "current_process", "analysis_results", "investor_checked", "investor_map_available"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "analysis_results" else False

# Investor data check (once)
if not st.session_state.investor_checked:
    boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
    waste_csv = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"
    st.session_state.investor_map_available = boundaries_dir.exists() and waste_csv.exists()
    st.session_state.investor_checked = True

# ============================================================
# RUN ANALYSIS (your original working pipeline – fully restored)
# ============================================================
if run_btn:
    if st.session_state.analysis_running:
        st.warning("Analysis already running. Please wait.")
        st.stop()

    st.session_state.analysis_results = None
    st.session_state.analysis_running = True

    with st.spinner("Preparing local data..."):
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        tif_files = list(raw_dir.glob("*.tif"))
        if len(tif_files) < 5:
            st.error("Not enough GeoTIFF files found in data/raw/")
            st.info("Please place your soil raster files in data/raw/")
            st.session_state.analysis_running = False
            st.stop()

    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    if not wrapper_script.exists():
        st.error(f"Missing: {wrapper_script}")
        st.stop()

    cli = [sys.executable, str(wrapper_script), "--h3-resolution", str(h3_res)]
    config_file = PROJECT_ROOT / "configs" / "config.yaml"
    if config_file.exists():
        cli += ["--config", str(config_file)]
    if use_coords and lat and lon and radius:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    progress_bar = st.progress(0)
    log_box = st.expander("Detailed logs", expanded=False)
    logs = []

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"

        process = subprocess.Popen(
            cli, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=str(PROJECT_ROOT), env=env
        )
        st.session_state.current_process = process
        start_time = time.time()

        for line in process.stdout:
            logs.append(line.strip())
            log_box.code("\n".join(logs[-25:]), language="text")
            elapsed = int(time.time() - start_time)
            status.markdown(f"**Running analysis...** {elapsed}s elapsed")

            l = line.lower()
            if any(x in l for x in ["clip", "mask"]): progress_bar.progress(25)
            if "zonal" in l: progress_bar.progress(50)
            if "h3" in l: progress_bar.progress(70)
            if any(x in l for x in ["scor", "sav", "done", "complet"]): progress_bar.progress(100)

        return_code = process.wait()
        st.session_state.current_process = None

        if return_code != 0:
            st.error("Pipeline failed")
            st.code("".join(logs))
            st.session_state.analysis_running = False
            st.stop()

        csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
        if not csv_path.exists():
            st.error("Results file not found")
            st.session_state.analysis_running = False
            st.stop()

        df = pd.read_csv(csv_path)
        if df.empty or "suitability_score" not in df.columns:
            st.error("Invalid or empty results")
            st.session_state.analysis_running = False
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
        st.success("Analysis completed successfully!")

    except Exception as e:
        st.error("Pipeline error")
        st.code(traceback.format_exc())
    finally:
        st.session_state.analysis_running = False

# ============================================================
# DISPLAY RESULTS – FINAL POLISHED VERSION
# ============================================================
if st.session_state.analysis_results:
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    df = pd.read_csv(csv_path)
    map_paths = {k: Path(v) for k, v in st.session_state.analysis_results["map_paths"].items()}

    farmer_tab, investor_tab = st.tabs([
        "Farmer Perspective – Soil Health & Biochar Recommendations",
        "Investor Perspective – Crop Residue Opportunity"
    ])

    # ==================== FARMER TAB ====================
    with farmer_tab:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>Hexagons Analyzed</h4><p>{len(df):,}</p></div>', unsafe_allow_html=True)
        with col2:
            mean_score = df["suitability_score"].mean()
            st.markdown(f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>{mean_score:.2f}</p></div>', unsafe_allow_html=True)
        with col3:
            high = (df["suitability_score"] >= 7.0).sum()
            pct = high / len(df) * 100
            st.markdown(f'<div class="metric-card"><h4>Highly Suitable (≥7.0)</h4><p>{high:,} <small>({pct:.1f}%)</small></p></div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, rec_tab = st.tabs(["Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture", "Top 10 Recommendations"])

        def show_map(tab, title, key, legend_html):
            with tab:
                st.subheader(title)
                path = map_paths.get(key)
                if path and path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=700, scrolling=False)
                    st.markdown(legend_html, unsafe_allow_html=True)
                else:
                    st.warning(f"{title} map not generated.")

        show_map(tab1, "Biochar Application Suitability", "suitability", """
            <div class="legend-box">
                <div class="legend-title">Suitability Score (0–10)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>0–2 Very Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FF4500;"></span>2–4 Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>4–6 Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#90EE90;"></span>6–8 High</div>
                    <div class="legend-item"><span class="legend-color" style="background:#006400;"></span>8–10 Very High</div>
                </div>
                <p><strong>Higher score = better long-term biochar performance</strong></p>
            </div>
        """)

        show_map(tab2, "Soil Organic Carbon (g/kg)", "soc", """
            <div class="legend-box">
                <div class="legend-title">Soil Organic Carbon (Average 0–10 cm)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;border:1px solid #aaa;"></span>&lt;10 Very Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>10–20 Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#7FCDBB;"></span>20–30 Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>30–40 High</div>
                    <div class="legend-item"><span class="legend-color" style="background:#253494;"></span>&gt;50 Very High</div>
                </div>
            </div>
        """)

        show_map(tab3, "Soil pH", "ph", """
            <div class="legend-box">
                <div class="legend-title">Soil pH (Average 0–10 cm)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>&lt;5.0 Strongly Acidic</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FF6347;"></span>5.0–5.5 Acidic</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>5.5–7.0 Ideal for Biochar</div>
                    <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>7.0–8.0 Alkaline</div>
                </div>
            </div>
        """)

        show_map(tab4, "Soil Moisture (%)", "moisture", """
            <div class="legend-box">
                <div class="legend-title">Volumetric Soil Moisture</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B4513;"></span>&lt;10% Very Dry</div>
                    <div class="legend-item"><span class="legend-color" style="background:#D2691E;"></span>10–20% Dry</div>
                    <div class="legend-item"><span class="legend-color" style="background:#F4A460;"></span>20–30% Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>30–40% Moist</div>
                    <div class="legend-item"><span class="legend-color" style="background:#1E90FF;"></span>&gt;40% Very Moist</div>
                </div>
            </div>
        """)

        with rec_tab:
            st.subheader("Top 10 Recommended Locations for Biochar Application")
            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)
            if feed_col and reason_col:
                cols = ["h3_index", "suitability_score", "mean_soc", "mean_ph", "mean_moisture", feed_col, reason_col]
                cols = [c for c in cols if c in df.columns]
                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10).round(3)
                top10 = top10.rename(columns={
                    feed_col: "Recommended Feedstock",
                    reason_col: "Why This Feedstock?",
                    "mean_soc": "SOC (g/kg)",
                    "mean_ph": "pH",
                    "mean_moisture": "Moisture (%)"
                })
                st.dataframe(
                    top10.style.format({
                        "suitability_score": "{:.2f}",
                        "SOC (g/kg)": "{:.1f}",
                        "pH": "{:.2f}",
                        "Moisture (%)": "{:.1%}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Feedstock recommendations not available in this run.")

        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.download_button(
            "Download Full Results as CSV",
            data=df.to_csv(index=False).encode(),
            file_name=f"biochar_suitability_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True
        )

       # ==================== INVESTOR TAB – NOW STARTS INSTANTLY ====================
    with investor_tab:
        st.markdown("### Crop Residue Availability – Biochar Feedstock Opportunity")

        if not st.session_state.investor_map_available:
            st.warning("Investor map data not found")
            st.info("Required:\n• data/boundaries/BR_Municipios_2024/\n• data/crop_data/Updated_municipality_crop_production_data.csv")
        else:
            # IMPORT ONLY WHEN USER OPENS THIS TAB → app starts instantly!
            try:
                from src.map_generators.pydeck_maps.municipality_waste_map import (
                    prepare_investor_crop_area_geodata,
                    create_municipality_waste_deck,
                )
            except Exception as e:
                st.error("Could not import investor map module")
                st.code(str(e))
                st.stop()

            @st.cache_data(show_spinner="Loading crop residue data (first time only)...")
            def get_gdf():
                return prepare_investor_crop_area_geodata(
                    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024",
                    PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv",
                    simplify_tolerance=0.05  # ← this + lazy import = lightning fast
                )

            # First click on Investor tab: 5–8 seconds
            # Every other time + app startup: instant
            gdf = get_gdf()

            data_type = st.radio(
                "Display:",
                ["area", "production", "residue"],
                format_func=lambda x: {"area": "Planted Area (ha)", "production": "Production (tons)", "residue": "Residue (tons)"}[x],
                horizontal=True,
                key="investor_data_type"
            )

            deck = create_municipality_waste_deck(gdf, data_type=data_type)
            st.pydeck_chart(deck, use_container_width=True)

            if data_type == "residue":
                st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Available Crop Residue (tons/year)</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span>Low</div>
                        <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>Moderate</div>
                        <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>High</div>
                        <div class="legend-item"><span class="legend-color" style="background:#225EA8;"></span>Very High Potential</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar suitability and feedstock mapping for Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
