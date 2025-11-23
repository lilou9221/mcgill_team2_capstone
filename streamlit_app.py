# ============================================================
# FINAL VERSION – ALL TEXT VISIBLE, PERFECT CONTRAST
# ============================================================
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import os
import time
import traceback

st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state
for key, default in [
    ("analysis_running", False),
    ("current_process", None),
    ("analysis_results", None),
    ("investor_checked", False),
    ("investor_map_available", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Project setup
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
# FINAL CSS – WHITE BG + DARK TAB TEXT + PERFECT BUTTONS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Force pure white background everywhere */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stDecoration"], .main {
        background-color: white !important;
        background: white !important;
        color: #333 !important;
    }
    
    /* Fix tab text color (was white → now dark) */
    .stTabs [data-baseweb="tab"] {
        color: #173a30 !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #64955d !important;
        border-bottom: 3px solid #64955d !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #173a30 !important;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #64955d !important;
        color: white !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        height: 3.2em !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #527a48 !important;
        color: white !important;
    }
    
    /* Download button – force white text */
    .stDownloadButton > button {
        background-color: #64955d !important;
        color: white !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #527a48 !important;
        color: white !important;
    }
    
    /* Header */
    .header-title {font-size: 3.4rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem;}
    .header-subtitle {text-align: center; color: #444; font-size: 1.3rem; margin-bottom: 3rem;}
    
    /* Cards & legends */
    .metric-card {
        background: white; padding: 1.8rem; border-radius: 14px;
        border-left: 6px solid #64955d; box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        text-align: center; border: 1px solid #eee;
    }
    .metric-card h4 {margin: 0 0 0.5rem; color: #173a30; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.8px;}
    .metric-card p {margin: 0; font-size: 2.4rem; font-weight: 700; color: #333;}
    
    .legend-box {
        background: white; padding: 28px; border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.1); max-width: 760px;
        margin: 50px auto; text-align: center; border: 1px solid #eee;
    }
    .legend-title {font-size: 1.4rem; font-weight: 700; color: #173a30; margin-bottom: 18px;}
    .legend-row {display: flex; justify-content: center; flex-wrap: wrap; gap: 24px;}
    .legend-item {display: flex; align-items: center; gap: 12px; font-size: 1.05rem; font-weight: 500;}
    .legend-color {width: 38px; height: 24px; border-radius: 6px; display: inline-block;}
    
    .footer {
        text-align: center; padding: 6rem 0 3rem; color: #666;
        border-top: 1px solid #eee; margin-top: 8rem; font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil health & crop residue intelligence for sustainable biochar in Mato Grosso</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Analysis Settings")
    use_coords = st.checkbox("Analyze around a location", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 150, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, 7)
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)
    if st.button("Reset Cache & Restart"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# Run analysis (unchanged)
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
        st.success("Analysis completed successfully!")
    except Exception as e:
        st.error("Pipeline crashed.")
        st.code(traceback.format_exc())
    finally:
        st.session_state.analysis_running = False

# Display results
if st.session_state.get("analysis_results"):
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    df = pd.read_csv(csv_path)
    map_paths = st.session_state.analysis_results["map_paths"]

    farmer_tab, investor_tab = st.tabs(["Farmer Perspective", "Investor Perspective"])

    with farmer_tab:
        st.markdown("### Soil Health & Biochar Suitability Insights")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>Hexagons Analyzed</h4><p>{len(df):,}</p></div>', unsafe_allow_html=True)
        with col2:
            mean_score = df["suitability_score"].mean()
            st.markdown(f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>{mean_score:.2f}</p></div>', unsafe_allow_html=True)
        with col3:
            high = (df["suitability_score"] >= 7.0).sum()
            pct = high / len(df) * 100
            st.markdown(f'<div class="metric-card"><h4>Highly Suitable (≥7.0)</h4><p>{high:,}<br><small>({pct:.1f}%)</small></p></div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, rec_tab = st.tabs([
            "Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture", "Top 10 Recommendations"
        ])

        def load_map(path):
            if Path(path).exists():
                with open(path, "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=720, scrolling=False)
            else:
                st.warning("Map not generated yet.")

        with tab1:
            st.subheader("Biochar Application Suitability")
            load_map(map_paths["suitability"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Suitability Score (0–10)</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>0–2 Very Low</div>
                        <div class="legend-item"><span class="legend-color" style="background:#FF4500;"></span>2–4 Low</div>
                        <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>4–6 Moderate</div>
                        <div class="legend-item"><span class="legend-color" style="background:#90EE90;"></span>6–8 High</div>
                        <div class="legend-item"><span class="legend-color" style="background:#006400;"></span>8–10 Very High</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.subheader("Soil Organic Carbon (g/kg)")
            load_map(map_paths["soc"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil Organic Carbon</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;border:1px solid #aaa;"></span>&lt;10 Very Low</div>
                        <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>10–20</div>
                        <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>30–40</div>
                        <div class="legend-item"><span class="legend-color" style="background:#253494;"></span>&gt;50 Very High</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with tab3:
            st.subheader("Soil pH")
            load_map(map_paths["ph"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil pH (Ideal: 5.5–7.0)</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>&lt;5.0 Strongly Acidic</div>
                        <div class="legend-item"><span class="legend-color" style="background:#FF6347;"></span>5.0–5.5 Acidic</div>
                        <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>5.5–7.0 Ideal</div>
                        <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>&gt;7.0 Alkaline</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with tab4:
            st.subheader("Soil Moisture (%)")
            load_map(map_paths["moisture"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Volumetric Soil Moisture</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#8B4513;"></span>&lt;10% Very Dry</div>
                        <div class="legend-item"><span class="legend-color" style="background:#D2691E;"></span>10–20%</div>
                        <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>30–40%</div>
                        <div class="legend-item"><span class="legend-color" style="background:#1E90FF;"></span>&gt;40% Very Moist</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with rec_tab:
            st.subheader("Top 10 Recommended Locations")
            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)
            if feed_col and reason_col:
                cols = ["h3_index", "suitability_score", "mean_soc", "mean_ph", "mean_moisture", feed_col, reason_col]
                cols = [c for c in cols if c in df.columns]
                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10).round(3)
                top10 = top10.rename(columns={feed_col: "Recommended Feedstock", reason_col: "Rationale"})
                st.dataframe(top10.style.format({"suitability_score": "{:.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.info("Feedstock recommendations not available in this run.")

        st.markdown("<br><br>", unsafe_allow_html=True)
        st.download_button(
            "Download Full Results (CSV)",
            df.to_csv(index=False).encode(),
            f"biochar_results_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
            "text/csv",
            use_container_width=True
        )

    with investor_tab:
        st.markdown("### Crop Residue Availability – Biochar Feedstock Opportunity")
        boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
        csv_path = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"

        if not boundaries_dir.exists() or not csv_path.exists():
            st.warning("Investor map data missing.")
            st.info("Required:\n• data/boundaries/BR_Municipios_2024/\n• data/crop_data/Updated_municipality_crop_production_data.csv")
        else:
            try:
                from src.map_generators.pydeck_maps.municipality_waste_map import (
                    prepare_investor_crop_area_geodata,
                    create_municipality_waste_deck,
                )
            except Exception as e:
                st.error("Failed to load investor map module")
                st.code(str(e))
                st.stop()

            @st.cache_data(show_spinner="Loading crop residue data (first time only)...")
            def get_gdf():
                return prepare_investor_crop_area_geodata(
                    boundaries_dir,
                    csv_path,
                    simplify_tolerance=0.05
                )

            gdf = get_gdf()

            data_type = st.radio(
                "Display:",
                ["area", "production", "residue"],
                format_func=lambda x: {"area":"Planted Area (ha)", "production":"Production (tons)", "residue":"Residue (tons)"}[x],
                horizontal=True,
                key="investor_radio"
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
            with c1: st.metric("Total Crop Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")

else:
    st.info("Select your area and click **Run Analysis** (first run takes 2–6 minutes)")

# Footer
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
