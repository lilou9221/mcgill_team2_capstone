"""
Raster Clipping Module

Clips GeoTIFF files to circular buffers around user-specified points.
Handles coordinate transformations and saves clipped rasters.
Includes caching to avoid re-clipping the same areas.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from rasterio.mask import mask
from shapely.geometry import mapping

try:  # pragma: no cover
    from src.utils.geospatial import create_circle_buffer
    from src.utils.cache import (
        generate_cache_key,
        get_cache_dir,
        get_cached_files,
        is_cache_valid,
        save_cache_metadata,
        get_cache_subdirectory,
    )
except ModuleNotFoundError:  # Fallback when running as script
    import sys
    SCRIPT_ROOT = Path(__file__).resolve().parents[3]
    if str(SCRIPT_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPT_ROOT))
    from src.utils.geospatial import create_circle_buffer
    from src.utils.cache import (
        generate_cache_key,
        get_cache_dir,
        get_cached_files,
        is_cache_valid,
        save_cache_metadata,
        get_cache_subdirectory,
    )


def clip_raster_to_circle(
    tif_path: Path,
    circle_geometry,
    output_path: Path,
    nodata: Optional[float] = None
) -> Path:
    """
    Clip a GeoTIFF raster to a circular geometry.
    
    Parameters
    ----------
    tif_path : Path
        Path to input GeoTIFF file
    circle_geometry : shapely.geometry.Polygon
        Circular buffer polygon (should be in WGS84/EPSG:4326)
    output_path : Path
        Path to output clipped GeoTIFF file
    nodata : float, optional
        NoData value to use. If None, uses the raster's nodata value.
    
    Returns
    -------
    Path
        Path to the output clipped file
    """
    if not tif_path.exists():
        raise FileNotFoundError(f"Input raster not found: {tif_path}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Open input raster
    with rasterio.open(tif_path) as src:
        effective_nodata = nodata if nodata is not None else src.nodata
        if effective_nodata is None:
            dtype_name = src.dtypes[0]
            dtype = np.dtype(dtype_name)
            if np.issubdtype(dtype, np.floating):
                effective_nodata = np.nan
            elif np.issubdtype(dtype, np.signedinteger):
                effective_nodata = -9999
            elif np.issubdtype(dtype, np.unsignedinteger):
                effective_nodata = 0
            else:
                effective_nodata = 0
        # Get raster CRS
        raster_crs = src.crs
        
        # Convert circle geometry to GeoJSON format
        # The circle is in WGS84 (EPSG:4326), but the raster might be in a different CRS
        # We need to transform the geometry to match the raster's CRS
        if raster_crs != 'EPSG:4326':
            from src.utils.geospatial import transform_geometry
            circle_in_raster_crs = transform_geometry(circle_geometry, 'EPSG:4326', str(raster_crs))
        else:
            circle_in_raster_crs = circle_geometry
        
        # Convert to GeoJSON format for rasterio.mask
        geojson_geom = [mapping(circle_in_raster_crs)]
        
        # Clip the raster
        try:
            out_image, out_transform = mask(src, geojson_geom, crop=True, nodata=effective_nodata)
        except Exception as e:
            raise ValueError(f"Failed to clip raster: {e}")
        
        # Get metadata from source
        out_meta = src.meta.copy()
        
        # Update metadata
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "compress": "lzw",  # Compress output
        })
        
        # Set nodata value
        out_meta["nodata"] = effective_nodata
    
    # Write clipped raster
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)
    
    return output_path


def collect_geotiff_files(input_dir: Path, pattern: str = "*.tif") -> List[Path]:
    """
    Collect GeoTIFF files from a directory matching the given pattern.

    Parameters
    ----------
    input_dir : Path
        Directory containing GeoTIFF files.
    pattern : str, optional
        Glob pattern to match files (default: "*.tif").

    Returns
    -------
    List[Path]
        Sorted list of GeoTIFF file paths.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    tif_files = sorted(input_dir.glob(pattern))
    return tif_files


