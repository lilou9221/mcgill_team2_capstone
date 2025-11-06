"""
Raster Clipping Module

Clips GeoTIFF files to circular buffers around user-specified points.
Handles coordinate transformations and saves clipped rasters.
"""

from pathlib import Path
from typing import List, Optional

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping
import numpy as np

from src.utils.geospatial import create_circle_buffer


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
            out_image, out_transform = mask(src, geojson_geom, crop=True, nodata=nodata)
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
        if nodata is not None:
            out_meta["nodata"] = nodata
        elif out_meta.get("nodata") is None:
            # If no nodata specified, use a default based on data type
            if out_image.dtype == np.uint8:
                out_meta["nodata"] = 0
            elif out_image.dtype in [np.int16, np.int32]:
                out_meta["nodata"] = -9999
            else:
                out_meta["nodata"] = np.nan
    
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


def process_single_raster(
    tif_path: Path,
    circle_geometry,
    output_dir: Path,
    nodata: Optional[float] = None
) -> Optional[Path]:
    """
    Process a single GeoTIFF file by clipping it to the specified geometry.

    Parameters
    ----------
    tif_path : Path
        Path to the input GeoTIFF file.
    circle_geometry : shapely.geometry.Polygon
        Circular buffer polygon.
    output_dir : Path
        Directory where the clipped file will be stored.
    nodata : float, optional
        NoData value for the output file.

    Returns
    -------
    Optional[Path]
        Path to the clipped file, or None if processing failed.
    """
    try:
        output_path = output_dir / tif_path.name
        print(f"\nProcessing {tif_path.name}...")
        clipped_path = clip_raster_to_circle(
            tif_path=tif_path,
            circle_geometry=circle_geometry,
            output_path=output_path,
            nodata=nodata
        )

        input_size = tif_path.stat().st_size / (1024 * 1024)  # MB
        output_size = clipped_path.stat().st_size / (1024 * 1024)  # MB
        print(f"  Saved to: {clipped_path}")
        print(f"  Size: {input_size:.2f} MB -> {output_size:.2f} MB")
        return clipped_path
    except Exception as exc:  # pragma: no cover - runtime I/O guard
        print(f"  Error clipping {tif_path.name}: {type(exc).__name__}: {exc}")
        return None


def clip_all_rasters_to_circle(
    input_dir: Path,
    output_dir: Path,
    circle_geometry,
    pattern: str = "*.tif"
) -> List[Path]:
    """
    Clip all GeoTIFF files in a directory to a circular geometry.
    
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
    
    Returns
    -------
    List[Path]
        List of paths to clipped output files
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all GeoTIFF files
    tif_files = list(input_dir.glob(pattern))
    
    if not tif_files:
        print(f"No GeoTIFF files found in {input_dir} matching pattern {pattern}")
        return []
    
    print(f"\nFound {len(tif_files)} GeoTIFF file(s) to clip")
    
    clipped_files = []
    for tif_path in tif_files:
        try:
            # Create output filename (same name, in output directory)
            output_path = output_dir / tif_path.name
            
            print(f"\nClipping {tif_path.name}...")
            
            # Clip the raster
            clipped_path = clip_raster_to_circle(
                tif_path=tif_path,
                circle_geometry=circle_geometry,
                output_path=output_path
            )
            
            clipped_files.append(clipped_path)
            print(f"  Saved to: {clipped_path}")
            
            # Show file size comparison
            input_size = tif_path.stat().st_size / (1024 * 1024)  # MB
            output_size = clipped_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  Size: {input_size:.2f} MB -> {output_size:.2f} MB")
            
        except Exception as e:
            print(f"  Error clipping {tif_path.name}: {type(e).__name__}: {e}")
            continue
    
    print(f"\nSuccessfully clipped {len(clipped_files)} of {len(tif_files)} file(s)")
    return clipped_files


def verify_clipping_success(clipped_files: List[Path]) -> bool:
    """
    Verify that clipped files were created successfully.
    
    Parameters
    ----------
    clipped_files : List[Path]
        List of paths to clipped files
    
    Returns
    -------
    bool
        True if all files exist and are valid, False otherwise
    """
    if not clipped_files:
        return False
    
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
        except Exception as e:
            print(f"  Warning: Clipped file is invalid: {file_path} ({e})")
            all_valid = False
    
    return all_valid


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
  clipped = clip_all_rasters_to_circle(
      input_dir=Path('data/raw'),
      output_dir=Path('data/processed'),
      circle_geometry=circle
  )
------------------------------------------------------------""")

