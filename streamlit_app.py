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

# === Dependency check ===
def ensure_dependency(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name, "--quiet"]
            )
            __import__(import_name)
            return True
        except Exception:
            return False

if not ensure_dependency("PyYAML", "yaml"):
    st.error("Missing dependency: PyYAML. Add PyYAML>=6.0 to requirements.txt.")
    st.stop()

import yaml

# === Project setup ===
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# === Page config ===
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === COMPLETE DASHBOARD CSS (GREEN / PURPLE / WHITE) ===
st.markdown(
    """
<style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --green: #234F38;
        --purple: #6A4E77;
        --text: #111827;
        --muted: #6B7280;
        --border: #E5E7EB;
        --bg: #F7F8FA;
        --white: #FFFFFF;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: var(--bg);
    }

    /* MAIN CONTAINER WIDTH */
    .main .block-container {
        max-width: 1180px;
        margin: 0 auto;
        padding-top: 1.5rem;
    }

    /* ---------------------- HEADER ---------------------- */
    .rc-header {
        margin-bottom: 1.8rem;
    }
    .rc-header-kicker {
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: .15em;
        font-weight: 600;
        color: var(--purple);
        margin-bottom: 0.1rem;
    }
    .rc-header-title {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: .3rem;
    }
    .rc-header-subtitle {
        font-size: .95rem;
        color: var(--muted);
        max-width: 720px;
        line-height: 1.45;
    }

    /* ---------------------- SIDEBAR ---------------------- */
    section[data-testid="stSidebar"] {
        background-color: var(--white) !important;
        border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] * {
        color: var(--text) !important;
        font-size: .95rem;
    }

    /* Fix all sidebar input boxes */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] textarea {
        background-color: var(--white) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
    }

    section[data-testid="stSidebar"] input::placeholder {
        color: var(--muted) !important;
    }

    /* Slider text visibility */
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stSlider span {
        color: var(--text) !important;
    }

    /* ---------------------- BUTTONS ---------------------- */
    .stButton > button {
        background-color: var(--green) !important;
        color: white !important;
        padding: .5rem 1.3rem !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.08) !important;
        transition: all .15s ease;
    }
    .stButton > button:hover {
        background-color: #193828 !important;
        transform: translateY(-1px);
        box-shadow: 0 10px 26px rgba(0,0,0,0.12) !important;
    }

    /* ---------------------- METRIC CARDS ---------------------- */
    .metric-card {
        background: var(--white);
        padding: 1.3rem;
        border-radius: 14px;
        border: 1px solid var(--border);
        box-shadow: 0 6px 16px rgba(0,0,0,0.05);
        transition: 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 26px rgba(0,0,0,0.08);
    }
    .metric-card h4 {
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: .4rem;
    }
    .metric-card p {
        font-size: 2rem;
        color: var(--text);
        font-weight: 700;
        margin: 0;
    }

    /* ---------------------- DATAFRAME ---------------------- */
    .stDataFrame {
        background: white;
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.05) !important;
    }

    /* ---------------------- FOOTER ---------------------- */
    .footer {
        margin-top: 2rem;
        padding: 2rem 0 1.5rem;
        text-align: center;
        color: var(--muted);
        border-top: 1px solid var(--border);
    }
    .footer strong {
        color: var(--green);
    }

</style>
""",
    unsafe_allow_html=True,
)

# ---------------------- HEADER ----------------------
st.markdown(
    """
<div class="rc-header">
    <div class="rc-header-kicker">Residual Carbon • Mato Grosso</div>
    <div class="rc-header-title">Biochar Suitability Mapper</div>
    <div class="rc-header-subtitle">
        A professional dashboard for geospatial biochar suitability analysis using H3 hexagons
        and multiple environmental layers.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------- SIDEBAR ----------------------
with st.sidebar:
    st.markdown("### Analysis Scope")

    use_coords = st.checkbox("Analyze radius around a point", value=False)

    lat = lon = radius = None
    if use_coords:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f")
        lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
        st.info(f"Radius: {radius} km")
    else:
        st.info("Analysing full Mato Grosso state.")

    h3_res = st.slider(
        "H3 Resolution", 5, 9, config["processing"].get("h3_resolution", 7)
    )

    run_btn = st.button("Run Analysis", use_container_width=True)

# ---------------------- ANALYSIS PIPELINE ----------------------
if run_btn:
    with st.spinner("Initializing…"):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(exist_ok=True, parents=True)

        # Use cached GeoTIFFs
        if len(list(raw_dir.glob("*.tif"))) >= 5:
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning("Downloading GeoTIFFs from Drive…")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload

                creds_info = json.loads(st.secrets["google_drive"]["credentials"])
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=["https://www.googleapis.com/auth/drive.readonly"],
                )
                service = build("drive", "v3", credentials=credentials)

                folder_id = config["drive"]["raw_data_folder_id"]
                results = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields="files(id, name)",
                    )
                    .execute()
                )

                tif_files = [
                    f for f in results["files"] if f["name"].endswith(".tif")
                ]
                for file in tif_files:
                    path = raw_dir / file["name"]
                    if path.exists():
                        continue
                    request = service.files().get_media(fileId=file["id"])
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    fh.seek(0)
                    with open(path, "wb") as f:
                        f.write(fh.read())

                shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)

            except Exception as e:
                st.error(f"Drive error: {e}")
                st.stop()

        # Run pipeline
        wrapper_script = PROJECT_ROOT / "run_analysis.py"
        cli = [
            sys.executable,
            str(wrapper_script),
            "--config",
            str(PROJECT_ROOT / "configs" / "config.yaml"),
            "--h3-resolution",
            str(h3_res),
        ]
        if lat and lon and radius:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

        process = subprocess.Popen(
            cli,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        logs = []
        log_box = st.empty()
        start = time.time()

        for line in process.stdout:
            logs.append(line)
            log_box.code("".join(logs[-12:]), language="bash")

        ret = process.wait()

        if ret != 0:
            st.error("Pipeline failed.")
            st.code("".join(logs))
            st.stop()

    # ---------------------- DISPLAY RESULTS ----------------------
    df_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not df_path.exists():
        st.error("Results CSV not generated.")
        st.stop()

    df = pd.read_csv(df_path)
    st.success("Analysis completed successfully.")

    # === METRIC CARDS ===
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4>Total Hexagons</h4>
            <p>{len(df):,}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4>Mean Score</h4>
            <p>{df['suitability_score'].mean():.2f}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
        <div class='metric-card'>
            <h4>High Suitability (≥8)</h4>
            <p>{(df['suitability_score'] >= 8).sum():,}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # === TABLE ===
    st.subheader("Suitability Scores")
    st.dataframe(
        df.sort_values("suitability_score", ascending=False),
        use_container_width=True,
    )

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode(),
        "biochar_scores.csv",
        "text/csv",
    )

    # === MAP ===
    map_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if map_path.exists():
        st.subheader("Interactive Map")
        st.components.v1.html(map_path.read_text(), height=720, scrolling=True)
    else:
        st.warning("Map not generated.")

# ---------------------- FOOTER ----------------------
st.markdown(
    """
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University  
    Data-driven biochar deployment for ecological impact.
</div>
""",
    unsafe_allow_html=True,
)
