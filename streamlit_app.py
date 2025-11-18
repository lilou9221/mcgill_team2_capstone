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
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--quiet"])
            __import__(import_name)
            return True
        except Exception:
            return False

if not ensure_dependency("PyYAML", "yaml"):
    st.error(
        "**Missing Dependency: PyYAML**\n\n"
        "Add `PyYAML>=6.0` to your requirements.txt and redeploy."
    )
    st.stop()
import yaml

# === Project setup ===
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# === Page config ===
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === DASHBOARD CSS — forest green, muted purple, light background ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --rc-green: #234F38;
        --rc-purple: #6A4E77;
        --bg-main: #F7F8FA;
        --bg-card: #FFFFFF;
        --text-main: #111827;
        --text-muted: #6B7280;
        --border: #E5E7EB;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: var(--bg-main);
    }

    /* Main container width */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1180px;
        margin: 0 auto;
    }

    /* Header */
    .rc-header {
        margin-bottom: 1.8rem;
    }
    .rc-header-kicker {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: var(--rc-purple);
        margin-bottom: 0.25rem;
    }
    .rc-header-title {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-main);
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .rc-header-subtitle {
        font-size: 0.95rem;
        color: var(--text-muted);
        max-width: 720px;
        line-height: 1.5;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] * {
        color: var(--text-main);
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 1.05rem;
        margin-bottom: 0.4rem;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--rc-green) !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
        border: none !important;
        padding: 0.5rem 1.3rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: background-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.07) !important;
    }
    .stButton > button:hover {
        background-color: #193828 !important;
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12) !important;
    }

    /* Metric cards */
    .metric-card {
        background: var(--bg-card);
        padding: 1.3rem 1.4rem;
        border-radius: 14px;
        border: 1px solid var(--border);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }
    .metric-card:hover {
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.09);
        transform: translateY(-1px);
    }
    .metric-card h4 {
        color: var(--text-muted);
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin: 0 0 0.45rem 0;
    }
    .metric-card p {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-main);
        margin: 0;
        line-height: 1.2;
    }

    /* DataFrame wrapper */
    .stDataFrame {
        border-radius: 12px;
        border: 1px solid var(--border);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        background: var(--bg-card);
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: var(--rc-green) !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.45rem 1.1rem !important;
    }
    .stDownloadButton > button:hover {
        background-color: #193828 !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2.2rem 0 1.8rem;
        color: var(--text-muted);
        font-size: 0.9rem;
        border-top: 1px solid var(--border);
        margin-top: 2.2rem;
    }
    .footer strong {
        color: var(--rc-green);
    }
</style>
""", unsafe_allow_html=True)

# === Header ===
st.markdown("""
<div class="rc-header">
  <div class="rc-header-kicker">Residual Carbon • Mato Grosso</div>
  <div class="rc-header-title">Biochar Suitability Mapper</div>
  <div class="rc-header-subtitle">
    Precision mapping for sustainable biochar application across Mato Grosso, Brazil.
    Aggregates environmental layers into an H3-based suitability score to support
    data-driven deployment decisions.
  </div>
