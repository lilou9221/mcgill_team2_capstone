import streamlit as st
from src.utils.initialization import initialize_project
from src.data.processing.user_input import get_user_area_of_interest
from src.data.processing.raster_clip import clip_all_rasters_to_circle
from src.data.processing.raster_to_csv import convert_all_rasters_to_csv
from src.data.processing.h3_converter import process_all_csv_files_with_h3
from src.analysis.suitability import process_csv_files_with_suitability_scores
from src.visualization.map_generator import create_suitability_map
from src.utils.geospatial import create_circle_buffer
from src.utils.browser import open_html_in_browser
from pathlib import Path
import tempfile
import shutil

st.title("🌱 Biochar Suitability Mapping Tool")
st.write("Analyze soil suitability for biochar production interactively.")

# Input section
lat = st.number_input("Latitude", value=-13.0)
lon = st.number_input("Longitude", value=-56.0)
radius = st.slider("Radius (km)", 10, 300, 100)
resolution = st.number_input("H3 Resolution", value=7)
run_button = st.button("Run Analysis")

if run_button:
    with st.spinner("Running analysis..."):
        config, project_root, raw_dir, processed_dir = initialize_project("configs/configs.yaml")
        output_dir = project_root / config.get("output", {}).get("html", "output/html")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        circle = create_circle_buffer(lat, lon, radius)
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_clip_"))
        clip_all_rasters_to_circle(raw_dir, tif_dir, circle)

        csv_files = convert_all_rasters_to_csv(
            input_dir=tif_dir,
            output_dir=processed_dir,
            band=1,
            nodata_handling="skip"
        )
        shutil.rmtree(tif_dir, ignore_errors=True)
        
        scored_df = process_csv_files_with_suitability_scores(
            csv_dir=processed_dir,
            thresholds_path=config.get("thresholds", {}).get("path"),
            output_csv=processed_dir / "suitability_scores.csv",
            property_weights=None,
            pattern="*.csv",
            lon_column="lon",
            lat_column="lat"
        )

        process_all_csv_files_with_h3(
            csv_dir=processed_dir,
            resolution=resolution,
            pattern="*.csv",
            lat_column="lat",
            lon_column="lon"
        )

        output_path = output_dir / "suitability_map.html"
        create_suitability_map(
            df=scored_df,
            output_path=output_path,
            max_file_size_mb=100.0,
            use_h3=True,
            center_lat=lat,
            center_lon=lon,
            zoom_start=8
        )

        st.success("✅ Map generated successfully!")
        st.components.v1.html(Path(output_path).read_text(), height=700)
