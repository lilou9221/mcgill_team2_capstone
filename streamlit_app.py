# ============================================================
# STREAMLIT APP – FINAL POLISHED & LIGHTNING-FAST VERSION
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
# PAGE CONFIG + SESSION STATE
# ============================================================
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# GLOBAL STYLING (updated for white background + black text)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
        color: #000 !important;
    }

    /* Ensure ALL text is black (except sidebar) */
    body, html, .stApp, div, span, p, h1, h2, h3, h4, h5, h6 {
        color: #000 !important;
    }

    /* Sidebar remains perfect (DO NOT TOUCH per user request) */
    section[data-testid="stSidebar"] {
        background-color: #173a30 !important;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    .header-title {
        font-size: 3.4rem;
        font-weight: 700;
        text-align: center;
        color: #173a30;
        margin: 2rem 0 0.5rem;
    }

    .header-subtitle {
        text-align: center;
        color: #444444;
        font-size: 1.3rem;
        margin-bottom: 3rem;
    }

    .stButton > button {
        background-color: #64955d !important;
        color: white !important;
        border-radius: 999px;
        font-weight: 600;
        height: 3.2em;
    }

    .stButton > button:hover {
        background-color: #527a48 !important;
    }

    .metric-card {
        background: white;
        padding: 1.8rem;
        border-radius: 14px;
        border-left: 6px solid #64955d;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        text-align: center;
        color: #000 !important;
    }

    .metric-card h4 {
        margin: 0 0 0.5rem;
        color: #173a30;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    .metric-card p {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 700;
        color: #333333;
    }

    /* Legend box - all text black */
    .legend-box {
        background: white;
        padding: 28px;
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.1);
        max-width: 760px;
        margin: 50px auto;
        text-align: center;
        border: 1px solid #eee;
        color: #000 !important;
    }

    .legend-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #173a30 !important;
        margin-bottom: 18px;
    }

    .legend-row {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 24px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.05rem;
        font-weight: 500;
        color: #000 !important;
    }

    .legend-color {
        width: 38px;
        height: 24px;
        border-radius: 6px;
        display: inline-block;
    }

    .gradient-legend {
        margin: 20px 0;
    }

    .gradient-bar {
        width: 100%;
        height: 40px;
        border-radius: 8px;
        margin: 12px 0;
        border: 1px solid #ddd;
    }

    .gradient-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
        font-size: 0.95rem;
        color: #333;
    }

    .gradient-label {
        text-align: center;
        font-weight: 500;
    }

    .footer {
        text-align: center;
        padding: 6rem 0 3rem;
        color: #666;
        border-top: 1px solid #eee;
        margin-top: 8rem;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil health & crop residue intelligence for sustainable biochar in Mato Grosso</div>', unsafe_allow_html=True)

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
        radius = st.slider("Radius (km)", 25, 150, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, 7)
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)
    if st.button("Reset Cache & Restart"):
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
        st.success("Analysis completed successfully!")
    except Exception as e:
        st.error("Pipeline crashed.")
        st.code(traceback.format_exc())
    finally:
        st.session_state.analysis_running = False

