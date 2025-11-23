"""
Residual_Carbon - Main Entry Point
Biochar Suitability Mapping Tool

This module serves as the main entry point for the biochar suitability mapping pipeline.
It orchestrates the complete workflow from raw GeoTIFF data to interactive map generation.

The pipeline processes manually provided GeoTIFF data files from the data/raw/ directory.
Data acquisition is done manually outside the codebase.

Workflow:
1. Validates and filters GeoTIFF files
2. Clips rasters to area of interest (if specified)
3. Converts rasters to DataFrames
4. Adds H3 hexagonal indexes for spatial aggregation
5. Merges and aggregates soil property data
6. Calculates biochar suitability scores
7. Generates interactive HTML maps (suitability, SOC, pH, moisture, investor crop area)
"""
import argparse
import sys
from pathlib import Path
from typing import List
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.initialization import initialize_project
from src.data_processors.user_input import get_user_area_of_interest
from src.data_processors.raster_clip import clip_all_rasters_to_circle
from src.utils.geospatial import create_circle_buffer
from src.data_processors.raster_to_csv import convert_all_rasters_to_dataframes
from src.data_processors.h3_converter import process_dataframes_with_h3
from src.analyzers.suitability import merge_and_aggregate_soil_data
from src.map_generators.biochar_map import create_biochar_suitability_map
from src.map_generators.soc_map import create_soc_map
from src.map_generators.ph_map import create_ph_map
from src.map_generators.moisture_map import create_moisture_map
from src.analyzers.biochar_suitability import calculate_biochar_suitability_scores
from src.utils.browser import open_html_in_browser
from src.map_generators.pydeck_maps.municipality_waste_map import (
    build_investor_waste_deck_html,
)

# Future feature: Biochar recommender integration
# When ready, uncomment the following line to enable biochar recommendations:
# from src.analyzers.biochar_recommender import recommend_biochar

def ensure_rasters_acquired(raw_dir: Path) -> List[Path]:
    """
    Validate that required GeoTIFF files are present in data/raw/ directory.
    
    Filters to only scoring-required datasets and preferred resolutions.
    Excludes lower resolution files when higher resolution versions are available.
    
    Parameters
    ----------
    raw_dir : Path
        Directory containing raw GeoTIFF files
        
    Returns
    -------
    List[Path]
        List of validated GeoTIFF file paths
        
    Raises
    ------
    FileNotFoundError
        If no GeoTIFF files are found or no valid scoring datasets are present
    """
    all_tif_files = sorted(raw_dir.glob("*.tif"))
    all_tif_files.extend(sorted(raw_dir.glob("*.tiff")))
    if not all_tif_files:
        raise FileNotFoundError(f"No GeoTIFF files found in '{raw_dir}'.")
    # Filter scoring datasets (no GEE dependency - just file name matching)
    tif_files = []
    excluded_files = []
    res_250_files = {f.name for f in all_tif_files if 'res_250' in f.name}

    for tif in all_tif_files:
        tif_name_lower = tif.name.lower()
        is_scoring_dataset = any(
            ds in tif_name_lower
            for ds in ['moisture', 'soc', 'soil_organic', 'ph', 'temp', 'temperature']
        )
        if not is_scoring_dataset:
            excluded_files.append(tif)
            continue
        if 'res_3000' in tif.name:
            potential_250m = tif.name.replace('res_3000', 'res_250')
            if potential_250m in res_250_files:
                excluded_files.append(tif)
                continue
        if any(d in tif.name for d in ['_b30', '_b60']):
            excluded_files.append(tif)
            continue
        tif_files.append(tif)

    if not tif_files:
        raise FileNotFoundError("No valid scoring GeoTIFFs found.")
    print(f"Found {len(tif_files)} scoring GeoTIFF file(s):")
    for t in tif_files: print(f" - {t.name}")
    return tif_files


