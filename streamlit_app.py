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

# ============================================================
# DEPENDENCY CHECK
# ============================================================
def ensure_dependency(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name, "--quiet"
            ])
            __import__(import_name)
            return True
        except Exception:
            return False

if not ensure_dependency("PyYAML", "yaml"):
    st.error("PyYAML missing. Add to requirements.txt:\nPyYAML>=6.0")
    st.stop()

import yaml

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

@st.cache_data
def load_config():
    cfg = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg, encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS — Final theme with dark sidebar + green buttons
# ============================================================
st.markdown("""
<style>

    body, .stApp {
        background-color: #ffffff !important;
        color: #333333 !important;
        font-family: 'Inter', sans-serif !important;
    }

    .header-title {
        font-size: 2.8rem;
        text-align: center;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #2d3a3a;
    }

    .header-subtitle {
        text-align: center;
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }

    /* ------------------------------------------------------- */
    /* SIDEBAR — Very Dark Green */
    /* ------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        background-color: #0C2F29 !important;
        color: white !important;
        padding-top: 2rem !important;
    }

    section[data-testid="stSidebar"] * {
        color: white !important;
        font-size: 0.95rem !important;
    }

    /* Sidebar inputs */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] textarea {
        background-color: #12473F !important;
        color: #FFFFFF !important;
        border: 1px solid #88BFB3 !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
    }

    section[data-testid="stSidebar"] input::placeholder {
        color: #D1E7E2 !important;
    }

    /* Slider text */
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stSlider span {
        color: #FFFFFF !important;
    }

    /* Slider track */
    section[data-testid="stSidebar"] .stSlider > div > div > div {
        background-color: #FFFFFF !important;
    }

    /* Slider knob */
    section[data-testid="stSidebar"] .stSlider [role="slider"] {
        background-color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        height: 18px !important;
        width: 18px !important;
    }

    /* ------------------------------------------------------- */
    /* BUTTONS — All Green, White Text */
    /* ------------------------------------------------------- */
    .stButton > button,
    section[data-testid="stSidebar"] button {
        background-color: #234F38 !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        border: none !important;
        transition: 0.2s ease !important;
    }

    .stButton > button:hover,
    section[data-testid="stSidebar"] button:hover {
        background-color: #193829 !important;
    }

    /* Download CSV button */
    .stDownloadButton > button {
        background-color: #234F38 !important;
        color: white !important;
        border-radius: 999px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
    }

    .stDownloadButton > button:hover {
        background-color: #193829 !important;
    }

    /* ------------------------------------------------------- */
    /* METRIC CARDS */
    /* ------------------------------------------------------- */
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.3rem;
        border-radius: 12px;
        border-left: 4px solid #5D7B6A;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* Logs */
    .stCodeBlock, code, pre {
        background-color: #f5f5f5 !important;
        color: #1a1a1a !important;
        padding: 0.5rem !important;
        border-radius: 6px !important;
        border: 1px solid #ddd !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #6c757d;
        font-size: 0.9rem;
        border-top: 1px solid #dee2e6;
        margin-top: 3rem;
    }

</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# ============================================================
# SIDEBAR — BASIC VERSION
# ============================================================
with st.sidebar:
    st.markdown("### Analysis Scope")

    use_coords = st.checkbox("Analyze area around a point", value=False)
    lat = lon = radius = None

    if use_coords:
        lat = st.number_input("Latitude", value=-13.0, step=0.1, format="%.4f")
        lon = st.number_input("Longitude", value=-56.0, step=0.1, format="%.4f")
        radius = st.slider("Radius (km)", min_value=25, max_value=100, value=100, step=25)

    h3_res = st.slider(
        "H3 Resolution",
        min_value=5,
        max_value=9,
        value=config["processing"].get("h3_resolution", 7)
    )

    run_btn = st.button("Run Analysis", width="stretch")   # FIXED

# ============================================================
# MAIN ANALYSIS PIPELINE
# ============================================================
if run_btn:
    with st.spinner("Preparing data…"):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(exist_ok=True)

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
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name)"
                ).execute()

                for f in results["files"]:
                    if not f["name"].endswith(".tif"):
                        continue

                    dst = raw_dir / f["name"]
                    if dst.exists():
                        continue

                    request = service.files().get_media(fileId=f["id"])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                    with open(dst, "wb") as fp:
                        fp.write(fh.getvalue())

                shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)

            except Exception as e:
                st.error(f"TIFF download failed: {e}")
                st.stop()

    cli = [
        sys.executable,
        str(PROJECT_ROOT / "run_analysis.py"),
        "--config", str(PROJECT_ROOT / "configs" / "config.yaml"),
        "--h3-resolution", str(h3_res)
    ]

    if use_coords:
        cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

    status = st.empty()
    log_box = st.empty()
    logs = []

    process = subprocess.Popen(
        cli,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
        bufsize=1
    )

    start = time.time()
    for line in process.stdout:
        logs.append(line)
        status.info(f"Running… {int(time.time()-start)}s elapsed")
        log_box.code("".join(logs[-10:]), language="bash")

    ret = process.wait()

    if ret != 0:
        st.error("Pipeline failed.")
        st.code("".join(logs))
        st.stop()

    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results missing.")
        st.stop()

    df = pd.read_csv(csv_path)
    st.success("Analysis completed!")

    # ============================================================
    # METRICS
    # ============================================================
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Total Hexagons</h4>
            <p>{len(df):,}</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Mean Score</h4>
            <p>{df['suitability_score'].mean():.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <h4>High Suitability (≥8)</h4>
            <p>{(df['suitability_score'] >= 8).sum():,}</p>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # TABLE
    # ============================================================
    st.subheader("Suitability Scores")
    st.dataframe(
        df.sort_values("suitability_score", ascending=False),
        width="stretch"     # FIXED
    )

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode(),
        "biochar_suitability_scores.csv",
        "text/csv",
        width="stretch"     # FIXED
    )

    # ============================================================
    # MAP
    # ============================================================
    map_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if map_path.exists():
        st.subheader("Interactive Map")
        st.components.v1.html(open(map_path, "r").read(), height=720)
    else:
        st.warning("Map not generated.")

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University  
    Data-driven biochar deployment for ecological impact.
</div>
""", unsafe_allow_html=True)