# ============================================================
# DISPLAY RESULTS
# ============================================================
if st.session_state.get("analysis_results"):
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    df = pd.read_csv(csv_path)
    map_paths = st.session_state.analysis_results["map_paths"]

    farmer_tab, investor_tab = st.tabs(["Farmer Perspective", "Investor Perspective"])

    # ========================================================
    # FARMER TAB
    # ========================================================
    with farmer_tab:
        st.markdown("### Soil Health & Biochar Suitability Insights")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f'<div class="metric-card"><h4>Hexagons Analyzed</h4><p>{len(df):,}</p></div>',
                unsafe_allow_html=True
            )

        with col2:
            mean_score = df["suitability_score"].mean()
            st.markdown(
                f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>{mean_score:.2f}</p></div>',
                unsafe_allow_html=True
            )

        # UPDATED PER YOUR REQUEST
        with col3:
            high = (df["suitability_score"] >= 7.0).sum()
            pct = high / len(df) * 100
            st.markdown(
                f'''
                <div class="metric-card">
                    <h4>High Suitability (≥7.0)</h4>
                    <p>{high:,}<br><small>({pct:.1f}%)</small></p>
                </div>
                ''',
                unsafe_allow_html=True
            )

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
                    <div class="legend-title">Suitability Score</div>
                    <div class="gradient-legend">
                        <div class="gradient-bar" style="background: linear-gradient(to right, #8B0000 0%, #FF6B6B 25%, #FFD700 50%, #ADFF2F 75%, #2E7D32 100%);"></div>
                        <div class="gradient-labels">
                            <div class="gradient-label">0.0</div>
                            <div class="gradient-label">2.5</div>
                            <div class="gradient-label">5.0</div>
                            <div class="gradient-label">7.5</div>
                            <div class="gradient-label">10.0</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px; font-size: 0.9rem; color: #666;">
                        <strong>Thresholds:</strong> 0-2.5 (Not Suitable) | 2.6-5.0 (Low) | 5.1-7.5 (Moderate) | 7.6-10.0 (High Suitability)
                    </div>
                    <p style="margin-top: 8px;"><strong>Higher score = poor soil needs biochar (inverse relationship)</strong></p>
                </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.subheader("Soil Organic Carbon (g/kg)")
            load_map(map_paths["soc"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil Organic Carbon</div>
                    <div class="gradient-legend">
                        <div class="gradient-bar" style="background: linear-gradient(to right, #F5DEB3 0%, #D1EE71 25%, #ADFF2F 50%, #6DBE30 75%, #2E7D32 100%);"></div>
                        <div class="gradient-labels">
                            <div class="gradient-label">0</div>
                            <div class="gradient-label">15</div>
                            <div class="gradient-label">30</div>
                            <div class="gradient-label">45</div>
                            <div class="gradient-label">60</div>
                        </div>
                        <div style="text-align: center; margin-top: 4px; font-size: 0.9rem; color: #666;">g/kg</div>
                    </div>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 12px;"><em>Colors represent absolute values (consistent grading across the state)</em></p>
                </div>
            """, unsafe_allow_html=True)

        with tab3:
            st.subheader("Soil pH")
            load_map(map_paths["ph"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil pH</div>
                    <div class="gradient-legend">
                        <div class="gradient-bar" style="background: linear-gradient(to right, #FF8C00 0%, #FFB400 20%, #FFC800 30%, #FFFF00 60%, #ADD8E6 70%, #313695 100%);"></div>
                        <div class="gradient-labels">
                            <div class="gradient-label">4.0</div>
                            <div class="gradient-label">5.0</div>
                            <div class="gradient-label">5.5</div>
                            <div class="gradient-label">7.0</div>
                            <div class="gradient-label">7.5</div>
                            <div class="gradient-label">9.0</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px; font-size: 0.9rem; color: #666;">
                        <strong>Ideal range:</strong> 5.5–7.0 (yellow)
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with tab4:
            st.subheader("Soil Moisture (%)")
            load_map(map_paths["moisture"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Volumetric Soil Moisture</div>
                    <div class="gradient-legend">
                        <div class="gradient-bar" style="background: linear-gradient(to right, #D2B48C 0%, #B5EC45 25%, #67C528 50%, #298250 75%, #4169E0 100%);"></div>
                        <div class="gradient-labels">
                            <div class="gradient-label">0%</div>
                            <div class="gradient-label">25%</div>
                            <div class="gradient-label">50%</div>
                            <div class="gradient-label">75%</div>
                            <div class="gradient-label">100%</div>
                        </div>
                    </div>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 12px;"><em>Colors represent absolute values (consistent grading across the state)</em></p>
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

    # ========================================================
    # INVESTOR TAB (unchanged)
    # ========================================================
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

            # Show legend for all data types with appropriate labels
            legend_titles = {
                "area": "Planted Crop Area (ha)",
                "production": "Crop Production (tons)",
                "residue": "Available Crop Residue (tons/year)"
            }
            legend_title = legend_titles.get(data_type, "Crop Data")
            
            st.markdown(f"""
                <div class="legend-box">
                    <div class="legend-title">{legend_title}</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#00C85A;"></span>Low (0-25%)</div>
                        <div class="legend-item"><span class="legend-color" style="background:#3F9666;"></span>Low-Moderate (25-50%)</div>
                        <div class="legend-item"><span class="legend-color" style="background:#7F6473;"></span>Moderate-High (50-75%)</div>
                        <div class="legend-item"><span class="legend-color" style="background:#BF327F;"></span>High (75-100%)</div>
                    </div>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 12px;"><em>Colors represent relative values (percentage of maximum in dataset)</em></p>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Crop Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")

else:
    st.info("Select your area and click **Run Analysis** (first run takes 2–6 minutes)")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