def main() -> int:
    """
    Main entry point for the biochar suitability mapping pipeline.
    
    Processes GeoTIFF files, calculates suitability scores, and generates
    interactive maps. Supports both full-state analysis and targeted circular
    area of interest analysis.
    
    Command-line Arguments
    ----------------------
    --lat : float, optional
        Latitude for area of interest (default: None, uses full state)
    --lon : float, optional
        Longitude for area of interest (default: None, uses full state)
    --radius : float, optional
        Radius in kilometers for circular analysis (default: 100)
    --h3-resolution : int, optional
        H3 resolution for spatial aggregation (default: 7)
    --config : str, optional
        Path to configuration file (default: "configs/config.yaml")
    
    Returns
    -------
    int
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Biochar Suitability Mapping Tool")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--radius", type=float, default=100)
    parser.add_argument("--h3-resolution", type=int, default=7)
    parser.add_argument("--config", type=str, default="configs/config.yaml")
    args = parser.parse_args()

    config, project_root, raw_dir, processed_dir = initialize_project(args.config)
    processing_config = config.get("processing", {})
    persist_snapshots = processing_config.get("persist_snapshots", False)
    snapshot_dir = processed_dir / "snapshots" if persist_snapshots else None
    h3_snapshot_dir = snapshot_dir / "h3" if snapshot_dir else None
    output_dir = project_root / config.get("output", {}).get("html", "output/html")
    output_dir.mkdir(parents=True, exist_ok=True)

    filtered_tif_files = ensure_rasters_acquired(raw_dir)
    area = get_user_area_of_interest(lat=args.lat, lon=args.lon, radius_km=args.radius, interactive=False)

    # Process data: clip rasters, convert to DataFrames, add H3 indexes, merge and aggregate
    if area.use_full_state:
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_filtered_"))
        for tif_file in filtered_tif_files:
            shutil.copy2(tif_file, tif_dir / tif_file.name)
        print("Using full Mato Grosso state data")
        h3_resolution = 5
    else:
        print(f"Clipping to {area.radius_km}km radius around ({area.lat}, {area.lon})")
        circle = create_circle_buffer(area.lat, area.lon, area.radius_km)
        tif_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_clip_"))
        from src.utils.cache import get_cache_dir, cleanup_old_coordinate_caches
        cache_dir = get_cache_dir(processed_dir, cache_type="clipped_rasters")
        cleanup_old_coordinate_caches(cache_dir, area.lat, area.lon, area.radius_km, list(raw_dir.glob("*.tif")))
        filtered_input_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_filtered_"))
        for tif_file in filtered_tif_files:
            shutil.copy2(tif_file, filtered_input_dir / tif_file.name)
        _, cache_used = clip_all_rasters_to_circle(
            input_dir=filtered_input_dir, output_dir=tif_dir, circle_geometry=circle,
            use_cache=True, cache_dir=cache_dir, lat=area.lat, lon=area.lon, radius_km=area.radius_km
        )
        shutil.rmtree(filtered_input_dir, ignore_errors=True)
        if cache_used: print(" Using cached clipped rasters")
        h3_resolution = args.h3_resolution

    print("Converting GeoTIFFs to DataFrames...")
    tables = convert_all_rasters_to_dataframes(input_dir=tif_dir, band=1, nodata_handling="skip",
                                               persist_dir=snapshot_dir, use_cache=True, processed_dir=processed_dir)
    if not tables:
        print("No raster tables generated.")
        return 1
    if tif_dir != raw_dir and tif_dir.exists():
        shutil.rmtree(tif_dir, ignore_errors=True)

    print(f"Adding H3 indexes (resolution {h3_resolution})...")
    tables_with_h3 = process_dataframes_with_h3(tables, h3_resolution, persist_dir=h3_snapshot_dir,
                                                use_cache=True, processed_dir=processed_dir)
    if not tables_with_h3:
        print("Failed to add H3 indexes.")
        return 1

    print("Merging and aggregating soil data...")
    merged_df = merge_and_aggregate_soil_data(
        csv_dir=processed_dir, pattern="*.csv", lon_column="lon", lat_column="lat",
        dataframes=tables_with_h3, output_csv=processed_dir / "merged_soil_data.csv"
    )

    print("\n" + "="*60)
    print("Calculating biochar suitability scores...")
    print("="*60)
    scored_df = calculate_biochar_suitability_scores(merged_df)

    # Biochar recommender integration (future feature)
    # Uncomment and configure when ready to use:
    # from src.analyzers.biochar_recommender import recommend_biochar
    # scored_df = recommend_biochar(scored_df)

    # Save final CSV for Streamlit
    suitability_csv_path = processed_dir / "suitability_scores.csv"
    if 'biochar_suitability_score' in scored_df.columns:
        scored_df = scored_df.assign(suitability_score=scored_df['biochar_suitability_score'] / 10.0)
    scored_df.to_csv(suitability_csv_path, index=False)
    print(f"\nFinal results saved to: {suitability_csv_path}")

    # Prepare map view parameters
    center_lat = area.lat if not area.use_full_state else None
    center_lon = area.lon if not area.use_full_state else None
    zoom = 8 if not area.use_full_state else 6

    biochar_map_path = output_dir / "suitability_map.html"
    try:
        create_biochar_suitability_map(
            df=scored_df, output_path=biochar_map_path, use_h3=True,
            center_lat=center_lat, center_lon=center_lon, zoom_start=zoom
        )
    except Exception as e:
        print(f"Map error: {e}")

    # Create SOC map
    soc_map_path = output_dir / "soc_map.html"
    soc_map_streamlit_path = output_dir / "soc_map_streamlit.html"
    try:
        create_soc_map(
            processed_dir=processed_dir,
            output_path=soc_map_path,
            h3_resolution=h3_resolution,
            use_coords=not area.use_full_state,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom_start=zoom
        )
        # Copy for Streamlit
        shutil.copy2(soc_map_path, soc_map_streamlit_path)
        print(f"SOC map saved to: {soc_map_path}")
    except Exception as e:
        print(f"SOC map error: {e}")

    # Create pH map
    ph_map_path = output_dir / "ph_map.html"
    ph_map_streamlit_path = output_dir / "ph_map_streamlit.html"
    try:
        create_ph_map(
            processed_dir=processed_dir,
            output_path=ph_map_path,
            h3_resolution=h3_resolution,
            use_coords=not area.use_full_state,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom_start=zoom
        )
        # Copy for Streamlit
        shutil.copy2(ph_map_path, ph_map_streamlit_path)
        print(f"pH map saved to: {ph_map_path}")
    except Exception as e:
        print(f"pH map error: {e}")

    # Create moisture map
    moisture_map_path = output_dir / "moisture_map.html"
    moisture_map_streamlit_path = output_dir / "moisture_map_streamlit.html"
    try:
        create_moisture_map(
            processed_dir=processed_dir,
            output_path=moisture_map_path,
            h3_resolution=h3_resolution,
            use_coords=not area.use_full_state,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom_start=zoom
        )
        # Copy for Streamlit
        shutil.copy2(moisture_map_path, moisture_map_streamlit_path)
        print(f"Moisture map saved to: {moisture_map_path}")
    except Exception as e:
        print(f"Moisture map error: {e}")

    # Investor crop area map (municipality-level)
    investor_map_path = output_dir / "investor_crop_area_map.html"
    boundaries_dir = project_root / "data" / "boundaries" / "BR_Municipios_2024"
    waste_csv_path = project_root / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv"
    if boundaries_dir.exists() and waste_csv_path.exists():
        try:
            _, merged_gdf = build_investor_waste_deck_html(
                boundaries_dir, waste_csv_path, investor_map_path, simplify_tolerance=0.01
            )
            print(f"Investor crop area map saved to: {investor_map_path}")
        except Exception as exc:
            print(f"Could not create investor waste map: {exc}")
    else:
        print("Skipping investor crop area map (boundary or crop data missing).")

    print(f"\nAll done! Results in: {processed_dir}")
    print(f"Maps in: {output_dir}")

    if config.get("visualization", {}).get("auto_open_html", True):
        print("Opening maps in browser...")
        open_html_in_browser(biochar_map_path)
        for extra_map in [
            output_dir / "soc_map_streamlit.html",
            output_dir / "ph_map_streamlit.html",
            output_dir / "moisture_map_streamlit.html",
            investor_map_path,
        ]:
            if extra_map.exists():
                open_html_in_browser(extra_map)

    return 0


if __name__ == "__main__":
    sys.exit(main())