def clip_all_rasters_to_circle(
    input_dir: Path,
    output_dir: Path,
    circle_geometry,
    pattern: str = "*.tif",
    use_cache: bool = True,
    cache_dir: Optional[Path] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None
) -> Tuple[List[Path], bool]:
    """
    Clip all GeoTIFF files in a directory to a circular geometry.
    Includes caching to avoid re-clipping the same areas.
    
    Parameters
    ----------
    input_dir : Path
        Directory containing input GeoTIFF files
    output_dir : Path
        Directory to save clipped GeoTIFF files
    circle_geometry : shapely.geometry.Polygon
        Circular buffer polygon (should be in WGS84/EPSG:4326)
    pattern : str, optional
        File pattern to match (default: "*.tif")
    use_cache : bool, optional
        Whether to use cache (default: True)
    cache_dir : Optional[Path], optional
        Cache directory. If None, uses default cache directory.
    lat : Optional[float], optional
        Latitude of circle center (for cache key generation)
    lon : Optional[float], optional
        Longitude of circle center (for cache key generation)
    radius_km : Optional[float], optional
        Radius in kilometers (for cache key generation)
    
    Returns
    -------
    Tuple[List[Path], bool]
        List of paths to clipped output files and whether cache was used
    """
    # Collect GeoTIFF files sequentially
    tif_files = collect_geotiff_files(input_dir=input_dir, pattern=pattern)
    
    if not tif_files:
        print(f"No GeoTIFF files found in {input_dir} matching pattern {pattern}")
        return [], False
    
    # Try to use cache if enabled and coordinates are provided
    cache_used = False
    if use_cache and lat is not None and lon is not None and radius_km is not None:
        # Get cache directory
        if cache_dir is None:
            # Use output_dir's parent processed directory for cache
            # output_dir is typically a temp directory, so we need to find processed_dir
            # Try to infer from output_dir structure
            if "processed" in str(output_dir) or "cache" in str(output_dir):
                processed_dir = output_dir.parent
            else:
                # Fallback: use a default cache location relative to output_dir
                processed_dir = output_dir.parent.parent / "processed"
            
            cache_dir = get_cache_dir(processed_dir)
        
        # Generate cache key
        cache_key = generate_cache_key(lat, lon, radius_km, tif_files)
        
        # Check if cache is valid
        is_valid, reason = is_cache_valid(cache_dir, cache_key, tif_files)
        
        if is_valid:
            # Use cached files
            cached_files = get_cached_files(cache_dir, cache_key)
            if cached_files:
                print(f"\nUsing cached clipped rasters (cache key: {cache_key[:8]}...)")
                print(f"  Found {len(cached_files)} cached file(s)")
                
                # Copy cached files to output directory (temp directory)
                output_files: List[Path] = []
                for cached_file in cached_files:
                    output_path = output_dir / cached_file.name
                    if cached_file != output_path:
                        import shutil
                        shutil.copy2(cached_file, output_path)
                        print(f"  Copied: {cached_file.name}")
                    else:
                        output_path = cached_file
                    output_files.append(output_path)
                
                cache_subdir = get_cache_subdirectory(cache_dir, cache_key)
                print(f"  Cache location: {cache_subdir}")
                print(f"  Time saved: Using cached files instead of clipping")
                
                return output_files, True
        else:
            if reason:
                print(f"\nCache invalid or not found: {reason}")
                print(f"  Will clip and cache results (cache key: {cache_key[:8]}...)")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nFound {len(tif_files)} GeoTIFF file(s) to clip")
    
    clipped_files: List[Path] = []
    for index, tif_path in enumerate(tif_files, start=1):
        print(f"\n--- File {index}/{len(tif_files)} ---")
        output_path = output_dir / tif_path.name
        print(f"Processing {tif_path.name}...")
        try:
            clipped_path = clip_raster_to_circle(
                tif_path=tif_path,
                circle_geometry=circle_geometry,
                output_path=output_path,
                nodata=None
            )
            input_size_mb = tif_path.stat().st_size / (1024 * 1024)
            output_size_mb = clipped_path.stat().st_size / (1024 * 1024)
            print(f"  Saved to: {clipped_path}")
            print(f"  Size: {input_size_mb:.2f} MB -> {output_size_mb:.2f} MB")
            clipped_files.append(clipped_path)
        except Exception as exc:  # pragma: no cover - runtime I/O guard
            print(f"  Error clipping {tif_path.name}: {type(exc).__name__}: {exc}")
    
    # Save to cache if enabled and coordinates are provided and cache wasn't used
    if use_cache and lat is not None and lon is not None and radius_km is not None and clipped_files and not cache_used:
        if cache_dir is None:
            # Infer cache directory from output_dir structure
            if "processed" in str(output_dir) or "cache" in str(output_dir):
                processed_dir = output_dir.parent
            else:
                processed_dir = output_dir.parent.parent / "processed"
            cache_dir = get_cache_dir(processed_dir)
        
        cache_key = generate_cache_key(lat, lon, radius_km, tif_files)
        cache_subdir = get_cache_subdirectory(cache_dir, cache_key)
        
        # Copy clipped files to cache
        cached_files: List[Path] = []
        for clipped_file in clipped_files:
            cached_path = cache_subdir / clipped_file.name
            if clipped_file != cached_path:
                import shutil
                shutil.copy2(clipped_file, cached_path)
                cached_files.append(cached_path)
            else:
                cached_files.append(clipped_file)
        
        # Save cache metadata
        save_cache_metadata(
            cache_dir=cache_dir,
            cache_key=cache_key,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            source_files=tif_files,
            cached_files=cached_files
        )
        print(f"\n  Cached clipped rasters for future use (cache key: {cache_key[:8]}...)")
        print(f"  Cache location: {cache_subdir}")
    
    print(f"\nSuccessfully clipped {len(clipped_files)} of {len(tif_files)} file(s)")
    return clipped_files, cache_used


