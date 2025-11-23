# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import os
import time
import traceback
import yaml
import pydeck as pdk

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config_loader import load_config

@st.cache_data
def get_config():
    """
    Load configuration with fallback system.
    Works with local data files only - no cloud services required.
    """
    try:
        config = load_config()
        
        # Ensure all required sections exist with defaults
        if "data" not in config:
            config["data"] = {"raw": "data/raw", "processed": "data/processed", "external": "data/external"}
        if "output" not in config:
            config["output"] = {"maps": "output/maps", "html": "output/html"}
        if "processing" not in config:
            config["processing"] = {"h3_resolution": 7, "enable_clipping": True, "persist_snapshots": False, "cleanup_old_cache": True}
        if "gee" not in config:
            config["gee"] = {}
        if "drive" not in config:
            config["drive"] = {}
        
        return config
    except Exception as e:
        # Even if config loading fails, provide minimal defaults
        st.warning(f"Using default configuration: {e}")
        return {
            "data": {"raw": "data/raw", "processed": "data/processed", "external": "data/external"},
            "output": {"maps": "output/maps", "html": "output/html"},
            "processing": {"h3_resolution": 7, "enable_clipping": True, "persist_snapshots": False, "cleanup_old_cache": True},
            "gee": {},
            "drive": {}
        }

config = get_config()

