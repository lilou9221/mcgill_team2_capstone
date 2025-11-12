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

# Check for required dependencies and install if missing (for Streamlit Cloud)
def ensure_dependency(package_name, import_name=None):
    """Ensure a Python package is installed, try to install if missing."""
    import_name = import_name or package_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        try:
            # Try to install the package
            import subprocess
            import sys
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name, "--quiet"
            ])
            # Try importing again
            __import__(import_name)
            return True
        except Exception as e:
            return False

# Check for PyYAML
if not ensure_dependency("PyYAML", "yaml"):
    st.error(
        "**Missing Dependency: PyYAML**\n\n"
        "PyYAML could not be installed automatically. Please ensure it's in requirements.txt:\n\n"
        "```txt\nPyYAML>=6.0\n```\n\n"
        "For Streamlit Cloud, restart your deployment after updating requirements.txt."
    )
    st.stop()

import yaml

# Project setup
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Load config
@st.cache_data
def load_config():
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path, encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# Page config
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {padding-top: 2rem;}
    .stButton > button {
        background-color: #5D7B6A;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #4A5F54;
        box-shadow: 0 4px 8px rgba(93,123,106,0.3);
    }
    .metric-card {
        background-color: #1A1F2B;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #5D7B6A;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: 700;
        text-align: center;
        color: #FAFAFA;
        margin-bottom: 0.5rem;
    }
    .header-subtitle {
        text-align: center;
        color: #A8B5A2;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #6B7A6E;
        font-size: 0.9rem;
        border-top: 1px solid #2A2F3B;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision mapping for sustainable biochar application in Mato Grosso, Brazil</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Analysis Scope")
    use_coords = st.checkbox("Analyze 100 km radius around a point", value=False)
    lat = lon = None
    if use_coords:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=-13.0, step=0.1, format="%.4f")
        lon = col2.number_input("Longitude", value=-56.0, step=0.1, format="%.4f")
        st.info("Fixed radius: **100 km**")
    else:
        st.info("Full **Mato Grosso state** analysis")
    h3_res = st.slider("H3 resolution", 5, 9, config["processing"].get("h3_resolution", 7))
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

