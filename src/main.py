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
from typing import List
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.initialization import initialize_project
from src.data.processing.user_input import get_user_area_of_interest
from src.data.processing.raster_clip import clip_all_rasters_to_circle
from src.utils.geospatial import create_circle_buffer
from src.data.processing.raster_to_csv import convert_all_rasters_to_dataframes
from src.data.processing.h3_converter import process_dataframes_with_h3
from src.analysis.suitability import process_csv_files_with_suitability_scores
from src.visualization.map_generator import create_suitability_map
from src.utils.browser import open_html_in_browser


def ensure_rasters_acquired(raw_dir: Path) -> List[Path]:
    """
    Ensure GeoTIFF rasters are available from the acquisition step.

    Parameters
    ----------
    raw_dir : Path
        Directory expected to contain acquired GeoTIFF files.

    Returns
    -------
    List[Path]
        List of GeoTIFF files discovered in the raw directory.

    Raises
    ------
    FileNotFoundError
        If no GeoTIFF files are present.
    """
    tif_files = sorted(raw_dir.glob("*.tif"))
    tif_files.extend(sorted(raw_dir.glob("*.tiff")))

    if not tif_files:
        raise FileNotFoundError(
            f"No GeoTIFF files found in '{raw_dir}'. "
            "Run the acquisition step (data_loader.py) before processing."
        )

    print(f"Found {len(tif_files)} GeoTIFF file(s) from acquisition:")
    for tif in tif_files:
        print(f"  - {tif.name}")

    return tif_files


def main():
    """Simple, streamlined workflow."""
    parser = argparse.ArgumentParser(description="Biochar Suitability Mapping Tool")
    parser.add_argument("--lat", type=float, default=None, help="Latitude (optional)")
    parser.add_argument("--lon", type=float, default=None, help="Longitude (optional)")
    parser.add_argument("--radius", type=float, default=100, help="Radius in km (default: 100)")
    parser.add_argument("--h3-resolution", type=int, default=7, help="H3 resolution for clipped areas (default: 7). Full state uses resolution 9 automatically.")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Config file")
    
    args = parser.parse_args()
    
    # Initialize
    config, project_root, raw_dir, processed_dir = initialize_project(args.config)
    processing_config = config.get("processing", {})
    persist_snapshots = processing_config.get("persist_snapshots", False)
    snapshot_dir = processed_dir / "snapshots" if persist_snapshots else None
    h3_snapshot_dir = snapshot_dir / "h3" if snapshot_dir else None
    output_dir = project_root / config.get("output", {}).get("html", "output/html")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure acquisition step completed before prompting for coordinates
    ensure_rasters_acquired(raw_dir)

    # Get area of interest (optional coordinates)
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
        # Use coarser H3 resolution (9) for full state
        h3_resolution = 9
        print("Using H3 resolution 9 for full state (coarser resolution)")
    else:
        # Clip to 100km radius with caching
        print(f"Clipping to {area.radius_km}km radius around ({area.lat}, {area.lon})")
        circle = create_circle_buffer(area.lat, area.lon, area.radius_km)
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_clip_"))
        
        # Use cache for clipped rasters (enabled by default)
        # Pass processed_dir to get correct cache directory
        from src.utils.cache import get_cache_dir
        cache_dir = get_cache_dir(processed_dir, cache_type="clipped_rasters")
        
        clipped_files, cache_used = clip_all_rasters_to_circle(
            input_dir=raw_dir,
            output_dir=tif_dir,
            circle_geometry=circle,
            use_cache=True,
            cache_dir=cache_dir,
            lat=area.lat,
            lon=area.lon,
            radius_km=area.radius_km
        )
        
        if cache_used:
            print("  Using cached clipped rasters - skipping clipping step")
        
        # Use specified/default H3 resolution for clipped area
        h3_resolution = args.h3_resolution
    
    # Step 2: Convert GeoTIFFs to DataFrames (lon/lat/value tables) with caching
    print("Converting GeoTIFFs to DataFrames...")
    tables = convert_all_rasters_to_dataframes(
        input_dir=tif_dir,
        band=1,
        nodata_handling="skip",
        persist_dir=snapshot_dir,
        use_cache=True,
        processed_dir=processed_dir
    )

    if not tables:
        print("No raster tables were generated. Exiting.")
        return 1

    # Clean up temp directory
    if tif_dir != raw_dir and tif_dir.exists():
        shutil.rmtree(tif_dir, ignore_errors=True)

    # Step 3: Add H3 indexes before scoring (boundaries added after merge)
    print(f"Adding H3 indexes (resolution {h3_resolution})...")
    tables_with_h3 = process_dataframes_with_h3(
        tables=tables,
        resolution=h3_resolution,
        lat_column="lat",
        lon_column="lon",
        persist_dir=h3_snapshot_dir
    )

    if not tables_with_h3:
        print("Failed to add H3 indexes to any tables. Exiting.")
        return 1

    # Step 4: Calculate suitability scores (aggregates by H3 if available)
    print("Calculating suitability scores...")
    scored_df = process_csv_files_with_suitability_scores(
        csv_dir=processed_dir,
        thresholds_path=config.get("thresholds", {}).get("path"),
        output_csv=processed_dir / "suitability_scores.csv",
        property_weights=None,
        pattern="*.csv",
        lon_column="lon",
        lat_column="lat",
        dataframes=tables_with_h3
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