st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS (unchanged)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stMarkdown, h1, h2, h3, h4, h5, h6, p, div, span, label, .css-1d391kg, .css-1cpxqw2 {color: #333333 !important;}
    h2, h3 {color: #173a30 !important; font-weight: 600 !important;}
    html, body, .stApp {font-family: 'Inter', sans-serif;}
    .stApp {background-color: #f0f0f0;}
    .header-title {font-size: 3rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem 0; letter-spacing: -0.8px;}
    .header-subtitle {text-align: center; color: #333333; font-size: 1.15rem; margin-bottom: 3rem;}
    section[data-testid="stSidebar"] {background-color: #173a30 !important; padding-top: 2rem;}
    section[data-testid="stSidebar"] * {color: #FFFFFF !important;}
    section[data-testid="stSidebar"] .stButton > button {background-color: #4f1c53 !important; color: #FFFFFF !important; border-radius: 999px !important; font-weight: 600 !important;}
    section[data-testid="stSidebar"] .stButton > button:hover {background-color: #3d163f !important;}
    .stButton > button, .stDownloadButton > button {background-color: #64955d !important; color: #FFFFFF !important; border-radius: 999px !important; font-weight: 600 !important; border: none !important;}
    .stButton > button:hover, .stDownloadButton > button:hover {background-color: #527a48 !important;}
    .metric-card {background: #FFFFFF; padding: 1.8rem; border-radius: 12px; border-left: 6px solid #64955d; box-shadow: 0 4px 15px rgba(0,0,0,0.08);}
    .metric-card:hover {transform: translateY(-4px);}
    .metric-card h4 {margin: 0 0 0.8rem 0; color: #173a30; font-weight: 600; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 0.8px;}
    .metric-card p {margin: 0; font-size: 2.5rem; font-weight: 700; color: #333333;}
    .footer {text-align: center; padding: 3rem 0 2rem; color: #333333; font-size: 0.95rem; border-top: 1px solid #ddd; margin-top: 4rem;}
    .footer strong {color: #173a30;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze area around a point", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# ============================================================
# MAIN PIPELINE
# ============================================================
# Use session state to track if analysis is running and store results
if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False
if "current_process" not in st.session_state:
    st.session_state.current_process = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None  # Will store: {"df": df, "map_paths": {...}}
if "investor_map_loaded" not in st.session_state:
    st.session_state.investor_map_loaded = False  # Track if we've tried to load it
if "investor_map_available" not in st.session_state:
    st.session_state.investor_map_available = False  # Track if data files exist

# ============================================================
# Check investor map availability (lightweight check, no heavy objects stored)
# ============================================================
if not st.session_state.investor_map_loaded:
    boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
    waste_csv_path = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"
    st.session_state.investor_map_available = boundaries_dir.exists() and waste_csv_path.exists()
    st.session_state.investor_map_loaded = True

if run_btn:
    # Clear previous results when starting new analysis
    st.session_state.analysis_results = None
    # Prevent multiple simultaneous runs
    if st.session_state.analysis_running:
        st.warning("Analysis is already running. Please wait for it to complete.")
        st.stop()
    
    # Set running flag
    st.session_state.analysis_running = True
    
    # (your entire pipeline code stays 100% unchanged until here)
    with st.spinner("Preparing data…"):
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)
        # Check for local GeoTIFF files
        tif_files = list(raw_dir.glob("*.tif"))
        if len(tif_files) < 5:
            st.error("No GeoTIFF files found in data/raw/ directory.")
            st.info("Please ensure GeoTIFF data files are manually placed in the data/raw/ directory.")
            st.session_state.analysis_running = False
            st.stop()
        else:
            st.info("Using local GeoTIFF files from data/raw/ directory.")

    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    
    # Verify script exists
    if not wrapper_script.exists():
        st.error(f"Analysis script not found: {wrapper_script}")
        st.info("Please ensure scripts/run_analysis.py exists in the project root.")
        st.stop()
    
    # Build command line - config is optional (will use defaults if not found)
    config_file = PROJECT_ROOT / "configs" / "config.yaml"
    cli = [sys.executable, str(wrapper_script), "--h3-resolution", str(h3_res)]
    
    # Only add config if it exists, otherwise use defaults (config_loader will handle it)
    if config_file.exists():
        cli += ["--config", str(config_file)]
    # If config.yaml doesn't exist, don't pass --config, let it use defaults
    
    if use_coords and lat and lon and radius:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    log_box = st.empty()
    logs = []
    
    # Ensure working directory is project root for subprocess
    try:
        # Ensure Python path includes project root for imports
        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        if str(PROJECT_ROOT) not in python_path:
            env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{python_path}" if python_path else str(PROJECT_ROOT)
        
        process = subprocess.Popen(
            cli, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for simpler handling
            text=True, 
            bufsize=1, 
            universal_newlines=True,
            cwd=str(PROJECT_ROOT),  # Set working directory to project root
            env=env  # Pass environment with PYTHONPATH
        )
        # Store process in session state for potential cleanup
        st.session_state.current_process = process
        start = time.time()
        
        # Read output line by line with timeout handling
        try:
            for line in process.stdout:
                if line:
                    logs.append(line)
                    elapsed = int(time.time()-start)
                    # Use custom styled box with white text
                    status.markdown(
                        f'<div style="background-color: #0E6BA8; padding: 0.75rem 1rem; border-radius: 0.5rem; color: white; font-weight: 500;">Running… {elapsed}s elapsed</div>',
                        unsafe_allow_html=True
                    )
                    # Show last 20 lines for better debugging
                    log_box.code("".join(logs[-20:]), language="bash")
        except Exception as read_error:
            logs.append(f"\n[Error reading subprocess output: {read_error}]\n")
        finally:
            # Ensure process is properly closed
            if process.stdout:
                process.stdout.close()
        
        return_code = process.wait()
        # Clear process from session state
        st.session_state.current_process = None
        
        if return_code != 0:
            st.error("Pipeline failed.")
            error_msg = "".join(logs)
            if not error_msg.strip():
                error_msg = "No output captured. Check that all dependencies are installed and data files are present."
            st.code(error_msg, language="bash")
            st.expander("Full Error Details", expanded=False).code(error_msg, language="bash")
            st.session_state.analysis_running = False
            st.stop()
        
        # Check results file after subprocess completes successfully
        csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
        if not csv_path.exists():
            st.error("Results missing.")
            st.info(f"Expected file: {csv_path}")
            st.info("The analysis pipeline may have failed. Check the error messages above.")
            st.session_state.analysis_running = False
            st.stop()

        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                st.error("Results file is empty.")
                st.session_state.analysis_running = False
                st.stop()
            # Verify required column exists
            if "suitability_score" not in df.columns:
                st.error("Results file missing 'suitability_score' column.")
                st.info(f"Available columns: {', '.join(df.columns)}")
                st.session_state.analysis_running = False
                st.stop()
        except Exception as e:
            st.error(f"Failed to read results file: {e}")
            st.info(f"File path: {csv_path}")
            st.session_state.analysis_running = False
            st.stop()
        
        # Store results path in session state for persistence (not the DataFrame itself to save memory)
        map_paths = {
            "suitability": str(PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"),
            "soc": str(PROJECT_ROOT / config["output"]["html"] / "soc_map_streamlit.html"),
            "ph": str(PROJECT_ROOT / config["output"]["html"] / "ph_map_streamlit.html"),
            "moisture": str(PROJECT_ROOT / config["output"]["html"] / "moisture_map_streamlit.html"),
        }
        csv_path_str = str(csv_path)
        st.session_state.analysis_results = {
            "csv_path": csv_path_str,
            "map_paths": map_paths
        }
        
        # Reset running flag on successful completion
        st.session_state.analysis_running = False
        st.success("Analysis completed successfully!")
        
    except FileNotFoundError as e:
        st.error(f"Failed to find required file or script: {e}")
        st.info(f"Looking for: {wrapper_script}")
        st.info(f"Python executable: {sys.executable}")
        st.session_state.analysis_running = False
        st.session_state.current_process = None
        st.stop()
    except Exception as e:
        st.error(f"Failed to start pipeline: {e}")
        import traceback
        error_details = traceback.format_exc()
        st.code(error_details, language="python")
        st.expander("Full Error Traceback", expanded=False).code(error_details, language="python")
        st.session_state.analysis_running = False
        st.session_state.current_process = None
        st.stop()
    finally:
        # Always reset running flag when done (success or failure)
        # This ensures the flag is reset even if an exception occurs
        if "analysis_running" in st.session_state:
            st.session_state.analysis_running = False

# ============================================================
# DISPLAY RESULTS (from cache if available, or from new analysis)
# ============================================================
if st.session_state.analysis_results is not None:
    # Read DataFrame from CSV file (not stored in memory to save space)
    csv_path = Path(st.session_state.analysis_results["csv_path"])
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            st.error(f"Failed to read cached results: {e}")
            st.session_state.analysis_results = None
            st.stop()
    else:
        st.warning("Cached results file no longer exists.")
        st.session_state.analysis_results = None
        st.stop()
    
    # Convert map paths back to Path objects
    map_paths = {k: Path(v) for k, v in st.session_state.analysis_results["map_paths"].items()}
    
    # ============================================================
    # METRICS
    # ============================================================
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <h4>Total Hexagons Analyzed</h4>
            <p>{len(df):,}</p>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        mean_score = df["suitability_score"].mean() if "suitability_score" in df.columns else 0.0
        st.markdown(f'''
        <div class="metric-card">
            <h4>Mean Suitability Score<br>
                <small style="color:#173a30; font-weight:500;">(scale: 0–10)</small>
            </h4>
            <p>{mean_score:.2f}</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        if "suitability_score" in df.columns:
            mod_high = (df["suitability_score"] >= 7.0).sum()
            pct = mod_high / len(df) * 100 if len(df) > 0 else 0.0
        else:
            mod_high = 0
            pct = 0.0
        st.markdown(f'''
        <div class="metric-card">
            <h4>Moderately to Highly Suitable<br>
                <small style="color:#173a30; font-weight:500;">(≥ 7.0 / 10)</small>
            </h4>
            <p>{mod_high:,} <span style="font-size:1.1rem; color:#64955d;">({pct:.1f}%)</span></p>
        </div>
        ''', unsafe_allow_html=True)

    # ============================================================
    # SAFE TABLE + RECOMMENDATIONS (NO MORE KeyError!)
    # ============================================================
    st.subheader("Suitability Scores")
    if "suitability_score" in df.columns:
        st.dataframe(df.sort_values("suitability_score", ascending=False), width='stretch', hide_index=True)
    else:
        st.dataframe(df, width='stretch', hide_index=True)
        st.warning("'suitability_score' column not found. Displaying all available data.")

    # Auto-detect recommendation columns
    feed_col = None
    reason_col = None
    for col in df.columns:
        if "feedstock" in col.lower():
            feed_col = col
        if "reason" in col.lower():
            reason_col = col

    st.subheader("Top 10 Recommended Locations")
    if feed_col and reason_col and "h3_index" in df.columns:
        display_cols = ["h3_index"]
        if "suitability_score" in df.columns:
            display_cols.append("suitability_score")
        if "mean_soc" in df.columns:
            display_cols.append("mean_soc")
        if "mean_ph" in df.columns:
            display_cols.append("mean_ph")
        if "mean_moisture" in df.columns:
            display_cols.append("mean_moisture")
        display_cols.extend([feed_col, reason_col])
        
        # Filter to only columns that exist
        display_cols = [col for col in display_cols if col in df.columns]
        
        if display_cols:
            top_df = df[display_cols]
            # Sort by suitability_score if available, otherwise by first column
            sort_col = "suitability_score" if "suitability_score" in display_cols else display_cols[0]
            top_df = top_df.sort_values(sort_col, ascending=False).head(10)
            
            # Format numeric columns
            format_dict = {}
            if "suitability_score" in display_cols:
                format_dict["suitability_score"] = "{:.2f}"
            if "mean_soc" in display_cols:
                format_dict["mean_soc"] = "{:.1f}"
            if "mean_ph" in display_cols:
                format_dict["mean_ph"] = "{:.2f}"
            if "mean_moisture" in display_cols:
                format_dict["mean_moisture"] = "{:.1%}"
            
            if format_dict:
                st.dataframe(top_df.round(3).style.format(format_dict))
            else:
                st.dataframe(top_df)
        else:
            st.warning("No displayable columns found.")
    else:
        st.info("No feedstock recommendations yet — run the analysis with the recommender enabled!")

    # Download
    st.download_button(
        label="Download Results as CSV",
        data=df.to_csv(index=False).encode(),
        file_name="biochar_suitability_scores.csv",
        mime="text/csv",
        use_container_width=True
    )

    # ============================================================
    # MAP TABS (unchanged)
    # ============================================================
    tab1, tab2, tab3, tab4, investor_tab = st.tabs(
        ["Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture", "Investor Waste Map"]
    )
    # ... (your map tabs stay exactly the same)

    with tab1:
        st.subheader("Interactive Suitability Map")
        map_path = map_paths.get("suitability", PROJECT_ROOT / config["output"]["html"] / "suitability_map.html")
        if map_path.exists():
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    map_html = f.read()
                st.components.v1.html(map_html, height=750, scrolling=False)
            except Exception as e:
                st.error(f"Failed to load map: {e}")
                st.info(f"Map file: {map_path}")
        else:
            st.warning("Interactive map not generated.")
            st.info(f"Expected file: {map_path}")

    with tab2:
        st.subheader("Soil Organic Carbon Map")
        st.markdown("<p style='color: #333; margin-bottom: 1rem;'>SOC = average of surface and 10cm depth (g/kg).</p>", unsafe_allow_html=True)
        soc_map_path = map_paths.get("soc", PROJECT_ROOT / config["output"]["html"] / "soc_map_streamlit.html")
        if soc_map_path.exists():
            try:
                with open(soc_map_path, "r", encoding="utf-8") as f:
                    map_html = f.read()
                st.components.v1.html(map_html, height=750, scrolling=False)
            except Exception as e:
                st.error(f"Failed to load SOC map: {e}")
        else:
            st.warning("SOC map not generated.")
            st.info(f"Expected file: {soc_map_path}")

    with tab3:
        st.subheader("Soil pH Map")
        st.markdown("<p style='color: #333; margin-bottom: 1rem;'>pH = average of surface and 10cm depth.</p>", unsafe_allow_html=True)
        ph_map_path = map_paths.get("ph", PROJECT_ROOT / config["output"]["html"] / "ph_map_streamlit.html")
        if ph_map_path.exists():
            try:
                with open(ph_map_path, "r", encoding="utf-8") as f:
                    map_html = f.read()
                st.components.v1.html(map_html, height=750, scrolling=False)
            except Exception as e:
                st.error(f"Failed to load pH map: {e}")
        else:
            st.warning("pH map not generated.")
            st.info(f"Expected file: {ph_map_path}")

    with tab4:
        st.subheader("Soil Moisture Map")
        st.markdown("<p style='color: #333; margin-bottom: 1rem;'>Moisture shown as percentage (0–100%).</p>", unsafe_allow_html=True)
        moisture_map_path = map_paths.get("moisture", PROJECT_ROOT / config["output"]["html"] / "moisture_map_streamlit.html")
        if moisture_map_path.exists():
            try:
                with open(moisture_map_path, "r", encoding="utf-8") as f:
                    map_html = f.read()
                st.components.v1.html(map_html, height=750, scrolling=False)
            except Exception as e:
                st.error(f"Failed to load moisture map: {e}")
        else:
            st.warning("Soil moisture map not generated.")
            st.info(f"Expected file: {moisture_map_path}")

    with investor_tab:
        st.subheader("Investor Crop Area Map")
        
        boundaries_dir = PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024"
        waste_csv_path = PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"
        
        if not boundaries_dir.exists():
            st.warning("Municipality boundaries not found. Please add files to data/boundaries/BR_Municipios_2024/.")
        elif not waste_csv_path.exists():
            st.warning("Municipality crop CSV missing. Expected data/crop_data/Updated_municipality_crop_production_data.csv")
        else:
            # Data type selector using radio buttons
            data_type = st.radio(
                "Select data type to display:",
                options=["area", "production", "residue"],
                format_func=lambda x: {
                    "area": "Crop Area (ha)",
                    "production": "Crop Production (ton)",
                    "residue": "Crop Residue (ton)"
                }[x],
                horizontal=True,
                key="investor_map_data_type"
            )
            
            try:
                # Import functions at module level to avoid caching issues
                from src.map_generators.pydeck_maps.municipality_waste_map import (
                    prepare_investor_crop_area_geodata,
                    create_municipality_waste_deck,
                )
                
                # Cache the merged geodata to avoid reloading on every render (optimize performance)
                @st.cache_data
                def get_merged_geodata(_boundaries_dir, _waste_csv_path):
                    return prepare_investor_crop_area_geodata(
                        _boundaries_dir, _waste_csv_path, simplify_tolerance=0.01
                    )
                
                # Get cached geodata (only loads once, cached for subsequent renders)
                merged_gdf = get_merged_geodata(boundaries_dir, waste_csv_path)
                
                # Create deck with selected data type (lightweight, only processes selected data)
                deck = create_municipality_waste_deck(merged_gdf, data_type=data_type)
                
                # Display map
                st.pydeck_chart(deck, use_container_width=True)
                
                # Display metrics for all three data types
                # Production and residue are already integers, round for display
                total_area = merged_gdf["total_crop_area_ha"].sum()
                total_production_sum = int(round(merged_gdf["total_crop_production_ton"].sum()))
                total_residue_sum = int(round(merged_gdf["total_crop_residue_ton"].sum()))
                
                # Format totals - show as number (not N/A) since it's a sum across all municipalities
                total_production_str = f"{total_production_sum:,.0f}"
                total_residue_str = f"{total_residue_sum:,.0f}"
                
                # Show top municipalities based on selected data type
                if data_type == "area":
                    top_col = "total_crop_area_ha"
                    col_label = "Crop area (ha)"
                elif data_type == "production":
                    top_col = "total_crop_production_ton"
                    col_label = "Crop production (ton)"
                else:
                    top_col = "total_crop_residue_ton"
                    col_label = "Crop residue (ton)"
                
                # Sort by numeric value, then format for display
                top_municipalities = (
                    merged_gdf.sort_values(top_col, ascending=False)
                    .head(5)[["NM_MUN", "SIGLA_UF", top_col, "total_crop_area_ha"]]
                    .copy()
                )
                
                # Round production and residue to integers, show N/A when appropriate
                if data_type in ["production", "residue"]:
                    # Format: show N/A if area > 0 but production/residue = 0
                    top_municipalities[col_label] = top_municipalities.apply(
                        lambda row: "N/A" if row["total_crop_area_ha"] > 0 and row[top_col] == 0 else int(round(row[top_col])),
                        axis=1
                    )
                    # Drop the helper column and rename
                    top_municipalities = top_municipalities.drop(columns=[top_col, "total_crop_area_ha"])
                    top_municipalities = top_municipalities.rename(columns={
                        "NM_MUN": "Municipality",
                        "SIGLA_UF": "State",
                    })
                else:
                    top_municipalities = top_municipalities.drop(columns=["total_crop_area_ha"])
                    top_municipalities = top_municipalities.rename(columns={
                        "NM_MUN": "Municipality",
                        "SIGLA_UF": "State",
                        top_col: col_label,
                    })
                
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    st.metric("Total crop area (ha)", f"{total_area:,.0f}")
                with c2:
                    st.metric("Total production (ton)", total_production_str)
                with c3:
                    st.metric("Total residue (ton)", total_residue_str)
                
                st.write(f"Top municipalities by {col_label}:")
                # Format based on data type - handle N/A for production/residue
                if data_type in ["production", "residue"]:
                    # Don't format if values contain "N/A" strings
                    # The dataframe already has N/A as strings where appropriate
                    st.dataframe(
                        top_municipalities,
                        use_container_width=True,
                    )
                else:
                    format_dict = {col_label: "{:,.0f}"}
                    st.dataframe(
                        top_municipalities.style.format(format_dict),
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Unable to render investor waste map: {e}")
                st.code(traceback.format_exc())

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Data-driven biochar suitability mapping for ecological impact.
</div>
""", unsafe_allow_html=True)
