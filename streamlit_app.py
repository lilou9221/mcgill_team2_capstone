# ============================================================
# STREAMLIT APP – FINAL POLISHED & LIGHTNING-FAST VERSION + YOUR REQUEST
# ============================================================
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
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
    ("existing_results_checked", False), ("download_attempted", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.config_loader import load_config

# ============================================================
# DATA FILE MANAGEMENT - Downloads from Cloudflare R2
# ============================================================
import requests

R2_BASE_URL = "https://pub-d86172a936014bdc9e794890543c5f66.r2.dev"

# Required files with expected sizes for verification (prevents corrupted downloads)
REQUIRED_FILES = {
    "BR_Municipios_2024.shp": 286858448,
    "BR_Municipios_2024.dbf": 2865036,
    "BR_Municipios_2024.shx": 44684,
    "BR_Municipios_2024.prj": 151,
    "BR_Municipios_2024.cpg": 5,
    "Updated_municipality_crop_production_data.csv": 1605740,
    "brazil_crop_harvest_area_2017-2024.csv": 25409421,
    "residue_ratios.csv": 179,
    "SOC_res_250_b0.tif": 3201905,
    "SOC_res_250_b10.tif": 3163692,
    "soil_moisture_res_250_sm_surface.tif": 58559674,
    "soil_pH_res_250_b0.tif": 5260755,
    "soil_pH_res_250_b10.tif": 5254048,
    "soil_temp_res_250_soil_temp_layer1.tif": 39979898,
}

def check_data_files():
    """Check if required data files exist and are complete."""
    try:
        data_dir = PROJECT_ROOT / "data"
        for filename, expected_size in REQUIRED_FILES.items():
            filepath = data_dir / filename
            if not filepath.exists():
                return False
            # Allow 1% tolerance for size differences
            if filepath.stat().st_size < expected_size * 0.99:
                return False
        return True
    except Exception:
        return False

@st.cache_resource(show_spinner=False)
def download_data_from_r2():
    """Download missing/incomplete data files from Cloudflare R2."""
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    errors = []
    
    for filename, expected_size in REQUIRED_FILES.items():
        dest = data_dir / filename
        
        # Skip if file exists and is complete
        if dest.exists() and dest.stat().st_size >= expected_size * 0.99:
            continue
        
        # Delete incomplete file
        if dest.exists():
            dest.unlink()
        
        url = f"{R2_BASE_URL}/{filename}"
        try:
            # Use longer timeout for large files (10 min for shapefile)
            timeout = 600 if expected_size > 100000000 else 300
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Write with larger chunks for faster download
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1048576):  # 1MB chunks
                    f.write(chunk)
            
            # Verify download
            if dest.stat().st_size >= expected_size * 0.99:
                downloaded.append(filename)
            else:
                errors.append(f"{filename}: incomplete download")
                dest.unlink()
        except requests.exceptions.RequestException as e:
            errors.append(f"{filename}: {e}")
        except Exception as e:
            errors.append(f"{filename}: {e}")
    
    return downloaded, errors

# Auto-download on startup if files are missing or incomplete
if not check_data_files():
    with st.spinner("Downloading data files from cloud storage (this may take a few minutes on first run)..."):
        downloaded, errors = download_data_from_r2()
        if downloaded:
            st.success(f"Downloaded {len(downloaded)} data files.")
        if errors:
            st.error(f"Failed to download {len(errors)} files. Check Streamlit Cloud logs for details.")

