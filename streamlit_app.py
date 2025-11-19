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
    # TABLE + DOWNLOAD + MAP – ALL WORKING
    # ============================================================
    st.subheader("Suitability Scores")
    st.dataframe(df.sort_values("suitability_score", ascending=False), width='stretch', hide_index=True)

    st.download_button(
        label="Download Results as CSV",
        data=df.to_csv(index=False).encode(),
        file_name="biochar_suitability_scores.csv",
        mime="text/csv",
        use_container_width=True
    )

    # ============================================================
    # TABS: Biochar Suitability, Soil Organic Carbon, pH, and Soil Moisture
    # ============================================================
    tab1, tab2, tab3, tab4 = st.tabs(["Biochar Suitability", "Soil Organic Carbon", "Soil pH", "Soil Moisture"])
    
    with tab1:
        st.subheader("Interactive Suitability Map")
        map_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=750, scrolling=False)
        else:
            st.warning("Interactive map not generated.")
    
    with tab2:
        st.subheader("Soil Organic Carbon Map")
        st.markdown("""
        <p style="color: #333; margin-bottom: 1rem;">
            This map displays Soil Organic Carbon (SOC) values aggregated by H3 hexagons. 
            SOC is calculated as the average of the ground layer (b0) and at 10 cm below the surface (b10): <strong>mean_SOC = (mean(b0) + mean(b10)) / 2</strong>.
            Values are shown in g/kg (grams per kilogram).
        </p>
        """, unsafe_allow_html=True)
        
        # Load pre-generated SOC map (created during analysis pipeline, same as suitability map)
        soc_map_path = PROJECT_ROOT / config["output"]["html"] / "soc_map_streamlit.html"
        if soc_map_path.exists():
            with open(soc_map_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=750, scrolling=False)
        else:
            st.warning("SOC map not generated. Please run the analysis first.")
    
    with tab3:
        st.subheader("Soil pH Map")
        st.markdown("""
        <p style="color: #333; margin-bottom: 1rem;">
            This map displays Soil pH values aggregated by H3 hexagons. 
            pH is calculated as the average of the ground layer (b0) and at 10 cm below the surface (b10): <strong>mean_pH = (mean(b0) + mean(b10)) / 2</strong>.
            The color scheme uses a diverging scale: light orange-yellow for acidic soils (&lt;5.5), yellow for neutral (~7), and blue for alkaline soils (&gt;7.5).
        </p>
        """, unsafe_allow_html=True)
        
        # Load pre-generated pH map (created during analysis pipeline, same as suitability map)
        ph_map_path = PROJECT_ROOT / config["output"]["html"] / "ph_map_streamlit.html"
        if ph_map_path.exists():
            with open(ph_map_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=750, scrolling=False)
        else:
            st.warning("pH map not generated. Please run the analysis first.")
    
    with tab4:
        st.subheader("Soil Moisture Map")
        st.markdown("""
        <p style="color: #333; margin-bottom: 1rem;">
            This map displays Soil Moisture values aggregated by H3 hexagons. 
            Soil moisture is shown as a percentage (0-100%), converted from m³/m³ volume fraction. 
            The color scheme uses a sequential scale: light brown/yellow for relatively drier soils, green for moderate moisture, and blue for relatively wetter soils.
        </p>
        """, unsafe_allow_html=True)
        
        # Load pre-generated moisture map (created during analysis pipeline, same as suitability map)
        moisture_map_path = PROJECT_ROOT / config["output"]["html"] / "moisture_map_streamlit.html"
        if moisture_map_path.exists():
            with open(moisture_map_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=750, scrolling=False)
        else:
            st.warning("Soil moisture map not generated. Please run the analysis first.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Data-driven biochar deployment for ecological impact.
</div>
""", unsafe_allow_html=True)
