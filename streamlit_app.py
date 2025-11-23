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
            "processing": {"h3_resolution": 7, "enable_clipping": True, "persist_snapshots": False, "cleanup_old_cache": True},
            "gee": {}, "drive": {}
        }
        for key, val in defaults.items():
            if key not in config:
                config[key] = val
        return config
    except:
        st.warning("Using default configuration")
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
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stMarkdown, h1, h2, h3, h4, h5, h6, p, div, span, label {color: #333333 !important; font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #173a30 !important; font-weight: 600 !important;}
    .stApp {background-color: #f8f9fa;}
    .header-title {font-size: 3.2rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem 0; letter-spacing: -1px;}
    .header-subtitle {text-align: center; color: #555; font-size: 1.2rem; margin-bottom: 3rem;}
    section[data-testid="stSidebar"] {background-color: #173a30 !important; padding-top: 2rem;}
    section[data-testid="stSidebar"] * {color: #FFFFFF !important;}
    section[data-testid="stSidebar"] .stButton > button {background-color: #64955d !important; border: none; border-radius: 999px; font-weight: 600;}
    section[data-testid="stSidebar"] .stButton > button:hover {background-color: #527a48 !important;}
    .stButton > button, .stDownloadButton > button {background-color: #64955d !important; color: white !important; border-radius: 999px; font-weight: 600; border: none;}
    .stButton > button:hover, .stDownloadButton > button:hover {background-color: #527a48 !important;}
    .metric-card {background: white; padding: 1.8rem; border-radius: 12px; border-left: 6px solid #64955d; box-shadow: 0 4px 15px rgba(0,0,0,0.08); transition: all 0.2s;}
    .metric-card:hover {transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.12);}
    .metric-card h4 {margin: 0 0 0.8rem 0; color: #173a30; font-weight: 600; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 0.8px;}
    .metric-card p {margin: 0; font-size: 2.6rem; font-weight: 700; color: #333;}
    .footer {text-align: center; padding: 4rem 0 2rem; color: #666; font-size: 0.95rem; border-top: 1px solid #eee; margin-top: 5rem;}
    .footer strong {color: #173a30;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil & residue mapping for sustainable biochar in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Area")
    use_coords = st.checkbox("Analyze around a point (lat/lon)", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 150, 100, 25)
    
    h3_res = st.slider("H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    
    st.markdown("### Run")
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)
    
    if st.button("Clear Cache & Restart", type="secondary"):
        st.cache_data.clear()
        st.session_state.clear()
        st.success("Cache cleared! Reloading...")
        st.experimental_rerun()

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
if "analysis_running" not in st.session_state: st.session_state.analysis_running = False
if "current_process" not in st.session_state: st.session_state.current_process = None
if "analysis_results" not in st.session_state: st.session_state.analysis_results = None
if "investor_map_loaded" not in st.session_state: st.session_state.investor_map_loaded = False
if "investor_map_available" not in st.session_state: st.session_state.investor_map_available = False

# Check investor data availability once
if not st.session_state.investor_map_loaded:
    boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
    waste_csv_path = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"
    st.session_state.investor_map_available = boundaries_dir.exists() and waste_csv_path.exists()
    st.session_state.investor_map_loaded = True

# ============================================================
# RUN ANALYSIS
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
            st.info("Place your soil raster files (SOC, pH, moisture, etc.) in data/raw/")
            st.session_state.analysis_running = False
            st.stop()

    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    if not wrapper_script.exists():
        st.error("Analysis script not found: scripts/run_analysis.py")
        st.stop()

    cli = [sys.executable, str(wrapper_script), "--h3-resolution", str(h3_res)]
    config_file = PROJECT_ROOT / "configs" / "config.yaml"
    if config_file.exists():
        cli += ["--config", str(config_file)]
    if use_coords and lat and lon and radius:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    progress_bar = st.progress(0)
    log_expander = st.expander("Detailed logs", expanded=False)
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
            log_expander.code("\n".join(logs[-25:]), language="text")
            
            elapsed = int(time.time() - start_time)
            status.markdown(f"**Running analysis...** {elapsed}s elapsed")
            
            line_lower = line.lower()
            if any(x in line_lower for x in ["clip", "mask"]): progress_bar.progress(20)
            if "zonal" in line_lower: progress_bar.progress(45)
            if "h3" in line_lower: progress_bar.progress(65)
            if "scor" in line_lower: progress_bar.progress(85)
            if "sav" in line_lower or "done" in line_lower: progress_bar.progress(100)

        return_code = process.wait()
        st.session_state.current_process = None

        if return_code != 0:
            st.error("Analysis failed")
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
            st.error("Invalid results")
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
# DISPLAY RESULTS
# ============================================================
if st.session_state.analysis_results is not None:
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    if not csv_path.exists():
        st.error("Results disappeared. Please re-run.")
        st.stop()
    
    df = pd.read_csv(csv_path)
    map_paths = {k: Path(v) for k, v in st.session_state.analysis_results["map_paths"].items()}

    farmer_tab, investor_tab = st.tabs([
        "Farmer Perspective – Soil Health & Biochar Recommendations",
        "Investor Perspective – Crop Residue Opportunity"
    ])

    # ========================= FARMER TAB =========================
    with farmer_tab:
        st.markdown("### Soil Health & Biochar Application Recommendations")

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

        # Soil maps with legends
        tab1, tab2, tab3, tab4, rec_tab = st.tabs([
            "Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture", "Top 10 Recommendations"
        ])

        def show_map(tab, title, key, legend_html):
            with tab:
                st.subheader(title)
                path = map_paths.get(key)
                if path and path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=680, scrolling=False)
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(legend_html, unsafe_allow_html=True)
                else:
                    st.warning(f"Map not found: {path}")

        show_map(tab1, "Biochar Application Suitability", "suitability", """
            <div style="background:white;padding:16px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-width:650px;margin:0 auto;">
                <h4 style="margin:0;color:#173a30;">Suitability Score (0–10)</h4>
                <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.95rem;margin:10px 0;">
                    <div><span style="display:inline-block;width:24px;height:16px;background:#8B0000;border-radius:4px;"></span> 0–2 Very Low</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#FF4500;"></span> 2–4 Low</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#FFD700;"></span> 4–6 Moderate</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#90EE90;"></span> 6–8 High</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#006400;"></span> 8–10 Very High</div>
                </div>
                <p style="color:#555;font-size:0.9rem;margin:8px 0 0;"><strong>Higher score = better long-term biochar performance</strong></p>
            </div>
        """)

        show_map(tab2, "Soil Organic Carbon (g/kg)", "soc", """
            <div style="background:white;padding:16px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-width:650px;margin:0 auto;">
                <h4 style="margin:0;color:#173a30;">Soil Organic Carbon</h4>
                <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.95rem;">
                    <div><span style="display:inline-block;width:24px;height:16px;background:#FFFFCC;border:1px solid #aaa;"></span> &lt;10 Very Low</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#C7E9B4;"></span> 10–20</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#7FCDBB;"></span> 20–30</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#41B6C4;"></span> 30–40</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#253494;"></span> &gt;50 Very High</div>
                </div>
            </div>
        """)

        show_map(tab3, "Soil pH", "ph", """
            <div style="background:white;padding:16px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-width:650px;margin:0 auto;">
                <h4 style="margin:0;color:#173a30;">Soil pH</h4>
                <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.95rem;">
                    <div><span style="display:inline-block;width:24px;height:16px;background:#8B0000;"></span> &lt;5.0 Strongly Acidic</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#FF6347;"></span> 5.0–5.5 Acidic</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#FFD700;"></span> 5.5–7.0 Ideal</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#87CEEB;"></span> 7.0–8.0 Alkaline</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#000080;"></span> &gt;8.0 Strongly Alkaline</div>
                </div>
            </div>
        """)

        show_map(tab4, "Soil Moisture (%)", "moisture", """
            <div style="background:white;padding:16px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-width:650px;margin:0 auto;">
                <h4 style="margin:0;color:#173a30;">Volumetric Soil Moisture</h4>
                <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.95rem;">
                    <div><span style="display:inline-block;width:24px;height:16px;background:#8B4513;"></span> &lt;10% Very Dry</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#D2691E;"></span> 10–20%</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#F4A460;"></span> 20–30%</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#87CEEB;"></span> 30–40%</div>
                    <div><span style="display:inline-block;width:24px;height:16px;background:#1E90FF;"></span> &gt;40% Very Moist</div>
                </div>
            </div>
        """)

        with rec_tab:
            st.subheader("Top 10 Recommended Locations")
            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)

            if feed_col and reason_col:
                cols = ["h3_index", "suitability_score", "mean_soc", "mean_ph", "mean_moisture", feed_col, reason_col]
                cols = [c for c in cols if c in df.columns]
                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10).round(3)
                rename = {feed_col: "Recommended Feedstock", reason_col: "Rationale", "mean_soc": "SOC (g/kg)", "mean_ph": "pH", "mean_moisture": "Moisture (%)"}
                top10 = top10.rename(columns=rename)
                st.dataframe(top10.style.format({"suitability_score": "{:.2f}", "SOC (g/kg)": "{:.1f}", "pH": "{:.2f}", "Moisture (%)": "{:.1%}"}), 
                            use_container_width=True, hide_index=True)
            else:
                st.info("Feedstock recommendations not available in this run.")

        st.download_button("Download Full Results (CSV)", 
                          data=df.to_csv(index=False).encode(), 
                          file_name=f"biochar_results_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
                          mime="text/csv", use_container_width=True)

    # ========================= INVESTOR TAB =========================
    with investor_tab:
        st.markdown("### Crop Residue Availability – Biochar Feedstock Opportunity")

        if not st.session_state.investor_map_available:
            st.warning("Investor map data missing")
            st.info("Required:\n- data/boundaries/BR_Municipios_2024/\n- data/crop_data/Updated_municipality_crop_production_data.csv")
        else:
            try:
                from src.map_generators.pydeck_maps.municipality_waste_map import (
                    prepare_investor_crop_area_geodata, create_municipality_waste_deck
                )

                data_type = st.radio("Display:", ["area", "production", "residue"],
                                   format_func=lambda x: {"area": "Planted Area (ha)", "production": "Production (tons)", "residue": "Residue (tons)"}[x],
                                   horizontal=True)

                gdf = prepare_investor_crop_area_geodata(boundaries_dir, waste_csv_path, simplify_tolerance=0.008)
                deck = create_municipality_waste_deck(gdf, data_type=data_type)
                st.pydeck_chart(deck, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Total Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
                with col2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
                with col3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")

                if data_type == "residue":
                    st.markdown("""
                    <div style="background:white;padding:16px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-width:650px;margin:20px auto;">
                        <h4 style="margin:0;color:#173a30;">Available Crop Residue (tons/year)</h4>
                        <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.95rem;">
                            <div><span style="display:inline-block;width:24px;height:16px;background:#FFFFCC;border:1px solid #aaa;"></span> &lt;10k</div>
                            <div><span style="display:inline-block;width:24px;height:16px;background:#C7E9B4;"></span> 10k–50k</div>
                            <div><span style="display:inline-block;width:24px;height:16px;background:#41B6C4;"></span> 100k–500k</div>
                            <div><span style="display:inline-block;width:24px;height:16px;background:#225EA8;"></span> &gt;500k High Potential</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error("Failed to load investor map")
                if st.checkbox("Show details"):
                    st.code(traceback.format_exc())

# ============================================================
# EMPTY STATE (before first run)
# ============================================================
else:
    st.info("""
    **Welcome!**  
    Select your area of interest on the left → click **Run Analysis**  
    First run takes 2–6 minutes depending on radius and resolution.
    """)
    st.markdown("<br><br>", unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