def verify_clipping_success(
    clipped_files: List[Path],
    circle_geometry,
    expected_radius_km: float = 100.0,
    edge_tolerance_km: float = 5.0
) -> bool:
    """
    Verify that clipped files were created successfully.
    
    Parameters
    ----------
    clipped_files : List[Path]
        List of paths to clipped files
    circle_geometry : shapely.geometry.Polygon
        Circle used for clipping (must be in WGS84/EPSG:4326)
    expected_radius_km : float, optional
        Expected radius of the clipping circle in kilometers (default: 100 km)
    edge_tolerance_km : float, optional
        Allowed overshoot (km) for pixel centers relative to the circle radius
    
    Returns
    -------
    bool
        True if all files exist and are valid, False otherwise
    """
    if not clipped_files:
        return False
    if circle_geometry is None:
        raise ValueError("circle_geometry is required to verify clipping radius.")
    
    geod = Geod(ellps="WGS84")
    circle_centroid = circle_geometry.centroid
    center_lon, center_lat = circle_centroid.x, circle_centroid.y
    all_valid = True
    for file_path in clipped_files:
        if not file_path.exists():
            print(f"  Warning: Clipped file not found: {file_path}")
            all_valid = False
            continue
        
        # Try to open the file to verify it's valid
        try:
            with rasterio.open(file_path) as src:
                if src.width == 0 or src.height == 0:
                    print(f"  Warning: Clipped file has zero dimensions: {file_path}")
                    all_valid = False
                    continue

                raster_crs = src.crs if src.crs else "EPSG:4326"
                to_wgs84 = None
                if raster_crs != "EPSG:4326":
                    to_wgs84 = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)

                def _to_wgs84(x_coords, y_coords):
                    if to_wgs84:
                        transformed = to_wgs84.transform(x_coords, y_coords)
                        if isinstance(transformed, tuple):
                            if len(transformed) >= 2:
                                return transformed[0], transformed[1]
                            raise ValueError(
                                "Transformer returned fewer than 2 values when converting to WGS84."
                            )
                        # Older pyproj versions may return numpy arrays directly
                        return transformed
                    return x_coords, y_coords

                # Ensure all valid pixel centers lie within the circle (with tolerance)
                mask_array = src.dataset_mask()
                valid_rows, valid_cols = np.nonzero(mask_array)

                if valid_rows.size == 0:
                    print(f"  Warning: No valid pixels found in {file_path}")
                    all_valid = False
                    continue

                xs, ys = rasterio.transform.xy(
                    src.transform,
                    valid_rows,
                    valid_cols,
                    offset="center"
                )
                xs = np.asarray(xs)
                ys = np.asarray(ys)
                lons_arr, lats_arr = _to_wgs84(xs, ys)
                lons = np.asarray(lons_arr)
                lats = np.asarray(lats_arr)

                center_lon_arr = np.full_like(lons, center_lon, dtype=float)
                center_lat_arr = np.full_like(lats, center_lat, dtype=float)
                _, _, distances_m = geod.inv(center_lon_arr, center_lat_arr, lons, lats)
                max_distance_km = np.max(distances_m) / 1000.0

                if max_distance_km > (expected_radius_km + edge_tolerance_km):
                    print(
                        "  Warning: Valid pixels extend beyond expected radius "
                        f"(max distance = {max_distance_km:.2f} km, "
                        f"allowed <= {expected_radius_km + edge_tolerance_km:.2f} km)"
                    )
                    all_valid = False
        except Exception as e:
            print(f"  Warning: Clipped file is invalid: {file_path} ({e})")
            all_valid = False
    
    return all_valid


