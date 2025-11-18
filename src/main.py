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
from src.analysis.suitability import merge_and_aggregate_soil_data
from src.visualization.biochar_map import create_biochar_suitability_map
from src.analysis.biochar_suitability import calculate_biochar_suitability_scores
from src.utils.browser import open_html_in_browser


def ensure_rasters_acquired(raw_dir: Path) -> List[Path]:
    """
    Ensure GeoTIFF rasters are available from the acquisition step.
    Filters out old 3000m resolution files when 250m versions exist.

    Parameters
    ----------
    raw_dir : Path
        Directory expected to contain acquired GeoTIFF files.

    Returns
    -------
    List[Path]
        List of GeoTIFF files discovered in the raw directory (preferring 250m over 3000m).

    Raises
    ------
    FileNotFoundError
        If no GeoTIFF files are present.
    """
    all_tif_files = sorted(raw_dir.glob("*.tif"))
    all_tif_files.extend(sorted(raw_dir.glob("*.tiff")))

    if not all_tif_files:
        raise FileNotFoundError(
            f"No GeoTIFF files found in '{raw_dir}'. "
            "Run the acquisition step (data_loader.py) before processing."
        )

    # Filter: Prefer 250m over 3000m resolution files
    # Group files by dataset type (soil_moisture, soil_temp, etc.)
    tif_files = []
    excluded_files = []
    
    # Find all 250m files
    res_250_files = {f.name for f in all_tif_files if 'res_250' in f.name}
    
    for tif in all_tif_files:
        # If it's a 3000m file, check if a 250m version exists
        if 'res_3000' in tif.name:
            # Check if corresponding 250m file exists
            # Replace res_3000 with res_250 in filename
            potential_250m_name = tif.name.replace('res_3000', 'res_250')
            if potential_250m_name in res_250_files:
                excluded_files.append(tif)
                continue  # Skip this 3000m file, use 250m version instead
        tif_files.append(tif)
    
    if not tif_files:
        raise FileNotFoundError(
            f"No valid GeoTIFF files found in '{raw_dir}'. "
            "Run the acquisition step (data_loader.py) before processing."
        )

    print(f"Found {len(tif_files)} GeoTIFF file(s) from acquisition:")
    for tif in tif_files:
        print(f"  - {tif.name}")
    
    if excluded_files:
        print(f"\nExcluded {len(excluded_files)} old 3000m resolution file(s) (250m versions available):")
        for tif in excluded_files:
            print(f"  - {tif.name} (replaced by 250m version)")

    return tif_files


def main():
    """Simple, streamlined workflow."""
    parser = argparse.ArgumentParser(description="Biochar Suitability Mapping Tool")
    parser.add_argument("--lat", type=float, default=None, help="Latitude (optional)")
    parser.add_argument("--lon", type=float, default=None, help="Longitude (optional)")
    parser.add_argument("--radius", type=float, default=100, help="Radius in km (default: 100)")
    parser.add_argument("--h3-resolution", type=int, default=7, help="H3 resolution for clipped areas (default: 7). Full state uses resolution 5 automatically.")
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
        # Use coarser H3 resolution (5) for full state
        h3_resolution = 5
        print("Using H3 resolution 5 for full state (coarser resolution)")
    else:
        # Clip to 100km radius with caching
        print(f"Clipping to {area.radius_km}km radius around ({area.lat}, {area.lon})")
        circle = create_circle_buffer(area.lat, area.lon, area.radius_km)
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_clip_"))
        
        # Use cache for clipped rasters (enabled by default)
        # Pass processed_dir to get correct cache directory
        from src.utils.cache import get_cache_dir, cleanup_old_coordinate_caches
        
        cache_dir = get_cache_dir(processed_dir, cache_type="clipped_rasters")
        
        # Collect source files for cache cleanup
        raw_files = list(Path(raw_dir).glob("*.tif")) if Path(raw_dir).exists() else []
        
        # Clean up old coordinate-specific caches (preserves full state and protected coordinates)
        removed_count = cleanup_old_coordinate_caches(
            cache_dir=cache_dir,
            current_lat=area.lat,
            current_lon=area.lon,
            current_radius_km=area.radius_km,
            source_files=raw_files
        )
        if removed_count > 0:
            print(f"\nCleaned up {removed_count} old coordinate-specific cache(s)")
            print(f"  Preserved: Full state cache and protected coordinates (-13, -56, 100km)")
        
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
        persist_dir=h3_snapshot_dir,
        use_cache=True,
        processed_dir=processed_dir
    )

    if not tables_with_h3:
        print("Failed to add H3 indexes to any tables. Exiting.")
        return 1

    # Step 4: Merge and aggregate soil data (aggregates by H3 if available)
    print("Merging and aggregating soil data...")
    merged_df = merge_and_aggregate_soil_data(
        csv_dir=processed_dir,
        pattern="*.csv",
        lon_column="lon",
        lat_column="lat",
        dataframes=tables_with_h3,
        output_csv=processed_dir / "merged_soil_data.csv"
    )
    
    # Step 5: Calculate biochar suitability scores with new grading system
    print("\n" + "="*60)
    print("Calculating biochar suitability scores with new grading system...")
    print("="*60)
    
    scored_df = calculate_biochar_suitability_scores(merged_df)
    
    # Save suitability scores CSV for Streamlit (with compatibility column name and scale)
    suitability_csv_path = processed_dir / "suitability_scores.csv"
    # Create a copy with 'suitability_score' column for Streamlit compatibility
    # Scale from 0-100 to 0-10 for Streamlit display
    scored_df_for_csv = scored_df.copy()
    if 'biochar_suitability_score' in scored_df_for_csv.columns:
        # Scale from 0-100 to 0-10 for Streamlit (which expects 0-10 scale)
        scored_df_for_csv['suitability_score'] = scored_df_for_csv['biochar_suitability_score'] / 10.0
    scored_df_for_csv.to_csv(suitability_csv_path, index=False)
    print(f"\nSuitability scores saved to: {suitability_csv_path}")
    
    # Step 6: Output biochar suitability map
    print("\nCreating biochar suitability map...")
    
    center_lat = area.lat if not area.use_full_state else None
    center_lon = area.lon if not area.use_full_state else None
    zoom = 8 if not area.use_full_state else 6
    
    # Create biochar suitability map with new color scheme
    biochar_map_path = output_dir / "biochar_suitability_map.html"
    suitability_map_path = output_dir / "suitability_map.html"  # For Streamlit compatibility
    
    create_biochar_suitability_map(
        df=scored_df,
        output_path=biochar_map_path,
        max_file_size_mb=100.0,
        use_h3=True,
        center_lat=center_lat,
        center_lon=center_lon,
        zoom_start=zoom
    )
    
    # Also save a copy with the name Streamlit expects
    shutil.copy2(biochar_map_path, suitability_map_path)
    
    print(f"\nBiochar suitability map saved to: {biochar_map_path}")
    print(f"Suitability map (Streamlit) saved to: {suitability_map_path}")
    
    # Auto-open biochar map if enabled
    if config.get("visualization", {}).get("auto_open_html", True):
        open_html_in_browser(biochar_map_path)
    
    print(f"\nAll maps saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
