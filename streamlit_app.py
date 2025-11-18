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

# === Page config (set as early as possible) ===
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# === GLOBAL CSS – earthy green, clean academic style ===
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main container */
    .main .block-container {
        padding-top: 2.5rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    .stApp {
        background: #f5f7fa;
    }

    :root {
        --rc-green: #2d6b5e;
        --rc-green-dark: #1f4e45;
        --rc-green-soft: #e4f1ec;
        --text-primary: #111827;
        --text-secondary: #6b7280;
        --border-subtle: #e5e7eb;
        --bg-card: #ffffff;
        --bg-soft: #f9fafb;
    }

    /* Header / Hero */
    .rc-hero {
        background: linear-gradient(135deg, #ffffff 0%, #f3f7f5 45%, #e8f2ee 100%);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
        margin-bottom: 2rem;
    }

    .rc-hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.03em;
        margin-bottom: 0.4rem;
    }

    .rc-hero-subtitle {
        font-size: 1.05rem;
        color: var(--text-secondary);
        max-width: 700px;
        line-height: 1.6;
        margin-bottom: 1.4rem;
    }

    .rc-hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        background: rgba(45, 107, 94, 0.07);
        color: var(--rc-green);
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.75rem;
    }

    .rc-hero-pill span {
        font-size: 0.9rem;
    }

    .rc-hero-metadata {
        display: flex;
        flex-wrap: wrap;
        gap: 1.25rem;
        font-size: 0.9rem;
        color: var(--text-secondary);
        margin-top: 0.5rem;
    }

    .rc-hero-meta-item {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.02);
        border: 1px solid rgba(148, 163, 184, 0.35);
    }

    .rc-hero-meta-dot {
        width: 7px;
        height: 7px;
        border-radius: 999px;
        background: var(--rc-green);
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--rc-green) !important;
        color: #ffffff !important;
        border-radius: 999px !important;
        border: none !important;
        padding: 0.75rem 1.7rem !important;
        font-weight: 600 !important;
        font-size: 0.98rem !important;
        letter-spacing: 0.02em;
        transition: all 0.22s ease !important;
        box-shadow: 0 12px 30px rgba(45, 107, 94, 0.28) !important;
    }

    .stButton > button:hover {
        background-color: var(--rc-green-dark) !important;
        transform: translateY(-1px);
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.35) !important;
    }

    .stButton > button:focus {
        outline: 2px solid rgba(45, 107, 94, 0.4) !important;
        outline-offset: 2px !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--border-subtle);
    }

    section[data-testid="stSidebar"] .sidebar-content {
        padding-top: 1rem;
    }

    .rc-sidebar-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
        color: var(--text-primary);
    }

    .rc-sidebar-section-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ca3af;
        margin-top: 1rem;
        margin-bottom: 0.3rem;
    }

    .rc-sidebar-divider {
        border-top: 1px solid var(--border-subtle);
        margin: 0.8rem 0 0.5rem;
    }

    /* Metric cards */
    .metric-wrapper {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: var(--bg-card);
        padding: 1.5rem 1.6rem;
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        transition: all 0.22s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::after {
        content: "";
        position: absolute;
        inset: 0;
        opacity: 0;
        background: radial-gradient(circle at top left, rgba(45, 107, 94, 0.10), transparent 55%);
        transition: opacity 0.3s ease;
        pointer-events: none;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 45px rgba(15, 23, 42, 0.12);
    }

    .metric-card:hover::after {
        opacity: 1;
    }

    .metric-label {
        color: #6b7280;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        margin-bottom: 0.4rem;
        font-weight: 600;
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.1;
    }

    .metric-caption {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.3rem;
    }

    /* Section headings */
    .rc-section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-top: 1.8rem;
        margin-bottom: 0.2rem;
    }

    .rc-section-caption {
        font-size: 0.9rem;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }

    /* DataFrame */
    .stDataFrame {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.5);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }

    /* Status / log area */
    .rc-status-info {
        font-size: 0.9rem;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: var(--rc-green) !important;
        color: #ffffff !important;
        border-radius: 999px !important;
        border: none !important;
        font-weight: 600 !important;
    }

    .stDownloadButton > button:hover {
        background-color: var(--rc-green-dark) !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 2.5rem 0 2rem;
        color: var(--text-secondary);
        font-size: 0.92rem;
        border-top: 1px solid var(--border-subtle);
        margin-top: 2.5rem;
    }
    .footer strong {
        color: var(--rc-green);
    }

    /* Small tweaks */
    .stAlert {
        border-radius: 12px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# === HEADER / HERO ===
hero_col1, hero_col2 = st.columns([1.7, 1.3])

with hero_col1:
    st.markdown(
        """
<div class="rc-hero">
    <div class="rc-hero-pill">
        <span>🌱 Biochar Suitability Mapper</span>
    </div>
    <div class="rc-hero-title">
        Precision mapping for sustainable biochar application
    </div>
    <div class="rc-hero-subtitle">
        Explore where biochar can maximize climate and soil benefits across Mato Grosso, Brazil. 
        This tool aggregates environmental layers into a spatial suitability score using an H3 
        hexagonal grid.
    </div>
    <div class="rc-hero-metadata">
        <div class="rc-hero-meta-item">
            <div class="rc-hero-meta-dot"></div>
            Mato Grosso • Brazil
        </div>
        <div class="rc-hero-meta-item">
            <div class="rc-hero-meta-dot"></div>
            H3-based spatial aggregation
        </div>
        <div class="rc-hero-meta-item">
            <div class="rc-hero-meta-dot"></div>
            Multi-layer suitability scoring
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

with hero_col2:
    st.markdown(
        """
<div class="rc-hero" style="padding: 1.4rem 1.6rem; min-height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
    <div>
        <div class="metric-label">Project</div>
        <div class="metric-value" style="font-size: 1.4rem;">Residual Carbon</div>
        <div class="metric-caption" style="margin-bottom: 1.1rem;">
            McGill University capstone project on biodiversity and biochar deployment.
        </div>

        <div class="metric-label">How to use</div>
        <ul style="margin: 0.3rem 0 0.6rem 1rem; color: #4b5563; font-size: 0.9rem;">
            <li>Select analysis scope in the sidebar (full state or radius around a point).</li>
            <li>Tune the H3 resolution if needed.</li>
            <li>Run the analysis and explore the summary, data table, and interactive map.</li>
        </ul>
    </div>
    <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.8rem;">
        Data layers and scoring logic are defined in <code>configs/config.yaml</code>.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

# === SIDEBAR ===
with st.sidebar:
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)

    st.markdown('<div class="rc-sidebar-title">Analysis Setup</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rc-sidebar-section-title">Area of interest</div>',
        unsafe_allow_html=True,
    )

    use_coords = st.checkbox("Analyze radius around a point", value=False)
    lat = lon = radius = None

    if use_coords:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f")
        lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f")
        radius = st.slider(
            "Radius (km)", min_value=25, max_value=100, value=100, step=25
        )
        st.info(
            f"Analysis radius: **{radius} km** around the selected point in Mato Grosso.",
            icon="🟢",
        )
    else:
        st.info(
            "Running on the **full state of Mato Grosso**. This may take longer but "
            "gives a complete picture.",
            icon="🗺️",
        )

    st.markdown('<div class="rc-sidebar-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="rc-sidebar-section-title">Spatial resolution</div>',
        unsafe_allow_html=True,
    )
    h3_res = st.slider(
        "H3 resolution",
        5,
        9,
        config["processing"].get("h3_resolution", 7),
        help="Higher values = finer hexagons (more detail, heavier computation).",
    )

    st.markdown('<div class="rc-sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="rc-sidebar-section-title">Run</div>',
        unsafe_allow_html=True,
    )
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# === MAIN ANALYSIS ===
if run_btn:
    with st.spinner("Initializing analysis environment..."):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Check cached GeoTIFFs
        if raw_dir.exists() and len(list(raw_dir.glob("*.tif"))) >= 5:
            st.info("Using cached GeoTIFF layers for Mato Grosso.", icon="✅")
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning(
                "GeoTIFF files not found locally. Attempting to download them from Google Drive...",
                icon="📥",
            )
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
                        q=f"'{folder_id}' in parents and trashed=false and mimeType!='application/vnd.google-apps.folder'",
                        fields="files(id, name)",
                    )
                    .execute()
                )
                files = results.get("files", [])
                tif_files = [f for f in files if f["name"].endswith(".tif")]

                if not tif_files:
                    st.error("No `.tif` raster files found in the configured Drive folder.")
                    st.stop()

                for file in tif_files:
                    filepath = raw_dir / file["name"]
                    if not filepath.exists():
                        with st.spinner(f"Downloading **{file['name']}** from Drive..."):
                            request = service.files().get_media(fileId=file["id"])
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                            fh.seek(0)
                            with open(filepath, "wb") as f:
                                f.write(fh.read())
                    else:
                        st.info(f"Using existing file: **{file['name']}**", icon="📁")
                st.success("All GeoTIFF layers downloaded successfully.", icon="✅")
                shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
            except Exception as e:
                st.error(f"Drive download failed: {e}")
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
        if lat is not None and lon is not None and radius:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", str(radius)]

        status_container = st.empty()
        log_container = st.empty()

        with status_container.container():
            st.info(
                "Starting analysis pipeline. This typically takes a few minutes "
                "depending on resolution and area of interest.",
                icon="⏳",
            )

        proc = subprocess.Popen(
            cli,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={
                **os.environ,
                "PYTHONPATH": str(PROJECT_ROOT),
                "PYTHONUNBUFFERED": "1",
            },
            universal_newlines=True,
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
                        st.info(
                            f"Running spatial pipeline… **{elapsed}s** elapsed.",
                            icon="🔄",
                        )
                    recent = output_lines[-12:]
                    with log_container.expander(
                        "View live pipeline log (last ~12 lines)", expanded=False
                    ):
                        st.code("".join(recent), language="bash")
                    last_update = current_time
            else:
                time.sleep(0.1)

        returncode = proc.returncode
        full_output = "".join(output_lines)
        elapsed_total = int(time.time() - start_time)

        shutil.rmtree(tmp_raw, ignore_errors=True)

        with status_container.container():
            if returncode == 0:
                st.success(
                    f"Analysis completed successfully in **{elapsed_total}s**.",
                    icon="✅",
                )
            else:
                st.error(
                    f"Analysis failed after **{elapsed_total}s**. See error log below.",
                    icon="❌",
                )
                with st.expander("View full error log"):
                    st.code(full_output, language="bash")
                st.stop()

    # === DISPLAY RESULTS ===
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results file `suitability_scores.csv` was not generated.")
        st.stop()

    df = pd.read_csv(csv_path)

    st.markdown(
        """
<div class="rc-section-title">Results overview</div>
<div class="rc-section-caption">
    Summary statistics, full hexagon-level table, and the interactive suitability map.
</div>
""",
        unsafe_allow_html=True,
    )

    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
<div class="metric-wrapper">
  <div class="metric-card">
    <div class="metric-label">Total hexagons</div>
    <div class="metric-value">{len(df):,}</div>
    <div class="metric-caption">Number of H3 cells analyzed within the selected extent.</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with col2:
        mean_score = df["suitability_score"].mean()
        st.markdown(
            f"""
<div class="metric-wrapper">
  <div class="metric-card">
    <div class="metric-label">Mean suitability</div>
    <div class="metric-value">{mean_score:.2f}/10</div>
    <div class="metric-caption">Average biochar suitability score across all hexagons.</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    with col3:
        high_suitability = (df["suitability_score"] >= 8).sum()
        st.markdown(
            f"""
<div class="metric-wrapper">
  <div class="metric-card">
    <div class="metric-label">High suitability (≥ 8)</div>
    <div class="metric-value">{high_suitability:,}</div>
    <div class="metric-caption">Hexagons with top-tier suitability for biochar application.</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # Tabs for table / map
    tab_summary, tab_table, tab_map = st.tabs(["📊 Summary table", "📑 Full DataFrame", "🗺️ Interactive map"])

    with tab_summary:
        st.markdown(
            "Explore the top-scoring locations. You can sort or filter the table in-place.",
        )
        st.dataframe(
            df.sort_values("suitability_score", ascending=False).head(200),
            use_container_width=True,
            hide_index=True,
        )

    with tab_table:
        st.markdown(
            "Complete hexagon-level dataset. Download the CSV for further analysis in Python, R, or Excel."
        )
        st.dataframe(
            df.sort_values("suitability_score", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df.to_csv(index=False).encode()
        st.download_button(
            "Download full results as CSV",
            csv_data,
            "biochar_suitability_scores.csv",
            "text/csv",
            use_container_width=True,
        )

    with tab_map:
        html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
        if html_path.exists():
            st.markdown(
                "Interactive suitability map rendered from the processed H3 dataset."
            )
            with open(html_path, "r", encoding="utf-8") as f:
                st.components.v1.html(f.read(), height=720, scrolling=True)
        else:
            st.warning("Interactive map HTML was not generated for this run.")

# === Footer ===
st.markdown(
    """
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Promoting biodiversity through science-driven biochar deployment
</div>
""",
    unsafe_allow_html=True,
)