# Run analysis
if run_btn:
    with st.spinner("Initializing..."):
        tmp_raw = Path(tempfile.mkdtemp(prefix="rc_raw_"))
        raw_dir = PROJECT_ROOT / config["data"]["raw"]
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Check if GeoTIFFs are already cached
        if raw_dir.exists() and len(list(raw_dir.glob("*.tif"))) >= 5:
            st.info("Using cached GeoTIFFs")
            shutil.copytree(raw_dir, tmp_raw, dirs_exist_ok=True)
        else:
            st.warning("GeoTIFFs not found. Downloading from Google Drive...")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload

                # Load credentials from Streamlit Secrets
                creds_info = json.loads(st.secrets["google_drive"]["credentials"])
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly']
                )

                # Build Drive service
                service = build('drive', 'v3', credentials=credentials)

                # Get folder ID
                folder_id = config["drive"]["raw_data_folder_id"]

                # List .tif files in folder
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

        # === RUN MAIN PIPELINE ===
        # Use wrapper script that ensures dependencies are installed
        wrapper_script = PROJECT_ROOT / "run_analysis.py"
        
        # Prepare command arguments
        cli = [
            sys.executable, str(wrapper_script),
            "--config", str(PROJECT_ROOT / "configs" / "config.yaml"),
            "--h3-resolution", str(h3_res),
        ]
        if lat and lon:
            cli += ["--lat", str(lat), "--lon", str(lon), "--radius", "100"]

        # Run main pipeline with real-time output streaming
        status_container = st.empty()
        log_container = st.empty()
        
        with status_container.container():
            st.info("🚀 Starting analysis pipeline... This may take 2-5 minutes for a 100km radius.")
        
        # Use Popen to stream output in real-time
        # Set PYTHONUNBUFFERED=1 to ensure all print statements flush immediately
        proc = subprocess.Popen(
            cli,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            env={
                **os.environ, 
                "PYTHONPATH": str(PROJECT_ROOT),
                "PYTHONUNBUFFERED": "1"  # Force unbuffered output for real-time streaming
            },
            universal_newlines=True
        )
        
        # Stream output in real-time
        output_lines = []
        last_update = 0
        update_interval = 0.5  # Update UI every 0.5 seconds
        
        import time
        start_time = time.time()
        
        while True:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            
            output_lines.append(line)
            current_time = time.time()
            
            # Update UI periodically to show progress
            if current_time - last_update > update_interval:
                elapsed = int(current_time - start_time)
                with status_container.container():
                    st.info(f"⏳ Running... ({elapsed}s elapsed)")
                
                # Show last few lines of output
                recent_lines = output_lines[-10:] if len(output_lines) > 10 else output_lines
                with log_container.expander("📋 View progress log", expanded=False):
                    st.code("".join(recent_lines))
                
                last_update = current_time
        
        # Get remaining output
        remaining_output, _ = proc.communicate()
        if remaining_output:
            output_lines.append(remaining_output)
        
        # Wait for process to complete
        returncode = proc.returncode
        full_output = "".join(output_lines)
        elapsed_total = int(time.time() - start_time)
        
        # Update final status
        with status_container.container():
            if returncode == 0:
                st.success(f"✅ Analysis completed successfully! ({elapsed_total}s)")
            else:
                st.error(f"❌ Analysis failed after {elapsed_total}s")
        
        shutil.rmtree(tmp_raw, ignore_errors=True)

        if returncode != 0:
            st.error("Analysis failed")
            
            # Check if it's a yaml import error
            error_output = full_output
            if "ModuleNotFoundError" in error_output and "yaml" in error_output.lower():
                st.error(
                    "**PyYAML Missing in Subprocess**\n\n"
                    "The analysis pipeline requires PyYAML. Please ensure `pyyaml>=6.0` is in requirements.txt "
                    "and restart your Streamlit Cloud deployment.\n\n"
                    "Current requirements.txt should include:\n"
                    "```txt\npyyaml>=6.0\n```"
                )
            
            with st.expander("View error log"):
                st.code(error_output)
            st.stop()

    # === DISPLAY RESULTS ===
    csv_path = PROJECT_ROOT / config["data"]["processed"] / "suitability_scores.csv"
    if not csv_path.exists():
        st.error("Results not generated.")
        st.stop()

    df = pd.read_csv(csv_path)
    st.success("Analysis complete!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <h4 style="margin:0;color:#5D7B6A">Hexagons</h4>
            <p style="font-size:1.8rem;margin:0.4rem 0;color:#FAFAFA">{len(df):,}</p>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        mean = df['suitability_score'].mean()
        st.markdown(f'''
        <div class="metric-card">
            <h4 style="margin:0;color:#5D7B6A">Mean Score</h4>
            <p style="font-size:1.8rem;margin:0.4rem 0;color:#FAFAFA">{mean:.2f}/10</p>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        high = (df['suitability_score'] >= 8).sum()
        st.markdown(f'''
        <div class="metric-card">
            <h4 style="margin:0;color:#5D7B6A">High Suitability</h4>
            <p style="font-size:1.8rem;margin:0.4rem 0;color:#FAFAFA">{high:,}</p>
        </div>
        ''', unsafe_allow_html=True)

    st.subheader("Suitability Scores")
    st.dataframe(df.sort_values("suitability_score", ascending=False), use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode()
    st.download_button(
        "Download CSV",
        csv_data,
        "biochar_suitability_scores.csv",
        "text/csv",
        use_container_width=True
    )

    html_path = PROJECT_ROOT / config["output"]["html"] / "suitability_map.html"
    if html_path.exists():
        st.subheader("Interactive Suitability Map")
        with open(html_path, "r", encoding="utf-8") as f:
            st.components.v1.html(f.read(), height=700, scrolling=True)
    else:
        st.warning("Map not generated.")

# Footer
st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone<br>
    Promoting biodiversity through science-driven biochar deployment
</div>
""", unsafe_allow_html=True)