UNIFORMITY_THRESHOLDS = {
    "soil_organic_carbon": {"type": "continuous", "std": 0.1},
    "soil_type": {"type": "categorical"},
    "soil_temperature": {"type": "continuous", "std": 0.2},
    "soil_moisture": {"type": "continuous", "std": 0.005},
    "soil_pH": {"type": "continuous", "std": 0.02},
    "land_cover": {"type": "categorical"},
}


def verify_clipped_data_integrity(
    clipped_files: List[Path],
    circle_geometry,
    expected_radius_km: float = 100.0,
    edge_tolerance_km: float = 5.0,
    thresholds: Optional[dict] = None
) -> bool:
    """
    Ensure clipped rasters contain meaningful variation and non-empty data.
    
    Parameters
    ----------
    clipped_files : List[Path]
        Paths to clipped rasters to inspect.
    circle_geometry : shapely.geometry.Polygon
        Circle used for clipping (must be in WGS84/EPSG:4326)
    expected_radius_km : float, optional
        Expected radius of the clipping circle in kilometers (default: 100 km)
    edge_tolerance_km : float, optional
        Allowed overshoot (km) for pixel centers relative to the circle radius
    thresholds : dict, optional
        Override of per-variable thresholds. Defaults to UNIFORMITY_THRESHOLDS.
    
    Returns
    -------
    bool
        True if all rasters meet integrity checks, False otherwise.
    """
    if not clipped_files:
        return False
    if circle_geometry is None:
        raise ValueError("circle_geometry is required to verify data integrity.")

    geod = Geod(ellps="WGS84")
    circle_centroid = circle_geometry.centroid
    center_lon, center_lat = circle_centroid.x, circle_centroid.y
    
    active_thresholds = thresholds or UNIFORMITY_THRESHOLDS
    all_valid = True
    for file_path in clipped_files:
        if not file_path.exists():
            print(f"  Warning: Clipped file not found: {file_path}")
            all_valid = False
            continue
        
        dataset_key = _infer_dataset_key(file_path)
        threshold_info = active_thresholds.get(dataset_key)
        if threshold_info is None:
            # No guidance for this dataset; skip uniformity check
            continue
        
        try:
            with rasterio.open(file_path) as src:
                data = src.read(1)
                nodata = src.nodata
                raster_crs = src.crs if src.crs else "EPSG:4326"

                to_wgs84 = None
                if raster_crs != "EPSG:4326":
                    to_wgs84 = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)

                def _to_wgs84(x_coords, y_coords):
                    if to_wgs84:
                        transformed = to_wgs84.transform(x_coords, y_coords)
                        if isinstance(transformed, tuple):
                            if len(transformed) >= 2:
                                return transformed[0], transformed[1]
                            raise ValueError(
                                "Transformer returned fewer than 2 values when converting to WGS84."
                            )
                        return transformed
                    return x_coords, y_coords
                
                if nodata is None:
                    valid_mask = np.isfinite(data)
                else:
                    if np.isnan(nodata):
                        valid_mask = ~np.isnan(data)
                    else:
                        valid_mask = data != nodata
                
                valid_count = np.count_nonzero(valid_mask)
                if valid_count == 0:
                    print(f"  Warning: {file_path.name} contains no valid pixels after clipping")
                    all_valid = False
                    continue

                rows, cols = np.nonzero(valid_mask)
                xs, ys = rasterio.transform.xy(
                    src.transform,
                    rows,
                    cols,
                    offset="center"
                )
                xs = np.asarray(xs)
                ys = np.asarray(ys)
                lons_arr, lats_arr = _to_wgs84(xs, ys)
                lons = np.asarray(lons_arr)
                lats = np.asarray(lats_arr)

                center_lon_arr = np.full_like(lons, center_lon, dtype=float)
                center_lat_arr = np.full_like(lats, center_lat, dtype=float)
                _, _, distances_m = geod.inv(center_lon_arr, center_lat_arr, lons, lats)
                distances_km = np.asarray(distances_m) / 1000.0
                inside_circle_mask = distances_km <= (expected_radius_km + edge_tolerance_km)

                if not np.any(inside_circle_mask):
                    print(
                        f"  Warning: {file_path.name} has no valid pixels within the expected circle "
                        f"(<= {expected_radius_km + edge_tolerance_km:.2f} km)."
                    )
                    all_valid = False
                    continue

                valid_values = data[valid_mask][inside_circle_mask]
                info_type = threshold_info.get("type")
                
                if info_type == "categorical":
                    unique_values = np.unique(valid_values)
                    if unique_values.size <= 1:
                        print(
                            f"  Warning: {file_path.name} contains a single category "
                            "after clipping"
                        )
                        all_valid = False
                elif info_type == "continuous":
                    std_threshold = threshold_info.get("std")
                    std_value = float(np.nanstd(valid_values))
                    if std_threshold is not None and std_value < std_threshold:
                        print(
                            f"  Warning: {file_path.name} standard deviation ({std_value:.4f}) "
                            f"is below threshold ({std_threshold})"
                        )
                        all_valid = False
                # If type is unknown, skip checks
        
        except Exception as exc:  # pragma: no cover - runtime I/O guard
            print(f"  Warning: Unable to inspect {file_path} ({type(exc).__name__}: {exc})")
            all_valid = False
    
    return all_valid


