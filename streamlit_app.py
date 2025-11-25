# ============================================================
# STREAMLIT APP – FINAL POLISHED & LIGHTNING-FAST VERSION + YOUR REQUEST
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
    ("analysis_running", False), ("current_process", None), ("analysis_results", None),
    ("data_downloaded", False), ("existing_results_checked", False),
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
DOWNLOAD_SCRIPT = PROJECT_ROOT / "scripts" / "download_assets.py"
REQUIRED_DATA_FILES = [
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.shp",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.dbf",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.shx",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.prj",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.cpg",
    PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv",
    PROJECT_ROOT / "data" / "raw" / "SOC_res_250_b0.tif",
    PROJECT_ROOT / "data" / "raw" / "SOC_res_250_b10.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_moisture_res_250_sm_surface.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_pH_res_250_b0.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_pH_res_250_b10.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_temp_res_250_soil_temp_layer1.tif",
]

@st.cache_data(ttl=3600)
def check_required_files_exist():
    missing = []
    for path in REQUIRED_DATA_FILES:
        if not path.exists() or (path.exists() and path.stat().st_size == 0):
            missing.append(path)
    return len(missing) == 0, missing

def ensure_required_data():
    if st.session_state.get("data_downloaded", False):
        return
    all_exist, missing = check_required_files_exist()
    if all_exist:
        st.session_state["data_downloaded"] = True
        return
    status_placeholder = st.empty()
    status_placeholder.info("Downloading required geo datasets from Google Drive (first run only). This may take a few minutes.\n\n**Note:** Soil data covers Mato Grosso state only.")
    if not DOWNLOAD_SCRIPT.exists():
        status_placeholder.empty()
        st.error("Download script missing. Please run `scripts/download_assets.py` manually.")
        st.stop()
    
    result = None
    try:
        result = subprocess.run(
            [sys.executable, str(DOWNLOAD_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            env=os.environ.copy()
        )
        
        # Always show download output for debugging
        if result.stdout:
            print(f"[DOWNLOAD STDOUT]\n{result.stdout}", flush=True)
        if result.stderr:
            print(f"[DOWNLOAD STDERR]\n{result.stderr}", flush=True)
        
        if result.returncode != 0:
            status_placeholder.empty()
            st.error("Automatic data download failed.")
            
            # Check for Google Drive blocking/rate limiting issues
            error_output = (result.stderr or "") + (result.stdout or "")
            if any(keyword in error_output.lower() for keyword in ["403", "forbidden", "rate limit", "blocked", "access denied", "quota"]):
                st.warning("""
                **Google Drive Access Issue Detected**
                
                Google Drive downloads may be blocked or rate-limited on Streamlit Cloud servers. 
                This is a known limitation when accessing Google Drive from cloud hosting platforms.
                
                **Solutions:**
                1. **Manual Download (Recommended):** Download the data files manually from the Google Drive folder and place them in the project directory.
                2. **Alternative Hosting:** Consider using alternative file hosting (AWS S3, GitHub Releases, etc.) for production deployments.
                3. **Local Development:** The download works fine when running locally.
                
                **Required Files:**
                - Shapefiles: `data/boundaries/BR_Municipios_2024/` (all .shp, .dbf, .shx, .prj, .cpg files)
                - Crop Data: `data/crop_data/Updated_municipality_crop_production_data.csv`
                - Soil Data (Mato Grosso only): `data/raw/*.tif` (6 GeoTIFF files)
                """)
            
            st.code(f"Exit code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
            st.stop()
    except subprocess.TimeoutExpired:
        status_placeholder.empty()
        st.error("Data download timed out after 10 minutes.")
        st.warning("""
        **Possible Causes:**
        - Google Drive rate limiting on Streamlit Cloud
        - Network connectivity issues
        - Large file sizes taking longer than expected
        
        **Note:** Soil data covers Mato Grosso state only. Consider downloading files manually if this persists.
        """)
        if result and result.stdout:
            st.code(result.stdout)
        st.stop()
    except Exception as exc:
        status_placeholder.empty()
        st.error(f"Download failed: {exc}")
        st.warning("""
        **Google Drive Access Issue**
        
        If you're running on Streamlit Cloud, Google Drive downloads may be blocked or rate-limited.
        Please download the data files manually and place them in the project directory.
        
        **Note:** All soil data is for Mato Grosso state only.
        """)
        if result:
            st.code(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
        st.stop()
    
    # Give filesystem time to sync, especially on cloud platforms
    time.sleep(3)
    
    # Clear cache to force re-check
    check_required_files_exist.clear()
    
    status_placeholder.empty()
    all_exist, remaining_missing = check_required_files_exist()
    if not all_exist:
        st.error("Some files still missing after download.")
        st.code("\n".join(str(p) for p in remaining_missing))
        
        # Check if this might be a Google Drive blocking issue
        st.warning("""
        **Possible Google Drive Access Issue**
        
        If you're on Streamlit Cloud, Google Drive downloads may be blocked or rate-limited.
        The download script may have failed silently due to network restrictions.
        
        **Note:** All soil data is for Mato Grosso state only.
        
        **Solutions:**
        1. Download files manually from Google Drive and place them in the project
        2. Check the download script output below for specific error messages
        """)
        
        # Show download script output for debugging
        if result:
            with st.expander("Download script output (for debugging)", expanded=True):
                st.code(f"Exit code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
            st.info(f"**Debug Info:**\n- PROJECT_ROOT: `{PROJECT_ROOT}`\n- PROJECT_ROOT exists: {PROJECT_ROOT.exists()}")
        st.stop()
    st.session_state["data_downloaded"] = True

ensure_required_data()

# ============================================================
# GLOBAL STYLING (100% YOUR ORIGINAL)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, .stApp {font-family: 'Inter', sans-serif; background-color: #FFFFFF !important; color: #000 !important;}
    body, html, .stApp, div, span, p, h1, h2, h3, h4, h5, h6 {color: #000 !important;}
    section[data-testid="stSidebar"] {background-color: #173a30 !important;}
    section[data-testid="stSidebar"] * {color: white !important;}
    .header-title {font-size: 3.4rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem;}
    .header-subtitle {text-align: center; color: #444444; font-size: 1.3rem; margin-bottom: 3rem;}
    .stButton > button {background-color: #64955d !important; color: white !important; border-radius: 999px; font-weight: 600; height: 3.2em;}
    .stButton > button:hover {background-color: #527a48 !important;}
    .metric-card {background: white; padding: 1.8rem; border-radius: 14px; border-left: 6px solid #64955d; box-shadow: 0 6px 20px rgba(0,0,0,0.08); text-align: center;}
    .legend-box {background: white; padding: 28px; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.1); max-width: 760px; margin: 50px auto; text-align: center; border: 1px solid #eee;}
    .legend-title {font-size: 1.3rem; font-weight: 600; color: #173a30; margin-bottom: 16px;}
    .legend-row {display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; margin-top: 16px;}
    .legend-item {display: flex; align-items: center; gap: 8px; font-size: 0.95rem; color: #333;}
    .legend-color {width: 24px; height: 24px; border-radius: 4px; display: inline-block; border: 1px solid #ddd;}
    .gradient-legend {margin: 20px 0;}
    .gradient-bar {height: 30px; border-radius: 6px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);}
    .gradient-labels {display: flex; justify-content: space-between; font-size: 0.85rem; color: #666; margin-top: 4px;}
    .gradient-label {flex: 1; text-align: center;}
    .footer {text-align: center; padding: 6rem 0 3rem; color: #666; border-top: 1px solid #eee; margin-top: 8rem; font-size: 0.95rem;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER & SIDEBAR (YOUR ORIGINAL)
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil health & crop residue intelligence for sustainable biochar in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Analysis Settings")
    use_coords = st.checkbox("Analyze around a location", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, 7)
    run_btn = st.button("Run Analysis", type="primary", width='stretch')
    if st.button("Reset Cache & Restart"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# ============================================================
# RUN ANALYSIS PIPELINE (YOUR ORIGINAL – UNCHANGED)
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
        process = subprocess.Popen(cli, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(PROJECT_ROOT), text=True, bufsize=1)
        st.session_state.current_process = process
        start = time.time()
        for line in process.stdout:
            logs.append(line)
            status.write(f"Running… {int(time.time() - start)}s elapsed")
        rc = process.wait()
        if rc != 0:
            st.error("Pipeline failed.")
            st.code("".join(logs))
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
        st.session_state.analysis_results = {"csv_path": str(csv_path), "map_paths": map_paths}
        st.success("Analysis completed successfully!")
    except Exception as e:
        st.error("Pipeline crashed.")
        st.code(traceback.format_exc())
    finally:
        st.session_state.analysis_running = False

# ============================================================
# LOAD RESULTS (YOUR ORIGINAL)
# ============================================================
csv_path = df = map_paths = None
@st.cache_data(ttl=3600)
def load_results_csv(p): return pd.read_csv(p)
@st.cache_data(ttl=3600)
def load_html_map(p):
    path = Path(p)
    return path.read_text(encoding="utf-8") if path.exists() else None

if st.session_state.get("analysis_results"):
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    df = load_results_csv(str(csv_path))
    map_paths = st.session_state.analysis_results["map_paths"]
elif not st.session_state.get("analysis_running") and not st.session_state.get("existing_results_checked", False):
    potential_csv = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if potential_csv.exists() and Path(PROJECT_ROOT / config["output"]["html"] / "suitability_map.html").exists():
        st.session_state.analysis_results = {
            "csv_path": str(potential_csv),
            "map_paths": {
                "suitability": str(PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"),
                "soc": str(PROJECT_ROOT / config["output"]["html"] / "soc_map_streamlit.html"),
                "ph": str(PROJECT_ROOT / config["output"]["html"] / "ph_map_streamlit.html"),
                "moisture": str(PROJECT_ROOT / config["output"]["html"] / "moisture_map_streamlit.html"),
            }
        }
        csv_path = potential_csv
        df = load_results_csv(str(csv_path))
    map_paths = st.session_state.analysis_results["map_paths"]
    st.session_state["existing_results_checked"] = True

    farmer_tab, investor_tab = st.tabs(["Farmer Perspective", "Investor Perspective"])

# ========================================================
# FARMER TAB – YOUR ORIGINAL + YOUR REQUESTED SOURCING TOOL
# ========================================================
with farmer_tab:
    if csv_path and df is not None and map_paths:
        # === YOUR ORIGINAL MAPS & RECOMMENDATIONS (UNCHANGED) ===
        st.markdown("### Soil Health & Biochar Suitability Insights (Mato Grosso State)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>Hexagons Analyzed</h4><p>{len(df):,}</p></div>', unsafe_allow_html=True)
        with col2:
            mean_score = df["suitability_score"].mean()
            st.markdown(f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>{mean_score:.2f}</p></div>', unsafe_allow_html=True)
        with col3:
            high = (df["suitability_score"] >= 7.0).sum()
            pct = high / len(df) * 100
            st.markdown(f'<div class="metric-card"><h4>High Suitability (≥7.0)</h4><p>{high:,}<br><small>({pct:.1f}%)</small></p></div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4, rec_tab = st.tabs(["Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture", "Top 10 Recommendations"])

        def load_map(path):
            """Load and display HTML map. Uses cached content."""
            html_content = load_html_map(path)
            if html_content:
                st.components.v1.html(html_content, height=720, scrolling=False)
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
            st.subheader("Soil Organic Carbon (g/kg) - Mato Grosso State")
            load_map(map_paths["soc"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil Organic Carbon (Mato Grosso State)</div>
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
                    <div style="margin-top: 12px; font-size: 0.9rem; color: #666;">
                        <strong>Quality Thresholds (g/kg):</strong><br>
                        &lt; 10 g/kg (Very Poor) | 10-20 g/kg (Poor) | 20-40 g/kg (Moderate) | ≥ 40 g/kg (Good)<br>
                        <em>Optimal: ≥ 40 g/kg (≥ 4%)</em>
                    </div>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 8px;"><em>Colors represent absolute values (consistent grading across the state)</em></p>
                </div>
            """, unsafe_allow_html=True)

        with tab3:
            st.subheader("Soil pH - Mato Grosso State")
            load_map(map_paths["ph"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Soil pH (Mato Grosso State)</div>
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
                        <strong>Quality Thresholds:</strong><br>
                        &lt; 3.0 or &gt; 9.0 (Very Poor) | 3.0-4.5 or 8.0-9.0 (Poor) | 4.5-6.0 or 7.0-8.0 (Moderate) | 6.0-7.0 (Good)<br>
                        <em>Optimal range: 6.0-7.0 (yellow)</em>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with tab4:
            st.subheader("Soil Moisture (%) - Mato Grosso State")
            load_map(map_paths["moisture"])
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Volumetric Soil Moisture (Mato Grosso State)</div>
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
                    <div style="margin-top: 12px; font-size: 0.9rem; color: #666;">
                        <strong>Quality Thresholds:</strong><br>
                        &lt; 20% or &gt; 80% (Very Poor) | 20-30% or 70-80% (Poor) | 30-50% or 60-70% (Moderate) | 50-60% (Good)<br>
                        <em>Optimal range: 50-60%</em>
                    </div>
                    <p style="font-size: 0.9rem; color: #666; margin-top: 8px;"><em>Colors represent absolute values (consistent grading across the state)</em></p>
                </div>
            """, unsafe_allow_html=True)

        with rec_tab:
            st.subheader("Biochar Feedstock Recommendations")
            
            # Check if recommendation columns exist
            if "Recommended_Feedstock" in df.columns and "Recommendation_Reason" in df.columns:
                # Filter out rows without recommendations
                rec_df = df[df["Recommended_Feedstock"].notna() & (df["Recommended_Feedstock"] != "No recommendation")].copy()
                
                if len(rec_df) > 0:
                    # Show summary statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        unique_feedstocks = rec_df["Recommended_Feedstock"].nunique()
                        st.metric("Unique Feedstocks Recommended", unique_feedstocks)
                    with col2:
                        total_locations = len(rec_df)
                        st.metric("Locations with Recommendations", f"{total_locations:,}")
                    with col3:
                        if "Data_Quality" in rec_df.columns:
                            high_quality = (rec_df["Data_Quality"] == "high").sum()
                            st.metric("High Quality Data", f"{high_quality:,} ({high_quality/total_locations*100:.1f}%)")
                    
                    # Show top 10 by suitability score
                    st.markdown("### Top 10 Recommended Locations (by Suitability Score)")
                    display_cols = ["suitability_score", "suitability_grade", "Recommended_Feedstock", "Recommendation_Reason"]
                    if "Data_Source" in rec_df.columns and "Data_Quality" in rec_df.columns:
                        display_cols.extend(["Data_Source", "Data_Quality"])
                    if "lat" in rec_df.columns and "lon" in rec_df.columns:
                        display_cols.extend(["lat", "lon"])
                    
                    display_cols = [c for c in display_cols if c in rec_df.columns]
                    top10 = rec_df[display_cols].sort_values("suitability_score", ascending=False).head(10)
                    
                    # Format the dataframe for display
                    top10_display = top10.copy()
                    if "suitability_score" in top10_display.columns:
                        top10_display["suitability_score"] = top10_display["suitability_score"].round(2)
                    if "lat" in top10_display.columns and "lon" in top10_display.columns:
                        top10_display["lat"] = top10_display["lat"].round(4)
                        top10_display["lon"] = top10_display["lon"].round(4)
                    
                    # Rename columns for better display
                    rename_map = {
                        "suitability_score": "Suitability Score",
                        "suitability_grade": "Grade",
                        "Recommended_Feedstock": "Recommended Feedstock",
                        "Recommendation_Reason": "Reason",
                        "Data_Source": "Data Source",
                        "Data_Quality": "Data Quality",
                        "lat": "Latitude",
                        "lon": "Longitude"
                    }
                    top10_display = top10_display.rename(columns=rename_map)
                    
                    st.dataframe(top10_display, use_container_width=True, hide_index=True)
                    
                    # Show feedstock distribution
                    st.markdown("### Feedstock Distribution")
                    feedstock_counts = rec_df["Recommended_Feedstock"].value_counts()
                    st.bar_chart(feedstock_counts)
                else:
                    st.info("No biochar recommendations available. All locations show 'No recommendation'.")
            else:
                st.info("Biochar feedstock recommendations not available in this run. Please run the analysis with recommendations enabled.")

        # === SOURCING TOOL – CROP RESIDUE & BIOCHAR POTENTIAL ===
        st.markdown("### Sourcing Tool – Crop Residue & Biochar Potential (Mato Grosso only)")

        @st.cache_data(ttl=3600)
        def load_ratios():
            return pd.read_csv(PROJECT_ROOT / "data" / "raw" / "residue_ratios.csv")

        @st.cache_data(ttl=3600)
        def load_harvest_data():
            return pd.read_csv(PROJECT_ROOT / "data" / "raw" / "brazil_crop_harvest_area_2017-2024.csv")

        ratios = load_ratios()
        
        # Mapping: English crop name -> (Portuguese name in harvest file, English name in ratios file)
        crop_mapping = {
            "Soybean": ("Soja (em grão)", "Soybeans (grain)"),
            "Maize": ("Milho (em grão)", "Corn (grain)"),
            "Sugarcane": ("Cana-de-açúcar", "Sugarcane"),
            "Cotton": ("Algodão herbáceo (em caroço)", "Herbaceous cotton (seed)")
        }

        col1, col2 = st.columns(2)
        with col1:
            crop = st.selectbox("Select crop", options=list(crop_mapping.keys()), key="sourcing_crop")
        with col2:
            farmer_yield = st.number_input("Your yield (kg/ha) – optional", min_value=0, value=None, step=100, key="sourcing_yield")

        if st.button("Calculate Biochar Potential", type="primary", key="calc_sourcing"):
            try:
                harvest = load_harvest_data()
                crop_portuguese, crop_english = crop_mapping[crop]
                
                # Filter for Mato Grosso municipalities
                df_crop = harvest[
                    (harvest["Crop"] == crop_portuguese) & 
                    harvest["Municipality"].str.contains("\\(MT\\)", na=False, regex=True)
                ].copy()
                
                if df_crop.empty:
                    st.error(f"No data found for {crop} in Mato Grosso. Please check the crop data file.")
                    st.stop()
                
                latest_year = df_crop["Year"].max()
                df_crop = df_crop[df_crop["Year"] == latest_year].copy()
                
                if df_crop.empty:
                    st.error(f"No data found for {crop} in Mato Grosso for year {latest_year}.")
                    st.stop()

                # Look up residue ratio from ratios file
                ratio_row = ratios[ratios["Crop"] == crop_english]
                if ratio_row.empty:
                    st.error(f"Residue ratio not found for {crop} ({crop_english}) in ratios file.")
                    st.stop()
                
                ratio_row = ratio_row.iloc[0]
                urr = ratio_row["URR (t residue/t grain) Assuming AF = 0.5"] if pd.notna(ratio_row["URR (t residue/t grain) Assuming AF = 0.5"]) else ratio_row["Doesn't require AF"]
                
                if pd.isna(urr):
                    st.error(f"Residue ratio (URR) not available for {crop}.")
                    st.stop()

                # Calculate biochar potential
                yield_used = farmer_yield if farmer_yield is not None else 3500  # Default yield if not provided
                residue_t_ha = (yield_used / 1000) * urr
                biochar_t_ha = residue_t_ha * 0.30  # 30% pyrolysis yield

                df_crop["Residue_t_total"] = residue_t_ha * df_crop["Harvested_area_ha"]
                df_crop["Biochar_t_total"] = biochar_t_ha * df_crop["Harvested_area_ha"]
                df_crop["Biochar_t_per_ha"] = biochar_t_ha

                total_biochar = df_crop["Biochar_t_total"].sum()
                total_residue = df_crop["Residue_t_total"].sum()
                
                st.success(f"{latest_year} • {len(df_crop)} municipalities • Total biochar: {total_biochar:,.0f} tons • Total residue: {total_residue:,.0f} tons")

                # Display top municipalities
                display = df_crop[["Municipality", "Harvested_area_ha", "Biochar_t_per_ha", "Biochar_t_total"]].head(50)
                display = display.rename(columns={
                    "Harvested_area_ha": "Area (ha)",
                    "Biochar_t_per_ha": "Biochar (t/ha)",
                    "Biochar_t_total": "Total Biochar (tons)"
                })
                st.dataframe(display, use_container_width=True)
                
                # Show summary info
                with st.expander("Calculation Details", expanded=False):
                    st.write(f"**Crop:** {crop}")
                    st.write(f"**Year:** {latest_year}")
                    st.write(f"**Yield used:** {yield_used:,.0f} kg/ha {'(user input)' if farmer_yield is not None else '(default)'}")
                    st.write(f"**Residue ratio (URR):** {urr:.3f} t residue/t grain")
                    st.write(f"**Residue per hectare:** {residue_t_ha:.2f} t/ha")
                    st.write(f"**Biochar per hectare:** {biochar_t_ha:.2f} t/ha (30% pyrolysis yield)")
                    st.write(f"**Total harvested area:** {df_crop['Harvested_area_ha'].sum():,.0f} ha")
                
                st.download_button(
                    "Download full table", 
                    df_crop.to_csv(index=False).encode(), 
                    f"MT_{crop}_biochar_{latest_year}.csv", 
                    "text/csv",
                    key="dl_sourcing"
                )
            except Exception as e:
                st.error(f"Error calculating biochar potential: {str(e)}")
                import traceback
                with st.expander("Error Details", expanded=False):
                    st.code(traceback.format_exc())

        st.download_button("Download Full Results (CSV)", df.to_csv(index=False).encode(), f"biochar_results_{pd.Timestamp.now():%Y%m%d_%H%M}.csv", "text/csv", width='stretch')
    else:
        st.info("Run the analysis to view results.")

# ========================================================
# INVESTOR TAB
# ========================================================
with investor_tab:
    # Use container to isolate widget interactions and prevent tab resets
    investor_container = st.container()
    with investor_container:
        st.markdown("### Crop Residue Availability – Biochar Feedstock Opportunity")

        boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
        crop_data_csv = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"

        # Cache file existence checks
        @st.cache_data(ttl=3600)
        def check_investor_data_exists():
            return boundaries_dir.exists() and crop_data_csv.exists()

        if not check_investor_data_exists():
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
                    crop_data_csv,
                    simplify_tolerance=0.05
                )

            gdf = get_gdf()

            # Use a unique, stable key to prevent tab resets when radio button changes
            data_type_radio = st.radio(
                "Display:",
                ["Crop area", "Crop production", "Crop residue"],
                format_func=lambda x: {"Crop area":"Crop Area (ha)", "Crop production":"Crop Production (tons)", "Crop residue":"Crop Residue (tons)"}[x],
                horizontal=True,
                key="investor_pov_data_type_radio"
            )
            
            # Map radio button values to function parameter values
            data_type_map = {
                "Crop area": "area",
                "Crop production": "production",
                "Crop residue": "residue"
            }
            data_type = data_type_map.get(data_type_radio, "area")

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
            with c1: 
                st.metric("Total Crop Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: 
                st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: 
                st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")

# ============================================================
# FOOTER (YOUR ORIGINAL)
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
