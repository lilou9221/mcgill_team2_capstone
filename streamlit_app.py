# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import os
import json
import io
import time
import yaml

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

@st.cache_data
def load_config():
    with open(PROJECT_ROOT / "configs" / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# FINAL CSS – UNCHANGED (perfect as-is)
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
    use_coords = st.checkbox("Analyze area around a point", value=False)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# ============================================================
# MAIN ANALYSIS PIPELINE
# ============================================================
if run_btn:
    with st.spinner("Preparing data…"):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)

        if len(list(raw_dir.glob("*.tif"))) >= 5:
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning("Downloading GeoTIFFs from Google Drive…")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload
                creds = json.loads(st.secrets["google_drive"]["credentials"])
                credentials = service_account.Credentials.from_service_account_info(
                    creds, scopes=["https://www.googleapis.com/auth/drive.readonly"]
                )
                service = build("drive", "v3", credentials=credentials)
                folder_id = config["drive"]["raw_data_folder_id"]
                results = service.files().list(q=f"'{folder_id}' in parents and trashed=false", fields="files(id, name)").execute()
                for f in results["files"]:
                    if not f["name"].endswith(".tif"): continue
                    dst = raw_dir / f["name"]
                    if dst.exists(): continue
                    request = service.files().get_media(fileId=f["id"])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done: _, done = downloader.next_chunk()
                    dst.write_bytes(fh.getvalue())
                shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
            except Exception as e:
                st.error(f"Download failed: {e}")
                st.stop()

    # Run analysis
    wrapper_script = PROJECT_ROOT / "scripts" / "run_analysis.py"
    cli = [sys.executable, str(wrapper_script), "--config", str(PROJECT_ROOT / "configs" / "config.yaml"), "--h3-resolution", str(h3_res)]
    if use_coords and lat and lon and radius:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    log_box = st.empty()
    logs = []
    process = subprocess.Popen(cli, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
    start = time.time()
    for line in process.stdout:
        logs.append(line)
        status.info(f"Running… {int(time.time()-start)}s elapsed")
        log_box.code("".join(logs[-12:]), language="bash")
    if process.wait() != 0:
        st.error("Pipeline failed.")
        st.code("".join(logs), language="bash")
        st.stop()

    # Load results
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results missing.")
        st.stop()
    df = pd.read_csv(csv_path)
    st.success("Analysis completed successfully!")

    # ============================================================
    # METRICS – ONLY THE CHANGES YOU ASKED FOR
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
        st.markdown(f'''
        <div class="metric-card">
            <h4>Mean Suitability Score<br>
                <small style="color:#173a30; font-weight:500;">(scale: 0–10)</small>
            </h4>
            <p>{df["suitability_score"].mean():.2f}</p>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        mod_high = (df["suitability_score"] >= 7.0).sum()
        pct = mod_high / len(df) * 100
        st.markdown(f'''
        <div class="metric-card">
            <h4>Moderately to Highly Suitable<br>
                <small style="color:#173a30; font-weight:500;">(≥ 7.0 / 10)</small>
            </h4>
            <p>{mod_high:,} <span style="font-size:1.1rem; color:#64955d;">({pct:.1f}%)</span></p>
        </div>
        ''', unsafe_allow_html=True)

    # ============================================================
    # INTERACTIVE MAPS WITH BIOCHAR RECOMMENDATIONS
    # ============================================================
    st.subheader("Interactive Maps")
    
    try:
        import geopandas as gpd
        import numpy as np
        from branca.colormap import LinearColormap
        import folium
        from folium import plugins
        import h3
        from shapely.geometry import Polygon
        import gc  # For garbage collection
        
        # Load GeoJSON file (preferred - more efficient)
        geojson_path = PROJECT_ROOT / config["data"]["processed"] / "hexagons_with_scores.geojson"
        
        if geojson_path.exists():
            # Load GeoJSON directly (most efficient) with memory checks
            with st.spinner("Loading hexagon data from GeoJSON..."):
                try:
                    # Check file size first
                    file_size_mb = geojson_path.stat().st_size / (1024 * 1024)
                    st.info(f"GeoJSON file size: {file_size_mb:.2f} MB")
                    
                    # Load with memory-efficient settings
                    gdf = gpd.read_file(geojson_path)
                    
                    # Validate GeoJSON structure
                    if 'geometry' not in gdf.columns:
                        raise ValueError("GeoJSON missing 'geometry' column")
                    
                    # Check for valid geometries
                    invalid_geom = gdf['geometry'].isna().sum()
                    if invalid_geom > 0:
                        st.warning(f"Found {invalid_geom} rows with invalid geometry. Filtering them out.")
                        gdf = gdf[gdf['geometry'].notna()].copy()
                    
                    # Validate CRS
                    if gdf.crs is None:
                        gdf.set_crs('EPSG:4326', inplace=True)
                    
                    st.success(f"Loaded {len(gdf):,} hexagons from GeoJSON.")
                    st.info(f"Available columns: {', '.join([c for c in gdf.columns if c != 'geometry'])}")
                    
                    # Force garbage collection after loading
                    gc.collect()
                    
                except Exception as e:
                    st.error(f"Error loading GeoJSON: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    st.stop()
        else:
            # Fallback: reconstruct from CSV
            with st.spinner("Reconstructing hexagon geometry from CSV..."):
                if 'h3_index' not in df.columns:
                    st.error("Data missing 'h3_index' column. Cannot create maps.")
                    st.stop()
                
                # Reconstruct geometry from h3_index
                def h3_to_polygon(h3_index):
                    """Convert H3 index to Shapely Polygon."""
                    try:
                        if pd.isna(h3_index):
                            return None
                        boundary = h3.cell_to_boundary(str(h3_index))
                        # h3 returns (lat, lon), but Shapely needs (lon, lat)
                        coords = [(lon, lat) for lat, lon in boundary]
                        # Close the polygon
                        coords.append(coords[0])
                        return Polygon(coords)
                    except:
                        return None
                
                df_with_geom = df.copy()
                df_with_geom['geometry'] = df_with_geom['h3_index'].apply(h3_to_polygon)
                
                # Filter out rows with None geometry
                df_with_geom = df_with_geom[df_with_geom['geometry'].notna()].copy()
                
                if len(df_with_geom) == 0:
                    st.error("Could not reconstruct geometry from h3_index. Please check your data.")
                    st.stop()
                
                # Convert to GeoDataFrame
                gdf = gpd.GeoDataFrame(df_with_geom, geometry='geometry', crs='EPSG:4326')
                st.success(f"Reconstructed geometry for {len(gdf):,} hexagons from CSV.")
        
        # Helper function to find column (case-insensitive, partial match)
        def find_column(dataframe, target_name, possible_names):
            """Find column name in DataFrame, trying exact match first, then case-insensitive, then partial match."""
            # First try exact matches
            for name in possible_names:
                if name in dataframe.columns:
                    return name
            
            # Then try case-insensitive
            df_cols_lower = {col.lower(): col for col in dataframe.columns}
            for name in possible_names:
                if name.lower() in df_cols_lower:
                    return df_cols_lower[name.lower()]
            
            # Then try partial match (for columns like "SOC_res_250_b0 (g/kg)")
            for col in dataframe.columns:
                col_lower = col.lower()
                for name in possible_names:
                    if name.lower() in col_lower and 'score' not in col_lower and col_lower not in ['lon', 'lat', 'h3_index', 'geometry']:
                        return col
            
            return None
        
        # Ensure geometry column exists
        if 'geometry' not in gdf.columns:
            st.error("Missing 'geometry' column. Cannot create maps.")
            st.stop()
        
        # Calculate map center and zoom from geometry (with memory check)
        try:
            # Use a sample for large datasets to avoid memory issues
            if len(gdf) > 10000:
                sample_gdf = gdf.sample(min(1000, len(gdf)))
                bounds = sample_gdf.total_bounds
                del sample_gdf  # Free memory
            else:
                bounds = gdf.total_bounds
            center_lat = float((bounds[1] + bounds[3]) / 2)
            center_lon = float((bounds[0] + bounds[2]) / 2)
        except Exception as e:
            st.warning(f"Could not calculate map center from geometry: {e}. Using default coordinates.")
            center_lat = -13.0
            center_lon = -56.0
        
        # Load biochar database and generate recommendations
        biochar_db_path = PROJECT_ROOT / "data" / "pyrolysis" / "Dataset_feedstock_ML.xlsx"
        if biochar_db_path.exists():
            try:
                biochar_df = pd.read_excel(biochar_db_path, sheet_name="Biochar Properties ")
                
                # Parse pore size column if it exists
                def parse_pore_size(pore_str):
                    """Parse pore size string like '0.05 m²/g; 0.34 cm³/g' into surface area and pore volume."""
                    if pd.isna(pore_str) or not isinstance(pore_str, str):
                        return None, None
                    try:
                        parts = pore_str.split(';')
                        surface_area = None
                        pore_volume = None
                        for part in parts:
                            part = part.strip()
                            if 'm²/g' in part or 'm2/g' in part:
                                surface_area = float(''.join(c for c in part if c.isdigit() or c == '.'))
                            elif 'cm³/g' in part or 'cm3/g' in part:
                                pore_volume = float(''.join(c for c in part if c.isdigit() or c == '.'))
                        return surface_area, pore_volume
                    except:
                        return None, None
                
                # Biochar recommendation engine
                def recommend_biochar(row):
                    """Recommend best biochar feedstock based on soil conditions."""
                    soc = row.get('soc', 0)
                    ph = row.get('ph', 7.0)
                    moisture = row.get('soil_moisture', 50.0)
                    
                    # Priority rule: If SOC > 5.0%, no biochar recommended
                    if soc > 5.0:
                        return "No biochar application recommended", "High SOC (>5.0%) - soil already has sufficient organic carbon"
                    
                    # Score all biochar entries
                    best_score = -1
                    best_feedstock = "No suitable biochar found"
                    best_reason = "No match found"
                    
                    for _, biochar in biochar_df.iterrows():
                        score = 0
                        reasons = []
                        
                        # Extract biochar properties (handle missing values)
                        fixed_carbon = pd.to_numeric(biochar.get('Fixed Carbon (%)', biochar.get('Fixed Carbon', 0)), errors='coerce') or 0
                        volatile_matter = pd.to_numeric(biochar.get('Volatile Matter (%)', biochar.get('Volatile Matter', 0)), errors='coerce') or 0
                        ash = pd.to_numeric(biochar.get('Ash (%)', biochar.get('Ash', 0)), errors='coerce') or 0
                        biochar_ph = pd.to_numeric(biochar.get('pH', 0), errors='coerce') or 7.0
                        surface_area, pore_volume = parse_pore_size(biochar.get('Pore Size', biochar.get('pore size', '')))
                        porosity = pd.to_numeric(biochar.get('Porosity (%)', biochar.get('Porosity', 0)), errors='coerce') or 0
                        
                        feedstock_name = str(biochar.get('Feedstock', biochar.get('Feedstock Name', 'Unknown')))
                        temp = biochar.get('Temperature (°C)', biochar.get('Temperature', ''))
                        if temp:
                            feedstock_name += f" ({temp}°C)"
                        
                        # High moisture (≥80%) conditions
                        if moisture >= 80:
                            if fixed_carbon < 50:
                                score += 2
                                reasons.append("low fixed carbon")
                            if volatile_matter > 30:
                                score += 2
                                reasons.append("high volatile matter")
                            if ash > 40:
                                score += 2
                                reasons.append("high ash")
                            if biochar_ph > 10:
                                score += 2
                                reasons.append("high pH")
                            if porosity < 50:
                                score += 1
                                reasons.append("low porosity")
                        
                        # Low moisture (<80%) conditions
                        else:
                            if 60 <= fixed_carbon <= 85:
                                score += 3
                                reasons.append("optimal fixed carbon")
                            if volatile_matter > 20:
                                score += 1
                                reasons.append("adequate volatile matter")
                            if ash < 20:
                                score += 2
                                reasons.append("low ash")
                            if 7.0 <= biochar_ph <= 9.5:
                                score += 2
                                reasons.append("optimal pH range")
                            if porosity > 50:
                                score += 2
                                reasons.append("high porosity")
                        
                        # Acidic soil (pH < 6.0)
                        if ph < 6.0:
                            if ash > 25:
                                score += 3
                                reasons.append("high ash for acidic soil")
                            if biochar_ph > 10:
                                score += 3
                                reasons.append("very high pH for acidic soil")
                            if surface_area and surface_area > 100:
                                score += 2
                                reasons.append("high surface area")
                        
                        # Alkaline soil (pH > 7.0)
                        elif ph > 7.0:
                            if ash < 10:
                                score += 3
                                reasons.append("very low ash for alkaline soil")
                            if biochar_ph < 6.0:
                                score += 2
                                reasons.append("low pH for alkaline soil")
                            if surface_area and surface_area > 100:
                                score += 2
                                reasons.append("high surface area")
                        
                        if score > best_score:
                            best_score = score
                            best_feedstock = feedstock_name
                            best_reason = " + ".join(reasons[:3]) if reasons else "General match"
                    
                    return best_feedstock, best_reason
                
                # Apply recommendations to all hexagons
                with st.spinner("Generating biochar recommendations..."):
                    recommendations = gdf.apply(recommend_biochar, axis=1)
                    gdf['Recommended Feedstock'] = [r[0] for r in recommendations]
                    gdf['Recommendation Reason'] = [r[1] for r in recommendations]
                
                # Summary of top 5 feedstocks
                feedstock_counts = gdf['Recommended Feedstock'].value_counts().head(5)
                total_hexagons = len(gdf)
                
                st.info(f"""
                **Top 5 Recommended Feedstocks in this Area:**
                {chr(10).join([f"• {feedstock}: {count:,} hexagons ({count/total_hexagons*100:.1f}%)" 
                              for feedstock, count in feedstock_counts.items()])}
                """)
                
            except Exception as e:
                st.warning(f"Could not load biochar database: {e}. Recommendations will be skipped.")
                gdf['Recommended Feedstock'] = "Not available"
                gdf['Recommendation Reason'] = "Database not loaded"
        else:
            st.warning("Biochar database not found. Recommendations will be skipped.")
            gdf['Recommended Feedstock'] = "Not available"
            gdf['Recommendation Reason'] = "Database not found"
        
        # Create map tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Suitability", "Soil pH", "Soil Moisture", "Soil Organic Carbon (SOC)"])
        
        with tab1:
            # Original suitability map
            map_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
            if map_path.exists():
                st.markdown("**Biochar Suitability Score (0-10 scale)**")
                st.caption("Higher scores (green) indicate areas where biochar application would be most beneficial for improving soil quality.")
                with open(map_path, "r", encoding="utf-8") as f:
                    st.components.v1.html(f.read(), height=750, scrolling=False)
            else:
                st.warning("Suitability map not generated.")
        
        with tab2:
            st.markdown("**Soil pH**")
            st.caption("Diverging color scheme: Red indicates acidic soils (<5.5), yellow indicates neutral (6.5-7.5), blue indicates alkaline soils (>7.5).")
            
            try:
                # Work with a copy to avoid modifying the original
                gdf_ph = gdf.copy()
                
                # Find and map ph column
                ph_col_name = find_column(gdf_ph, 'ph', ['ph', 'soil_ph', 'soil_pH', 'pH', 'soil_pH_res_250_b0', 'soil_pH_res_250_b10'])
                if ph_col_name and ph_col_name != 'ph':
                    gdf_ph['ph'] = gdf_ph[ph_col_name]
                elif not ph_col_name or 'ph' not in gdf_ph.columns:
                    gdf_ph['ph'] = np.nan
                
                # Check if ph column exists and has valid data
                if 'ph' not in gdf_ph.columns or gdf_ph['ph'].isna().all():
                    st.warning("No pH data available in the dataset.")
                else:
                    ph_data = gdf_ph['ph'].dropna()
                    if len(ph_data) == 0:
                        st.warning("No valid pH data available.")
                    else:
                        col_map, col_stats = st.columns([3, 1])
                        
                        with col_map:
                            # Create pH map with diverging colormap (RdYlBu_r)
                            m_ph = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles='CartoDB positron')
                            
                            # Create diverging colormap: Red (acidic) -> Yellow (neutral) -> Blue (alkaline)
                            ph_min, ph_max = float(ph_data.min()), float(ph_data.max())
                            
                            # Handle edge case where min == max
                            if ph_min == ph_max:
                                ph_max = ph_min + 0.1
                            
                            ph_colormap = LinearColormap(
                                colors=['#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4'],
                                vmin=ph_min,
                                vmax=ph_max,
                                caption='Soil pH'
                            )
                            
                            # Add hexagons to map using GeoJson with style function
                            def style_function_ph(feature):
                                """Style function for pH map."""
                                try:
                                    ph_val = feature['properties'].get('ph')
                                    if ph_val is None or pd.isna(ph_val):
                                        return {
                                            'fillColor': '#808080',
                                            'color': 'black',
                                            'weight': 0.5,
                                            'fillOpacity': 0.3
                                        }
                                    ph_val = float(ph_val)
                                    color = ph_colormap(ph_val)
                                    return {
                                        'fillColor': color,
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.7
                                    }
                                except:
                                    return {
                                        'fillColor': '#808080',
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.3
                                    }
                            
                            # Create GeoJSON layer - only include rows with valid geometry and ph data
                            gdf_ph_map = gdf_ph[['ph', 'h3_index', 'geometry']].copy()
                            gdf_ph_map = gdf_ph_map[gdf_ph_map['geometry'].notna()].copy()
                            gdf_ph_map = gdf_ph_map[gdf_ph_map['ph'].notna()].copy()
                            
                            # Limit dataset size for very large files (sample if needed)
                            max_features = 50000  # Reasonable limit for Folium
                            if len(gdf_ph_map) > max_features:
                                st.warning(f"Dataset has {len(gdf_ph_map):,} features. Sampling {max_features:,} for map display.")
                                gdf_ph_map = gdf_ph_map.sample(n=max_features).copy()
                            
                            if len(gdf_ph_map) > 0:
                                try:
                                    # Convert to JSON with proper encoding
                                    geojson_str = gdf_ph_map.to_json()
                                    folium.GeoJson(
                                        geojson_str,
                                        style_function=style_function_ph,
                                        tooltip=folium.GeoJsonTooltip(
                                            fields=['h3_index', 'ph'],
                                            aliases=['H3:', 'pH:'],
                                            localize=True
                                        )
                                    ).add_to(m_ph)
                                    del geojson_str  # Free memory
                                    gc.collect()  # Force garbage collection
                                except Exception as e:
                                    st.warning(f"Could not add GeoJSON layer: {e}")
                            
                            try:
                                ph_colormap.add_to(m_ph)
                                plugins.Fullscreen().add_to(m_ph)
                            except Exception as e:
                                st.warning(f"Could not add colormap/plugins: {e}")
                            
                            # Convert to HTML and display
                            try:
                                from streamlit_folium import st_folium
                                st_folium(m_ph, width=700, height=750)
                            except ImportError:
                                # Fallback if streamlit_folium not available
                                try:
                                    html_str = m_ph._repr_html_()
                                    st.components.v1.html(html_str, height=750, scrolling=False)
                                    del html_str  # Free memory
                                    gc.collect()
                                except Exception as e:
                                    st.error(f"Could not render map: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        
                        with col_stats:
                            st.markdown("**Statistics**")
                            try:
                                ph_stats = gdf_ph['ph'].describe()
                                st.metric("Mean", f"{ph_stats['mean']:.2f}")
                                st.metric("Min", f"{ph_stats['min']:.2f}")
                                st.metric("Max", f"{ph_stats['max']:.2f}")
                                st.metric("Std Dev", f"{ph_stats['std']:.2f}")
                                
                                # Histogram
                                import matplotlib.pyplot as plt
                                fig, ax = plt.subplots(figsize=(3, 2))
                                ax.hist(ph_data, bins=20, color='#4575b4', edgecolor='black', alpha=0.7)
                                ax.set_xlabel('pH')
                                ax.set_ylabel('Frequency')
                                ax.set_title('pH Distribution')
                                plt.tight_layout()
                                st.pyplot(fig)
                                plt.close()
                            except Exception as e:
                                st.warning(f"Could not generate statistics: {e}")
            except Exception as e:
                st.error(f"Error creating pH map: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        with tab3:
            st.markdown("**Soil Moisture (%)**")
            st.caption("Sequential color scheme: Beige/yellow indicates dry soils, dark blue indicates wet soils. Higher moisture generally requires different biochar properties.")
            
            try:
                # Work with a copy to avoid modifying the original
                gdf_moisture = gdf.copy()
                
                # Find and map soil_moisture column
                moisture_col_name = find_column(gdf_moisture, 'soil_moisture', ['soil_moisture', 'moisture', 'soil_moisture_percent', 'sm_surface'])
                if moisture_col_name and moisture_col_name != 'soil_moisture':
                    gdf_moisture['soil_moisture'] = gdf_moisture[moisture_col_name]
                elif not moisture_col_name or 'soil_moisture' not in gdf_moisture.columns:
                    gdf_moisture['soil_moisture'] = np.nan
                
                # Check if soil_moisture column exists and has valid data
                if 'soil_moisture' not in gdf_moisture.columns or gdf_moisture['soil_moisture'].isna().all():
                    st.warning("No soil moisture data available in the dataset.")
                else:
                    moisture_data = gdf_moisture['soil_moisture'].dropna()
                    if len(moisture_data) == 0:
                        st.warning("No valid soil moisture data available.")
                    else:
                        col_map, col_stats = st.columns([3, 1])
                        
                        with col_map:
                            m_moisture = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles='CartoDB positron')
                            
                            # Create sequential colormap (YlGnBu: yellow -> green -> blue)
                            moisture_min, moisture_max = float(moisture_data.min()), float(moisture_data.max())
                            
                            # Handle edge case where min == max
                            if moisture_min == moisture_max:
                                moisture_max = moisture_min + 0.1
                            
                            moisture_colormap = LinearColormap(
                                colors=['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#2c7fb8', '#253494'],
                                vmin=moisture_min,
                                vmax=moisture_max,
                                caption='Soil Moisture (%)'
                            )
                            
                            # Add hexagons to map using GeoJson with style function
                            def style_function_moisture(feature):
                                """Style function for moisture map."""
                                try:
                                    moisture_val = feature['properties'].get('soil_moisture')
                                    if moisture_val is None or pd.isna(moisture_val):
                                        return {
                                            'fillColor': '#808080',
                                            'color': 'black',
                                            'weight': 0.5,
                                            'fillOpacity': 0.3
                                        }
                                    moisture_val = float(moisture_val)
                                    color = moisture_colormap(moisture_val)
                                    return {
                                        'fillColor': color,
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.7
                                    }
                                except:
                                    return {
                                        'fillColor': '#808080',
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.3
                                    }
                            
                            # Create GeoJSON layer - only include rows with valid geometry and moisture data
                            gdf_moisture_map = gdf_moisture[['soil_moisture', 'h3_index', 'geometry']].copy()
                            gdf_moisture_map = gdf_moisture_map[gdf_moisture_map['geometry'].notna()].copy()
                            gdf_moisture_map = gdf_moisture_map[gdf_moisture_map['soil_moisture'].notna()].copy()
                            
                            # Limit dataset size for very large files
                            max_features = 50000
                            if len(gdf_moisture_map) > max_features:
                                st.warning(f"Dataset has {len(gdf_moisture_map):,} features. Sampling {max_features:,} for map display.")
                                gdf_moisture_map = gdf_moisture_map.sample(n=max_features).copy()
                            
                            if len(gdf_moisture_map) > 0:
                                try:
                                    geojson_str = gdf_moisture_map.to_json()
                                    folium.GeoJson(
                                        geojson_str,
                                        style_function=style_function_moisture,
                                        tooltip=folium.GeoJsonTooltip(
                                            fields=['h3_index', 'soil_moisture'],
                                            aliases=['H3:', 'Moisture (%):'],
                                            localize=True
                                        )
                                    ).add_to(m_moisture)
                                    del geojson_str  # Free memory
                                    gc.collect()  # Force garbage collection
                                except Exception as e:
                                    st.warning(f"Could not add GeoJSON layer: {e}")
                            
                            try:
                                moisture_colormap.add_to(m_moisture)
                                plugins.Fullscreen().add_to(m_moisture)
                            except Exception as e:
                                st.warning(f"Could not add colormap/plugins: {e}")
                            
                            try:
                                from streamlit_folium import st_folium
                                st_folium(m_moisture, width=700, height=750)
                            except ImportError:
                                try:
                                    html_str = m_moisture._repr_html_()
                                    st.components.v1.html(html_str, height=750, scrolling=False)
                                    del html_str  # Free memory
                                    gc.collect()
                                except Exception as e:
                                    st.error(f"Could not render map: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        
                        with col_stats:
                            st.markdown("**Statistics**")
                            try:
                                moisture_stats = gdf_moisture['soil_moisture'].describe()
                                st.metric("Mean", f"{moisture_stats['mean']:.2f}%")
                                st.metric("Min", f"{moisture_stats['min']:.2f}%")
                                st.metric("Max", f"{moisture_stats['max']:.2f}%")
                                st.metric("Std Dev", f"{moisture_stats['std']:.2f}%")
                                
                                fig, ax = plt.subplots(figsize=(3, 2))
                                ax.hist(moisture_data, bins=20, color='#2c7fb8', edgecolor='black', alpha=0.7)
                                ax.set_xlabel('Moisture (%)')
                                ax.set_ylabel('Frequency')
                                ax.set_title('Moisture Distribution')
                                plt.tight_layout()
                                st.pyplot(fig)
                                plt.close()
                            except Exception as e:
                                st.warning(f"Could not generate statistics: {e}")
            except Exception as e:
                st.error(f"Error creating moisture map: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        with tab4:
            st.markdown("**Soil Organic Carbon (SOC) (%)**")
            st.caption("Sequential color scheme: Beige indicates low SOC, dark green/brown indicates high SOC. Areas with SOC >5% typically don't require biochar application.")
            
            try:
                # Work with a copy to avoid modifying the original
                gdf_soc = gdf.copy()
                
                # Find and map soc column
                soc_col_name = find_column(gdf_soc, 'soc', ['soc', 'soil_organic_carbon', 'soil_organic_carbon_percent', 'organic_carbon', 
                                                             'SOC_res_250_b0', 'SOC_res_250_b10', 'soil_organic'])
                if soc_col_name and soc_col_name != 'soc':
                    gdf_soc['soc'] = gdf_soc[soc_col_name]
                elif not soc_col_name or 'soc' not in gdf_soc.columns:
                    gdf_soc['soc'] = np.nan
                
                # Check if soc column exists and has valid data
                if 'soc' not in gdf_soc.columns or gdf_soc['soc'].isna().all():
                    st.warning("No SOC data available in the dataset.")
                else:
                    soc_data = gdf_soc['soc'].dropna()
                    if len(soc_data) == 0:
                        st.warning("No valid SOC data available.")
                    else:
                        col_map, col_stats = st.columns([3, 1])
                        
                        with col_map:
                            m_soc = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles='CartoDB positron')
                            
                            # Create sequential colormap (YlOrBr: yellow -> orange -> brown)
                            soc_min, soc_max = float(soc_data.min()), float(soc_data.max())
                            
                            # Handle edge case where min == max
                            if soc_min == soc_max:
                                soc_max = soc_min + 0.1
                            
                            soc_colormap = LinearColormap(
                                colors=['#ffffd4', '#fed98e', '#fe9929', '#d95f0e', '#993404'],
                                vmin=soc_min,
                                vmax=soc_max,
                                caption='SOC (%)'
                            )
                            
                            # Add hexagons to map using GeoJson with style function
                            def style_function_soc(feature):
                                """Style function for SOC map."""
                                try:
                                    soc_val = feature['properties'].get('soc')
                                    if soc_val is None or pd.isna(soc_val):
                                        return {
                                            'fillColor': '#808080',
                                            'color': 'black',
                                            'weight': 0.5,
                                            'fillOpacity': 0.3
                                        }
                                    soc_val = float(soc_val)
                                    color = soc_colormap(soc_val)
                                    return {
                                        'fillColor': color,
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.7
                                    }
                                except:
                                    return {
                                        'fillColor': '#808080',
                                        'color': 'black',
                                        'weight': 0.5,
                                        'fillOpacity': 0.3
                                    }
                            
                            # Create GeoJSON layer - only include rows with valid geometry and soc data
                            gdf_soc_map = gdf_soc[['soc', 'h3_index', 'geometry']].copy()
                            gdf_soc_map = gdf_soc_map[gdf_soc_map['geometry'].notna()].copy()
                            gdf_soc_map = gdf_soc_map[gdf_soc_map['soc'].notna()].copy()
                            
                            # Limit dataset size for very large files
                            max_features = 50000
                            if len(gdf_soc_map) > max_features:
                                st.warning(f"Dataset has {len(gdf_soc_map):,} features. Sampling {max_features:,} for map display.")
                                gdf_soc_map = gdf_soc_map.sample(n=max_features).copy()
                            
                            if len(gdf_soc_map) > 0:
                                try:
                                    geojson_str = gdf_soc_map.to_json()
                                    folium.GeoJson(
                                        geojson_str,
                                        style_function=style_function_soc,
                                        tooltip=folium.GeoJsonTooltip(
                                            fields=['h3_index', 'soc'],
                                            aliases=['H3:', 'SOC (%):'],
                                            localize=True
                                        )
                                    ).add_to(m_soc)
                                    del geojson_str  # Free memory
                                    gc.collect()  # Force garbage collection
                                except Exception as e:
                                    st.warning(f"Could not add GeoJSON layer: {e}")
                            
                            try:
                                soc_colormap.add_to(m_soc)
                                plugins.Fullscreen().add_to(m_soc)
                            except Exception as e:
                                st.warning(f"Could not add colormap/plugins: {e}")
                            
                            try:
                                from streamlit_folium import st_folium
                                st_folium(m_soc, width=700, height=750)
                            except ImportError:
                                try:
                                    html_str = m_soc._repr_html_()
                                    st.components.v1.html(html_str, height=750, scrolling=False)
                                    del html_str  # Free memory
                                    gc.collect()
                                except Exception as e:
                                    st.error(f"Could not render map: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                        
                        with col_stats:
                            st.markdown("**Statistics**")
                            try:
                                soc_stats = gdf_soc['soc'].describe()
                                st.metric("Mean", f"{soc_stats['mean']:.2f}%")
                                st.metric("Min", f"{soc_stats['min']:.2f}%")
                                st.metric("Max", f"{soc_stats['max']:.2f}%")
                                st.metric("Std Dev", f"{soc_stats['std']:.2f}%")
                                
                                fig, ax = plt.subplots(figsize=(3, 2))
                                ax.hist(soc_data, bins=20, color='#d95f0e', edgecolor='black', alpha=0.7)
                                ax.set_xlabel('SOC (%)')
                                ax.set_ylabel('Frequency')
                                ax.set_title('SOC Distribution')
                                plt.tight_layout()
                                st.pyplot(fig)
                                plt.close()
                            except Exception as e:
                                st.warning(f"Could not generate statistics: {e}")
            except Exception as e:
                st.error(f"Error creating SOC map: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # Display results table with recommendations
        # Convert GeoDataFrame to DataFrame for display (drop geometry)
        df_display = gdf.drop(columns=['geometry']).copy()
        
        # Build display columns list
        display_cols = []
        priority_cols = ['h3_index', 'suitability_score', 'ph', 'soil_moisture', 'soc']
        for col in priority_cols:
            if col in df_display.columns:
                display_cols.append(col)
        
        # Add recommendation columns if they exist
        if 'Recommended Feedstock' in df_display.columns:
            display_cols.extend(['Recommended Feedstock', 'Recommendation Reason'])
        
        # Add any other columns (excluding geometry which was already dropped)
        other_cols = [col for col in df_display.columns if col not in display_cols]
        display_cols.extend(other_cols)
        
        # Display table
        st.subheader("Detailed Results with Recommendations")
        if 'suitability_score' in df_display.columns:
            st.dataframe(df_display[display_cols].sort_values("suitability_score", ascending=False), width='stretch', hide_index=True)
        else:
            st.dataframe(df_display[display_cols], width='stretch', hide_index=True)
        
        # Download button
        st.download_button(
            label="Download Results as CSV (with Recommendations)",
            data=df_display[display_cols].to_csv(index=False).encode(),
            file_name="biochar_suitability_scores_with_recommendations.csv",
            mime="text/csv",
            use_container_width=True  # Note: width parameter not yet available for download_button
        )
        
    except ImportError as e:
        st.error(f"Missing required library: {e}. Please install geopandas, folium, branca, and matplotlib.")
    except Exception as e:
        st.error(f"Error loading maps: {e}")
        import traceback
        st.code(traceback.format_exc())

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Data-driven biochar deployment for ecological impact.
</div>
""", unsafe_allow_html=True)
