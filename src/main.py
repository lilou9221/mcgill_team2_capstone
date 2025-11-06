"""
Residual_Carbon - Main Entry Point
Biochar Suitability Mapping Tool

Simple workflow:
1. Load .tif files -> get coordinates and values
2. If coordinates provided -> clip to 100km radius
3. Score each value based on thresholds
4. Get H3 index for each point
5. Aggregate within hexagons -> final score per hexagon
6. Output HTML map (PyDeck format)
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.initialization import initialize_project
from src.data.processing.user_input import get_user_area_of_interest
from src.data.processing.raster_clip import clip_all_rasters_to_circle
from src.utils.geospatial import create_circle_buffer
from src.data.processing.raster_to_csv import convert_all_rasters_to_csv
from src.data.processing.h3_converter import process_all_csv_files_with_h3
from src.analysis.suitability import process_csv_files_with_suitability_scores
from src.visualization.map_generator import create_suitability_map
from src.utils.browser import open_html_in_browser


def main():
    """Simple, streamlined workflow."""
    parser = argparse.ArgumentParser(description="Biochar Suitability Mapping Tool")
    parser.add_argument("--lat", type=float, default=None, help="Latitude (optional)")
    parser.add_argument("--lon", type=float, default=None, help="Longitude (optional)")
    parser.add_argument("--radius", type=float, default=100, help="Radius in km (default: 100)")
    parser.add_argument("--h3-resolution", type=int, default=7, help="H3 resolution (default: 7)")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Config file")
    
    args = parser.parse_args()
    
    # Initialize
    config, project_root, raw_dir, processed_dir = initialize_project(args.config)
    output_dir = project_root / config.get("output", {}).get("html", "output/html")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get area of interest
    area = get_user_area_of_interest(
        lat=args.lat,
        lon=args.lon,
        radius_km=args.radius,
        interactive=(args.lat is None and args.lon is None)
    )
    
    # Step 1: Clip GeoTIFFs to circle (if coordinates provided)
    if area.use_full_state:
        # Use full state - no clipping needed
        tif_dir = raw_dir
        print("Using full Mato Grosso state data")
    else:
        # Clip to 100km radius
        print(f"Clipping to {area.radius_km}km radius around ({area.lat}, {area.lon})")
        circle = create_circle_buffer(area.lat, area.lon, area.radius_km)
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_clip_"))
        clip_all_rasters_to_circle(raw_dir, tif_dir, circle)
    
    # Step 2: Convert GeoTIFFs to CSV (get coordinates and values for each point)
    print("Converting GeoTIFFs to CSV...")
    csv_files = convert_all_rasters_to_csv(
        input_dir=tif_dir,
        output_dir=processed_dir,
        band=1,
        nodata_handling="skip"
    )
    
    # Clean up temp directory
    if tif_dir != raw_dir and tif_dir.exists():
        shutil.rmtree(tif_dir, ignore_errors=True)
    
    # Step 3: Score each value based on thresholds
    print("Calculating suitability scores...")
    scored_df = process_csv_files_with_suitability_scores(
        csv_dir=processed_dir,
        thresholds_path=config.get("thresholds", {}).get("path"),
        output_csv=processed_dir / "suitability_scores.csv",
        property_weights=None,
        pattern="*.csv",
        lon_column="lon",
        lat_column="lat"
    )
    
    # Step 4: Get H3 index for each point and aggregate within hexagons
    print(f"Adding H3 indexes (resolution {args.h3_resolution})...")
    process_all_csv_files_with_h3(
        csv_dir=processed_dir,
        resolution=args.h3_resolution,
        pattern="*.csv",
        lat_column="lat",
        lon_column="lon"
    )
    
    # Recalculate scores with H3 aggregation (aggregate points within hexagons)
    print("Aggregating scores by hexagon...")
    scored_df = process_csv_files_with_suitability_scores(
        csv_dir=processed_dir,
        thresholds_path=config.get("thresholds", {}).get("path"),
        output_csv=processed_dir / "suitability_scores.csv",
        property_weights=None,
        pattern="*.csv",
        lon_column="lon",
        lat_column="lat"
    )
    
    # Step 5: Output HTML map (PyDeck format)
    print("Creating map...")
    output_path = output_dir / "suitability_map.html"
    
    center_lat = area.lat if not area.use_full_state else None
    center_lon = area.lon if not area.use_full_state else None
    zoom = 8 if not area.use_full_state else 6
    
    create_suitability_map(
        df=scored_df,
        output_path=output_path,
        max_file_size_mb=100.0,
        use_h3=True,
        center_lat=center_lat,
        center_lon=center_lon,
        zoom_start=zoom
    )
    
    # Auto-open in browser
    if config.get("visualization", {}).get("auto_open_html", True):
        open_html_in_browser(output_path)
    
    print(f"\nMap saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
