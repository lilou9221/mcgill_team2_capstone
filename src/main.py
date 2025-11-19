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
    Filters to only scoring-required datasets and prefers 250m over 3000m resolution files.
    
    Note: All files are exported to Google Drive, but only scoring-required datasets
    (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature) are imported for processing.

    Parameters
    ----------
    raw_dir : Path
        Directory expected to contain acquired GeoTIFF files.

    Returns
    -------
    List[Path]
        List of GeoTIFF files discovered in the raw directory (only scoring-required datasets).

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

    # Filter to only scoring-required datasets (not used: land_cover, soil_type)
    from src.data.acquisition.gee_loader import get_scoring_required_datasets
    scoring_datasets = get_scoring_required_datasets()
    
    # Filter: Prefer 250m over 3000m resolution files
    # For SOC and pH: include both b0 and b10 layers (used in scoring)
    tif_files = []
    excluded_files = []
    
    # Find all 250m files
    res_250_files = {f.name for f in all_tif_files if 'res_250' in f.name}
    
    # Find all b0 files for datasets with multiple depth layers
    b0_files = {f.name for f in all_tif_files if '_b0' in f.name}
    
    for tif in all_tif_files:
        # First, filter out datasets not used in scoring (land_cover, soil_type)
        tif_name_lower = tif.name.lower()
        is_scoring_dataset = False
        for dataset in scoring_datasets:
            # Check if this file belongs to a scoring-required dataset
            if dataset == 'soil_moisture' and 'moisture' in tif_name_lower and 'sm_surface' in tif_name_lower:
                is_scoring_dataset = True
                break
            elif dataset == 'soil_organic_carbon' and ('soc' in tif_name_lower or 'soil_organic' in tif_name_lower):
                is_scoring_dataset = True
                break
            elif dataset == 'soil_pH' and ('ph' in tif_name_lower or 'soil_ph' in tif_name_lower):
                is_scoring_dataset = True
                break
            elif dataset == 'soil_temperature' and ('temp' in tif_name_lower or 'temperature' in tif_name_lower):
                is_scoring_dataset = True
                break
        
        # Skip files not used in scoring
        if not is_scoring_dataset:
            excluded_files.append(tif)
            continue
        
        # If it's a 3000m file, check if a 250m version exists
        if 'res_3000' in tif.name:
            # Check if corresponding 250m file exists
            # Replace res_3000 with res_250 in filename
            potential_250m_name = tif.name.replace('res_3000', 'res_250')
            if potential_250m_name in res_250_files:
                excluded_files.append(tif)
                continue  # Skip this 3000m file, use 250m version instead
        
        # For SOC and pH: include b0 and b10 (both used in scoring)
        # Check if this is a deeper layer file (b10, b30, b60)
        if any(depth in tif.name for depth in ['_b10', '_b30', '_b60']):
            # Check if this is SOC or pH - include b10, exclude b30 and b60
            if any(dataset in tif.name.lower() for dataset in ['soc', 'ph']):
                # Include b10 for SOC and pH
                if '_b10' in tif.name:
                    tif_files.append(tif)
                    continue
                # Exclude b30 and b60 for SOC and pH (only use b0 and b10)
                elif any(depth in tif.name for depth in ['_b30', '_b60']):
                    excluded_files.append(tif)
                    continue
        
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
        excluded_non_scoring = [t for t in excluded_files if not any(d in t.name.lower() for d in ['soc', 'ph', 'moisture', 'temp', 'temperature'])]
        excluded_3000m = [t for t in excluded_files if 'res_3000' in t.name and t not in excluded_non_scoring]
        excluded_deeper = [t for t in excluded_files if any(d in t.name for d in ['_b30', '_b60']) and t not in excluded_non_scoring]
        
        if excluded_non_scoring:
            print(f"\nExcluded {len(excluded_non_scoring)} dataset(s) not used in scoring (available in Google Drive but not imported for processing):")
            for tif in excluded_non_scoring:
                print(f"  - {tif.name} (not used in biochar suitability scoring)")
        
        if excluded_3000m:
            print(f"\nExcluded {len(excluded_3000m)} old 3000m resolution file(s) (250m versions available):")
            for tif in excluded_3000m:
                print(f"  - {tif.name} (replaced by 250m version)")
        
        if excluded_deeper:
            print(f"\nExcluded {len(excluded_deeper)} deeper layer file(s):")
            for tif in excluded_deeper:
                if any(d in tif.name for d in ['_b30', '_b60']):
                    if any(d in tif.name.lower() for d in ['soc', 'ph']):
                        print(f"  - {tif.name} (using b0 and b10 layers instead)")

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
    
    # Ensure acquisition step completed and get filtered file list (only scoring-required)
    filtered_tif_files = ensure_rasters_acquired(raw_dir)

    # Get area of interest (optional coordinates)
    # Use non-interactive mode when running from command line (even if no coordinates provided)
    # This will default to full state analysis
    area = get_user_area_of_interest(
        lat=args.lat,
        lon=args.lon,
        radius_km=args.radius,
        interactive=False  # Always non-interactive when running from command line
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
        
        # Clean up old coordinate-specific caches (enabled by default)
        # Preserves: full state cache, protected coordinates (-13, -56, 100km), and current coordinates
        cleanup_enabled = config.get("processing", {}).get("cleanup_old_cache", True)
        if cleanup_enabled:
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
        
        # Create a temporary directory with only scoring-required files for clipping
        # This ensures only the filtered files are processed
        filtered_input_dir = Path(tempfile.mkdtemp(prefix="residual_carbon_filtered_"))
        for tif_file in filtered_tif_files:
            shutil.copy2(tif_file, filtered_input_dir / tif_file.name)
        
        _, cache_used = clip_all_rasters_to_circle(
            input_dir=filtered_input_dir,
            output_dir=tif_dir,
            circle_geometry=circle,
            use_cache=True,
            cache_dir=cache_dir,
            lat=area.lat,
            lon=area.lon,
            radius_km=area.radius_km
        )
        
        # Clean up temporary filtered directory
        shutil.rmtree(filtered_input_dir, ignore_errors=True)
        
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
    # Add 'suitability_score' column for Streamlit compatibility
    # Scale from 0-100 to 0-10 for Streamlit display
    # Use assign() to avoid full copy - only creates new column
    if 'biochar_suitability_score' in scored_df.columns:
        scored_df_for_csv = scored_df.assign(
            suitability_score=scored_df['biochar_suitability_score'] / 10.0
        )
    else:
        scored_df_for_csv = scored_df
    scored_df_for_csv.to_csv(suitability_csv_path, index=False)
    del scored_df_for_csv  # Free memory immediately after saving
    print(f"\nSuitability scores saved to: {suitability_csv_path}")
    
    # Save GeoJSON file with hexagon geometry for efficient map rendering
    geojson_path = processed_dir / "hexagons_with_scores.geojson"
    try:
        import geopandas as gpd
        from shapely.geometry import Polygon
        import h3
        
        # Check if we have h3_boundary_geojson column (from aggregation)
        if 'h3_boundary_geojson' in scored_df.columns:
            # Convert h3_boundary_geojson to Shapely Polygon
            def boundary_to_polygon(boundary_list):
                """Convert h3_boundary_geojson list to Shapely Polygon."""
                if boundary_list is None or not isinstance(boundary_list, list):
                    return None
                try:
                    # boundary_list is [[lon, lat], [lon, lat], ...]
                    coords = list(boundary_list)
                    if len(coords) < 3:
                        return None
                    # Close the polygon
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    return Polygon(coords)
                except:
                    return None
            
            scored_df_geom = scored_df.copy()
            scored_df_geom['geometry'] = scored_df_geom['h3_boundary_geojson'].apply(boundary_to_polygon)
            scored_df_geom = scored_df_geom[scored_df_geom['geometry'].notna()].copy()
            
        elif 'h3_index' in scored_df.columns:
            # Reconstruct geometry from h3_index
            def h3_to_polygon(h3_index):
                """Convert H3 index to Shapely Polygon."""
                import pandas as pd
                if pd.isna(h3_index):
                    return None
                try:
                    boundary = h3.cell_to_boundary(str(h3_index))
                    # h3 returns (lat, lon), but Shapely needs (lon, lat)
                    coords = [(lon, lat) for lat, lon in boundary]
                    coords.append(coords[0])  # Close polygon
                    return Polygon(coords)
                except:
                    return None
            
            scored_df_geom = scored_df.copy()
            scored_df_geom['geometry'] = scored_df_geom['h3_index'].apply(h3_to_polygon)
            scored_df_geom = scored_df_geom[scored_df_geom['geometry'].notna()].copy()
        else:
            print("Warning: No geometry information found. Skipping GeoJSON export.")
            scored_df_geom = None
        
        if scored_df_geom is not None and len(scored_df_geom) > 0:
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(scored_df_geom, geometry='geometry', crs='EPSG:4326')
            
            # Drop h3_boundary_geojson column if it exists (not needed in GeoJSON)
            if 'h3_boundary_geojson' in gdf.columns:
                gdf = gdf.drop(columns=['h3_boundary_geojson'])
            
            # Ensure essential columns are present and have correct data types
            # Convert numeric columns to appropriate types to reduce file size
            numeric_cols = ['ph', 'soil_moisture', 'soc', 'suitability_score', 'biochar_suitability_score']
            for col in numeric_cols:
                if col in gdf.columns:
                    # Convert to float32 to save memory (if not already numeric)
                    if gdf[col].dtype == 'object':
                        gdf[col] = pd.to_numeric(gdf[col], errors='coerce')
                    elif gdf[col].dtype == 'float64':
                        gdf[col] = gdf[col].astype('float32')
            
            # Ensure h3_index is string type
            if 'h3_index' in gdf.columns:
                gdf['h3_index'] = gdf['h3_index'].astype(str)
            
            # Validate geometries before saving
            invalid_count = gdf['geometry'].isna().sum()
            if invalid_count > 0:
                print(f"Warning: {invalid_count} rows with invalid geometry. Filtering them out.")
                gdf = gdf[gdf['geometry'].notna()].copy()
            
            # Save as GeoJSON with proper encoding
            try:
                gdf.to_file(geojson_path, driver='GeoJSON')
                file_size_mb = geojson_path.stat().st_size / (1024 * 1024)
                print(f"GeoJSON file saved to: {geojson_path}")
                print(f"  Features: {len(gdf):,} hexagons")
                print(f"  File size: {file_size_mb:.2f} MB")
                print(f"  Columns: {', '.join([c for c in gdf.columns if c != 'geometry'])}")
            except Exception as e:
                print(f"Error saving GeoJSON: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Warning: Could not create GeoJSON - no valid geometry found.")
    except ImportError:
        print("Warning: geopandas not available. Skipping GeoJSON export.")
    except Exception as e:
        print(f"Warning: Could not save GeoJSON file: {e}")
    
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