@st.cache_data
def get_config():
    try:
        config = load_config()
        defaults = {
            "data": {"raw": "data", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }
        for k, v in defaults.items():
            config.setdefault(k, v)
        return config
    except:
        return {
            "data": {"raw": "data", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }

config = get_config()

# Legacy compatibility
REQUIRED_DATA_FILES = [PROJECT_ROOT / "data" / f for f in REQUIRED_FILES[:6]]

@st.cache_data(ttl=3600, show_spinner=False)
def check_required_files_exist():
    missing = []
    for path in REQUIRED_DATA_FILES:
        if not path.exists() or (path.exists() and path.stat().st_size == 0):
            missing.append(path)
    return len(missing) == 0, missing

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
    st.markdown("### Run Analysis")
    use_coords = st.checkbox("Analyze around a location", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, 7)
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)
    
    st.markdown("---")
    if st.button("Reset Cache & Restart"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# ============================================================
# RUN ANALYSIS PIPELINE (ON DEMAND)
# ============================================================
if run_btn:
    st.session_state.analysis_results = None
    if st.session_state.analysis_running:
        st.warning("Analysis already running. Please wait…")
        st.stop()
    
    # Check if required files exist before running (flat data/ structure)
    data_dir = PROJECT_ROOT / "data"
    tif_files = list(data_dir.glob("*.tif"))
    if len(tif_files) < 5:
        st.error("**Cannot run new analysis: Missing required data files**")
        st.info("""
        **Required data files are missing from the `data/` directory.**
        
        To run a new analysis, you need:
        - At least 5 GeoTIFF files (soil properties) in `data/`
        - Shapefile components for municipality boundaries
        - Crop production data CSV
        
        **Options:**
        - If you have existing analysis results, they will be displayed automatically
        - For new analysis, data files must be available in the deployment environment
        - Contact the administrator to ensure data files are properly deployed
        
        **Note:** Soil data covers Mato Grosso state only.
        """)
        st.stop()
    
    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    if not wrapper_script.exists():
        st.error("Analysis script not found. Analysis feature unavailable.")
        st.stop()
    
    st.session_state.analysis_running = True
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
@st.cache_data(ttl=3600, show_spinner=False)
def load_results_csv(p): 
    return pd.read_csv(p)

@st.cache_data(ttl=3600, show_spinner=False)
def load_html_map(p):
    path = Path(p)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None

if st.session_state.get("analysis_results"):
    analysis_results = st.session_state.analysis_results
    if "csv_path" in analysis_results and "map_paths" in analysis_results:
        csv_path = Path(analysis_results["csv_path"])
        df = load_results_csv(str(csv_path))
        map_paths = analysis_results["map_paths"]
    else:
        # Invalid analysis_results structure, reset it
        st.session_state.analysis_results = None
        csv_path = df = map_paths = None
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

# Create tabs - Streamlit maintains tab state automatically
# Tabs are always created to prevent tab resets on reruns
farmer_tab, investor_tab = st.tabs(["Farmer Perspective", "Investor Perspective"])

# ========================================================
# FARMER TAB – YOUR ORIGINAL + YOUR REQUESTED SOURCING TOOL
# ========================================================
with farmer_tab:
    if csv_path and df is not None and map_paths:
        # === YOUR ORIGINAL MAPS & RECOMMENDATIONS (UNCHANGED) ===
        st.markdown("### Soil Health & Biochar Suitability Insights (Mato Grosso State)")
        
        # Cache expensive calculations to avoid recomputing on every rerun
        @st.cache_data(show_spinner=False)
        def calculate_metrics(df):
            metrics = {"count": len(df)}
            if "suitability_score" in df.columns:
                metrics["mean_score"] = float(df["suitability_score"].mean())
                high = int((df["suitability_score"] >= 7.0).sum())
                metrics["high_count"] = high
                metrics["high_pct"] = float(high / len(df) * 100) if len(df) > 0 else 0.0
            else:
                metrics["mean_score"] = None
                metrics["high_count"] = None
                metrics["high_pct"] = None
            return metrics
        
        metrics = calculate_metrics(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>Hexagons Analyzed</h4><p>{metrics["count"]:,}</p></div>', unsafe_allow_html=True)
        with col2:
            if metrics["mean_score"] is not None:
                st.markdown(f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>{metrics["mean_score"]:.2f}</p></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="metric-card"><h4>Mean Suitability Score</h4><p>N/A</p></div>', unsafe_allow_html=True)
        with col3:
            if metrics["high_count"] is not None:
                st.markdown(f'<div class="metric-card"><h4>High Suitability (≥7.0)</h4><p>{metrics["high_count"]:,}<br><small>({metrics["high_pct"]:.1f}%)</small></p></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="metric-card"><h4>High Suitability (≥7.0)</h4><p>N/A</p></div>', unsafe_allow_html=True)

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
            if map_paths and "suitability" in map_paths:
                load_map(map_paths["suitability"])
            else:
                st.warning("Suitability map not available.")
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
            if map_paths and "soc" in map_paths:
                load_map(map_paths["soc"])
            else:
                st.warning("Soil Organic Carbon map not available.")
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
            if map_paths and "ph" in map_paths:
                load_map(map_paths["ph"])
            else:
                st.warning("Soil pH map not available.")
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
            if map_paths and "moisture" in map_paths:
                load_map(map_paths["moisture"])
            else:
                st.warning("Soil Moisture map not available.")
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
                    
                    # Show top 10 by suitability score (cached calculation)
                    @st.cache_data(show_spinner=False)
                    def get_top10_recommendations(rec_df):
                        display_cols = ["suitability_score", "suitability_grade", "Recommended_Feedstock", "Recommendation_Reason"]
                        if "Data_Source" in rec_df.columns and "Data_Quality" in rec_df.columns:
                            display_cols.extend(["Data_Source", "Data_Quality"])
                        if "lat" in rec_df.columns and "lon" in rec_df.columns:
                            display_cols.extend(["lat", "lon"])
                        
                        display_cols = [c for c in display_cols if c in rec_df.columns]
                        if "suitability_score" in display_cols:
                            top10 = rec_df[display_cols].sort_values("suitability_score", ascending=False).head(10)
                        elif display_cols:
                            top10 = rec_df[display_cols].head(10)
                        else:
                            top10 = rec_df.head(10)
                        
                        # Format the dataframe for display
                        top10_display = top10.copy()
                        if "suitability_score" in top10_display.columns:
                            top10_display["suitability_score"] = top10_display["suitability_score"].round(2)
                        if "lat" in top10_display.columns and "lon" in top10_display.columns:
                            top10_display["lat"] = top10_display["lat"].round(4)
                            top10_display["lon"] = top10_display["lon"].round(4)
                        return top10_display
                    
                    st.markdown("### Top 10 Recommended Locations (by Suitability Score)")
                    top10_display = get_top10_recommendations(rec_df)
                    
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
                    
                    # Show feedstock distribution (cached)
                    @st.cache_data(show_spinner=False)
                    def get_feedstock_counts(rec_df):
                        return rec_df["Recommended_Feedstock"].value_counts()
                    
                    st.markdown("### Feedstock Distribution")
                    feedstock_counts = get_feedstock_counts(rec_df)
                    st.bar_chart(feedstock_counts)
                else:
                    st.info("No biochar recommendations available. All locations show 'No recommendation'.")
            else:
                st.info("Biochar feedstock recommendations not available in this run. Please run the analysis with recommendations enabled.")

        # === SOURCING TOOL – CROP RESIDUE & BIOCHAR POTENTIAL ===
        st.markdown("### Sourcing Tool – Crop Residue & Biochar Potential (Mato Grosso only)")

        # Cache data loading functions (moved outside to avoid redefinition on reruns)
        @st.cache_data(ttl=3600, show_spinner=False)
        def load_ratios():
            return pd.read_csv(PROJECT_ROOT / "data" / "residue_ratios.csv")

        @st.cache_data(ttl=3600, show_spinner=False)
        def load_harvest_data():
            return pd.read_csv(PROJECT_ROOT / "data" / "brazil_crop_harvest_area_2017-2024.csv")
        
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
            farmer_yield = st.number_input("Your yield (kg/ha)", min_value=0, value=None, step=100, key="sourcing_yield", help="Leave empty to use default yield from crop data")

        if st.button("Calculate Biochar Potential", type="primary", key="calc_sourcing"):
            # Load data only when button is clicked (lazy loading)
            with st.spinner("Loading crop data..."):
                ratios = load_ratios()
                harvest = load_harvest_data()
            try:
                crop_portuguese, crop_english = crop_mapping[crop]
                
                # Filter for Mato Grosso municipalities (optimized: filter by state first)
                df_crop = harvest[
                    (harvest["Crop"] == crop_portuguese) & 
                    harvest["Municipality"].str.contains("\\(MT\\)", na=False, regex=True)
                ].copy()
                
                # Early exit if no data
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
                display_cols = ["Municipality", "Harvested_area_ha", "Biochar_t_per_ha", "Biochar_t_total"]
                display_cols = [c for c in display_cols if c in df_crop.columns]
                if display_cols:
                    display = df_crop[display_cols].head(50)
                    display = display.rename(columns={
                        "Harvested_area_ha": "Area (ha)",
                        "Biochar_t_per_ha": "Biochar (t/ha)",
                        "Biochar_t_total": "Total Biochar (tons)"
                    })
                    st.dataframe(display, use_container_width=True)
                else:
                    st.warning("Required columns not found in crop data.")
                
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

        if csv_path and df is not None:
            # Cache CSV encoding to avoid recomputation on every rerun
            @st.cache_data(show_spinner=False)
            def get_csv_data(df):
                return df.to_csv(index=False).encode()
            
            csv_data = get_csv_data(df)
            st.download_button("Download Full Results (CSV)", csv_data, f"biochar_results_{pd.Timestamp.now():%Y%m%d_%H%M}.csv", "text/csv", use_container_width=True)
    else:
        st.info("Run the analysis to view results.")

# ========================================================
# INVESTOR TAB - Independent feature, loads automatically
# ========================================================
with investor_tab:
    st.markdown("### Crop Residue Availability – Biochar Feedstock Opportunity")

    # Flat structure: shapefile components and CSV are directly in data/
    # These are independent of analysis results - investor map uses different data
    boundaries_dir = PROJECT_ROOT / "data"
    crop_data_csv = PROJECT_ROOT / "data" / "Updated_municipality_crop_production_data.csv"

    # Check file existence (no cache - cheap operation, needs to be accurate after downloads)
    def check_investor_data_exists():
        shp_file = boundaries_dir / "BR_Municipios_2024.shp"
        shp_exists = shp_file.exists()
        csv_exists = crop_data_csv.exists()
        return shp_exists and csv_exists, shp_exists, csv_exists

    # Automatically load and display investor map when data is available
    # This is completely independent of the analysis pipeline
    try:
        from src.map_generators.pydeck_maps.municipality_waste_map import (
            prepare_investor_crop_area_geodata,
            create_municipality_waste_deck,
        )
        
        data_available, shp_exists, csv_exists = check_investor_data_exists()
        
        if data_available:
            @st.cache_data(show_spinner=False)
            def get_gdf():
                    return prepare_investor_crop_area_geodata(
                        boundaries_dir,
                        crop_data_csv,
                        simplify_tolerance=0.05
                    )

            with st.spinner("Loading crop residue data (first time only)..."):
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
                if 'total_crop_area_ha' in gdf.columns:
                    st.metric("Total Crop Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
                else:
                    st.metric("Total Crop Area", "N/A")
            with c2: 
                if 'total_crop_production_ton' in gdf.columns:
                    st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
                else:
                    st.metric("Total Production", "N/A")
            with c3: 
                if 'total_crop_residue_ton' in gdf.columns:
                    st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")
                else:
                    st.metric("Total Residue", "N/A")
        else:
            missing = []
            if not shp_exists:
                missing.append("BR_Municipios_2024.shp (shapefile)")
            if not csv_exists:
                missing.append("Updated_municipality_crop_production_data.csv")
            st.info(f"Investor map data not available. Missing: {', '.join(missing)}")
    except Exception as e:
        import traceback
        st.error(f"Failed to load investor map: {str(e)}")
        st.code(traceback.format_exc(), language="text")

# ============================================================
# FOOTER (YOUR ORIGINAL)
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