</div>
""", unsafe_allow_html=True)

# === Sidebar ===
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze radius around a point", value=False)
    lat = lon = radius = None
    if use_coords:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f")
        lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f")
        radius = st.slider("Radius (km)", min_value=25, max_value=100, value=100, step=25)
        st.info(f"Analysis radius: **{radius} km** around the selected point.")
    else:
        st.info("Running on the **full state of Mato Grosso**.")

    h3_res = st.slider(
        "H3 resolution", 5, 9,
        config["processing"].get("h3_resolution", 7),
        help="Higher = more detail, more hexagons, longer runtime."
    )
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# === Main Analysis ===
if run_btn:
    with st.spinner("Initializing analysis..."):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Check cached GeoTIFFs
        if raw_dir.exists() and len(list(raw_dir.glob("*.tif"))) >= 5:
            st.info("Using cached GeoTIFFs.")
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning("GeoTIFFs not found locally. Downloading from Google Drive...")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload

                creds_info = json.loads(st.secrets["google_drive"]["credentials"])
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                service = build('drive', 'v3', credentials=credentials)
                folder_id = config["drive"]["raw_data_folder_id"]

                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'",
                    fields="files(id, name)"
                ).execute()
                files = results.get('files', [])
                tif_files = [f for f in files if f['name'].endswith('.tif')]

                if not tif_files:
                    st.error("No .tif files found in Drive folder.")
                    st.stop()

                for file in tif_files:
                    filepath = raw_dir / file['name']
                    if not filepath.exists():
                        with st.spinner(f"Downloading {file['name']}..."):
                            request = service.files().get_media(fileId=file['id'])
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                            fh.seek(0)
                            with open(filepath, 'wb') as f:
                                f.write(fh.read())
                    else:
                        st.info(f"{file['name']} already downloaded")
                st.success("All GeoTIFFs downloaded.")
                shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
            except Exception as e:
                st.error(f"Drive download failed: {e}")
                st.stop()

        # Run pipeline
        wrapper_script = PROJECT_ROOT / "run_analysis.py"
        cli = [
            sys.executable, str(wrapper_script),
            "--config", str(PROJECT_ROOT / "configs" / "config.yaml"),
            "--h3-resolution", str(h3_res),
        ]
        if lat is not None and lon is not None and radius:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

        status_container = st.empty()
        log_container = st.empty()
        with status_container.container():
            st.info("Starting analysis pipeline...")

        proc = subprocess.Popen(
            cli,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT), "PYTHONUNBUFFERED": "1"},
            universal_newlines=True
        )

        output_lines = []
        last_update = 0
        update_interval = 0.5
        start_time = time.time()

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                output_lines.append(line)
                current_time = time.time()
                if current_time - last_update > update_interval:
                    elapsed = int(current_time - start_time)
                    with status_container.container():
                        st.info(f"Running... ({elapsed}s elapsed)")
                    recent = output_lines[-10:]
                    with log_container.expander("View progress log", expanded=False):
                        st.code("".join(recent))
                    last_update = current_time
            else:
                time.sleep(0.1)

        returncode = proc.returncode
        full_output = "".join(output_lines)
        elapsed_total = int(time.time() - start_time)

        shutil.rmtree(tmp_raw, ignore_errors=True)

        with status_container.container():
            if returncode == 0:
                st.success(f"Analysis completed successfully ({elapsed_total}s).")
            else:
                st.error(f"Analysis failed after {elapsed_total}s.")
                with st.expander("View error log"):
                    st.code(full_output)
                st.stop()

    # === Display Results ===
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results file not generated.")
        st.stop()

    df = pd.read_csv(csv_path)
    st.success("Analysis complete.")

    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <h4>Hexagons</h4>
            <p>{len(df):,}</p>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        mean_score = df['suitability_score'].mean()
        st.markdown(f'''
        <div class="metric-card">
            <h4>Mean score</h4>
            <p>{mean_score:.2f}/10</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        high_suitability = (df['suitability_score'] >= 8).sum()
        st.markdown(f'''
        <div class="metric-card">
            <h4>High suitability (≥ 8)</h4>
            <p>{high_suitability:,}</p>
        </div>
        ''', unsafe_allow_html=True)

    st.subheader("Suitability scores (all H3 hexagons)")
    st.dataframe(df.sort_values("suitability_score", ascending=False),
                 use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode()
    st.download_button(
        "Download results as CSV",
        csv_data,
        "biochar_suitability_scores.csv",
        "text/csv",
        use_container_width=True
    )

    html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if html_path.exists():
        st.subheader("Interactive suitability map")
        with open(html_path, "r", encoding="utf-8") as f:
            st.components.v1.html(f.read(), height=720, scrolling=True)
    else:
        st.warning("Interactive map not generated.")

# === Footer ===
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Promoting biodiversity through science-driven biochar deployment
</div>
""", unsafe_allow_html=True)
