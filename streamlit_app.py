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
    page_icon="leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === FINAL CSS — Exact Residual Carbon style (earthy green, clean, formal) ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    .main > div {padding-top: 2rem;}
    .stApp {background-color: #ffffff;}
    
    /* Colors - Exact Residual Carbon palette */
    :root {
        --rc-green: #2d6b5e;
        --rc-green-dark: #1f4e45;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --border: #e2e8f0;
        --bg-light: #f8fafc;
    }
    
    /* Header */
    .header-title {
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
        letter-spacing: -0.8px;
    }
    .header-subtitle {
        text-align: center;
        color: var(--text-secondary);
        font-size: 1.15rem;
        max-width: 820px;
        margin: 0 auto 3rem auto;
        line-height: 1.6;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--rc-green) !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.25s ease !important;
    }
    .stButton > button:hover {
        background-color: var(--rc-green-dark) !important;
        box-shadow: 0 8px 25px rgba(45, 107, 94, 0.25) !important;
        transform: translateY(-1px);
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.75rem;
        border-radius: 12px;
        border: 1px solid var(--border);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.25s ease;
        text-align: left;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .metric-card h4 {
        color: var(--rc-green);
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 0 0 0.5rem 0;
    }
    .metric-card p {
        font-size: 2.4rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
        line-height: 1;
    }
    
    /* DataFrame */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid var(--border);
    }
    .stSidebar .stMarkdown h3 {color: var(--text-primary);}
    
    /* Code blocks */
    code, pre, .stCodeBlock {
        background: var(--bg-light) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background-color: var(--rc-green) !important;
        color: white !important;
    }
    .stDownloadButton > button:hover {
        background-color: var(--rc-green-dark) !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 3rem 0 2rem;
        color: var(--text-secondary);
        font-size: 0.95rem;
        border-top: 1px solid var(--border);
        margin-top: 4rem;
    }
    .footer strong {color: var(--rc-green);}
</style>
""", unsafe_allow_html=True)

# === Header ===
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

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
        st.info(f"Analysis radius: {radius} km")
    else:
        st.info("Full Mato Grosso state analysis")
    
    h3_res = st.slider("H3 resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# === Main Analysis ===
if run_btn:
    with st.spinner("Initializing..."):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Check cached GeoTIFFs
        if raw_dir.exists() and len(list(raw_dir.glob("*.tif"))) >= 5:
            st.info("Using cached GeoTIFFs")
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning("GeoTIFFs not found. Downloading from Google Drive...")
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
                st.success("All GeoTIFFs downloaded!")
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
        if lat and lon and radius:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

        status_container = st.empty()
        log_container = st.empty()
        with status_container.container():
            st.info("Starting analysis pipeline. This may take 2–5 minutes.")

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
                st.success(f"Analysis completed successfully ({elapsed_total}s)")
            else:
                st.error(f"Analysis failed after {elapsed_total}s")
                with st.expander("View error log"):
                    st.code(full_output)
                st.stop()

    # === Display Results ===
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results file not generated.")
        st.stop()

    df = pd.read_csv(csv_path)
    st.success("Analysis complete")

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
            <h4>Mean Score</h4>
            <p>{mean_score:.2f}/10</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        high_suitability = (df['suitability_score'] >= 8).sum()
        st.markdown(f'''
        <div class="metric-card">
            <h4>High Suitability (≥8)</h4>
            <p>{high_suitability:,}</p>
        </div>
        ''', unsafe_allow_html=True)

    st.subheader("Suitability Scores")
    st.dataframe(df.sort_values("suitability_score", ascending=False), use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode()
    st.download_button(
        "Download Results as CSV",
        csv_data,
        "biochar_suitability_scores.csv",
        "text/csv",
        use_container_width=True
    )

    html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if html_path.exists():
        st.subheader("Interactive Suitability Map")
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