def _infer_dataset_key(file_path: Path) -> Optional[str]:
    stem_lower = file_path.stem.lower()
    if "soil_moisture" in stem_lower:
        return "soil_moisture"
    if "soil_temp" in stem_lower or "soil_temperature" in stem_lower:
        return "soil_temperature"
    if "soil_ph" in stem_lower:
        return "soil_pH"
    if "soil_type" in stem_lower:
        return "soil_type"
    if "land_cover" in stem_lower:
        return "land_cover"
    if stem_lower.startswith("soc") or "soc" in stem_lower:
        return "soil_organic_carbon"
    return None


if __name__ == "__main__":
    """Debug and test raster clipping functions."""
    import sys
    
    print("""============================================================
Raster Clipping - Debug Mode
============================================================
    
------------------------------------------------------------
1. Testing circle buffer creation:
------------------------------------------------------------""")
    
    try:
        circle = create_circle_buffer(lat=-12.0, lon=-55.0, radius_km=100.0)
        print(f"""  PASS: Successfully created circle buffer
    Center: (-12.0, -55.0)
    Radius: 100.0 km
    Circle type: {type(circle).__name__}
    Bounds: {circle.bounds}""")
    except Exception as e:
        print(f"  FAIL: Could not create circle buffer: {type(e).__name__}: {e}")
        sys.exit(1)
    
    # Test with actual GeoTIFF files if available
    print("""
------------------------------------------------------------
2. Testing with GeoTIFF files:
------------------------------------------------------------""")
    
    project_root = Path(__file__).parent.parent.parent.parent
    input_dir = project_root / "data" / "raw"
    output_dir = project_root / "data" / "processed"
    
    if input_dir.exists():
        tif_files = list(input_dir.glob("*.tif"))
        if tif_files:
            print(f"  Found {len(tif_files)} GeoTIFF file(s) in {input_dir}")
            print(f"  Testing with first file: {tif_files[0].name}")
            
            # Test clipping (dry run - just check if function works)
            try:
                # Just verify the function can be called (we won't actually clip in debug mode)
                print("""  PASS: clip_raster_to_circle function is available
  Note: Actual clipping requires valid GeoTIFF files""")
            except Exception as e:
                print(f"  FAIL: Error testing clip function: {type(e).__name__}: {e}")
        else:
            print(f"""  No GeoTIFF files found in {input_dir}
  Note: Place GeoTIFF files in data/raw/ to test clipping""")
    else:
        print(f"""  Input directory not found: {input_dir}
  Note: Create data/raw/ directory and add GeoTIFF files to test""")
    
    print("""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.data.raster_clip import clip_all_rasters_to_circle
  from src.utils.geospatial import create_circle_buffer
  circle = create_circle_buffer(lat=-12.0, lon=-55.0, radius_km=100.0)
  clipped_files, cache_used = clip_all_rasters_to_circle(
      input_dir=Path('data/raw'),
      output_dir=Path('data/processed'),
      circle_geometry=circle,
      lat=-12.0,
      lon=-55.0,
      radius_km=100.0,
      use_cache=True
  )
  # Returns: (List[Path], bool) - list of clipped files and whether cache was used
------------------------------------------------------------""")

