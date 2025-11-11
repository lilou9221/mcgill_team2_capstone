"""
Raster to CSV Conversion Module

Converts GeoTIFF raster files to CSV format with coordinates and pixel values.
Handles nodata values and extracts pixel coordinates.
"""

from pathlib import Path
from typing import Optional, Sequence
import rasterio
import pandas as pd
import numpy as np
from rasterio.transform import xy


VALUE_UNIT_PATTERNS: Sequence[tuple[str, str]] = (
    ("soil_temperature", "K"),
    ("soil_temp", "K"),
    ("soil_moisture", "m3/m3"),
    ("soil_organic_carbon", "g/kg"),
    ("soc", "g/kg"),
    ("soil_ph", "pH"),
)

VALUE_SCALING_PATTERNS: Sequence[tuple[str, float]] = (
    ("soil_pH", 0.1),
    ("soil_ph", 0.1),
)


def _infer_unit(*names: str) -> Optional[str]:
    """
    Infer the unit for a raster value column based on known naming patterns.
    """
    combined = " ".join(name.lower() for name in names if name)
    for pattern, unit in VALUE_UNIT_PATTERNS:
        if pattern in combined:
            return unit
    return None


def _infer_scaling_factor(*names: str) -> Optional[float]:
    """
    Infer a scaling factor to convert raw raster values into human-readable units.
    """
    combined = " ".join(name.lower() for name in names if name)
    for pattern, factor in VALUE_SCALING_PATTERNS:
        if pattern.lower() in combined:
            return factor
    return None


def raster_to_csv(
    tif_path: Path,
    output_csv: Path,
    band: int = 1,
    nodata_handling: str = "skip",
    value_column_name: Optional[str] = None
) -> pd.DataFrame:
    """
    Convert a GeoTIFF raster to CSV format with coordinates and pixel values.
    
    Parameters
    ----------
    tif_path : Path
        Path to input GeoTIFF file
    output_csv : Path
        Path to output CSV file
    band : int, optional
        Band number to extract (default: 1)
    nodata_handling : str, optional
        How to handle nodata values: "skip", "nan", or "zero" (default: "skip")
    value_column_name : str, optional
        Name for the value column. If None, uses the filename stem.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: lon, lat, value
    """
    if not tif_path.exists():
        raise FileNotFoundError(f"Input raster not found: {tif_path}")
    
    # Ensure output directory exists
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine value column name (optionally include unit)
    base_column_name = value_column_name if value_column_name is not None else tif_path.stem
    unit_label = _infer_unit(base_column_name, tif_path.stem)
    if unit_label and f"({unit_label}" not in base_column_name:
        value_column_name = f"{base_column_name} ({unit_label})"
    else:
        value_column_name = base_column_name
    scaling_factor = _infer_scaling_factor(base_column_name, tif_path.stem)
    
    # Open raster
    with rasterio.open(tif_path) as src:
        # Read the specified band
        band_data = src.read(band).astype(np.float32)
        if scaling_factor and scaling_factor != 1.0:
            band_data *= scaling_factor
        
        # Get nodata value
        nodata = src.nodata
        
        # Get transform for coordinate conversion
        transform = src.transform
        
        # Get dimensions
        height, width = band_data.shape
        
        # Create coordinate arrays
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        
        # Convert pixel coordinates to geographic coordinates
        lons, lats = xy(transform, rows, cols)
        
        # Flatten arrays
        lons_flat = lons.flatten()
        lats_flat = lats.flatten()
        values_flat = band_data.flatten()
        
        # Create DataFrame
        df = pd.DataFrame({
            'lon': lons_flat,
            'lat': lats_flat,
            value_column_name: values_flat
        })
        
        # Handle nodata values
        if nodata is not None:
            if nodata_handling == "skip":
                # Remove rows with nodata values
                df = df[df[value_column_name] != nodata]
            elif nodata_handling == "nan":
                # Replace nodata with NaN
                df.loc[df[value_column_name] == nodata, value_column_name] = np.nan
            elif nodata_handling == "zero":
                # Replace nodata with 0
                df.loc[df[value_column_name] == nodata, value_column_name] = 0
            else:
                raise ValueError(f"Unknown nodata_handling: {nodata_handling}. Use 'skip', 'nan', or 'zero'")
        
        # Remove NaN values if any remain (from nodata_handling="nan" or other sources)
        if nodata_handling != "skip":
            df = df.dropna(subset=[value_column_name])
    
    # Save to CSV
    df.to_csv(output_csv, index=False)
    
    return df


def convert_all_rasters_to_csv(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.tif",
    band: int = 1,
    nodata_handling: str = "skip",
    clean_output_dir: bool = True
) -> list[Path]:
    """
    Convert all GeoTIFF files in a directory to CSV format.
    
    Parameters
    ----------
    input_dir : Path
        Directory containing input GeoTIFF files
    output_dir : Path
        Directory to save CSV files
    pattern : str, optional
        File pattern to match (default: "*.tif")
    band : int, optional
        Band number to extract (default: 1)
    nodata_handling : str, optional
        How to handle nodata values: "skip", "nan", or "zero" (default: "skip")
    
    clean_output_dir : bool, optional
        If True, delete existing CSV files in the output directory before conversion (default: True)

    Returns
    -------
    List[Path]
        List of paths to output CSV files
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    if clean_output_dir:
        removed_files = 0
        for existing_csv in output_dir.glob("*.csv"):
            try:
                existing_csv.unlink()
                removed_files += 1
            except Exception as exc:  # pragma: no cover - filesystem variability
                print(f"  Warning: Could not remove {existing_csv.name}: {type(exc).__name__}: {exc}")
        if removed_files:
            print(f"\nRemoved {removed_files} existing CSV file(s) from {output_dir} before conversion")
    
    # Find all GeoTIFF files
    tif_files = list(input_dir.glob(pattern))
    
    if not tif_files:
        print(f"No GeoTIFF files found in {input_dir} matching pattern {pattern}")
        return []
    
    print(f"\nFound {len(tif_files)} GeoTIFF file(s) to convert to CSV")
    
    csv_files = []
    for tif_path in tif_files:
        try:
            # Create output CSV filename (same name, .csv extension)
            output_csv = output_dir / f"{tif_path.stem}.csv"
            
            print(f"\nConverting {tif_path.name} to CSV...")
            
            # Convert to CSV
            df = raster_to_csv(
                tif_path=tif_path,
                output_csv=output_csv,
                band=band,
                nodata_handling=nodata_handling
            )
            
            csv_files.append(output_csv)
            print(f"  Saved to: {output_csv}")
            print(f"  Rows: {len(df):,}")
            print(f"  Columns: {list(df.columns)}")
            
            # Show file size
            csv_size = output_csv.stat().st_size / (1024 * 1024)  # MB
            print(f"  Size: {csv_size:.2f} MB")
            
        except Exception as e:
            print(f"  Error converting {tif_path.name}: {type(e).__name__}: {e}")
            continue
    
    print(f"\nSuccessfully converted {len(csv_files)} of {len(tif_files)} file(s) to CSV")
    return csv_files


if __name__ == "__main__":
    """Debug and test raster to CSV conversion."""
    import sys
    
    print("""============================================================
Raster to CSV Conversion - Debug Mode
============================================================""")
    
    # Test with actual GeoTIFF files if available
    project_root = Path(__file__).parent.parent.parent.parent
    input_dir = project_root / "data" / "processed"
    output_dir = project_root / "data" / "processed"
    
    if input_dir.exists():
        tif_files = list(input_dir.glob("*.tif"))
        if tif_files:
            print(f"\nFound {len(tif_files)} GeoTIFF file(s) in {input_dir}")
            print(f"Testing with first file: {tif_files[0].name}")
            
            try:
                output_csv = output_dir / f"{tif_files[0].stem}_test.csv"
                df = raster_to_csv(
                    tif_path=tif_files[0],
                    output_csv=output_csv,
                    band=1,
                    nodata_handling="skip"
                )
                print(f"""\nPASS: Successfully converted to CSV
  Output: {output_csv}
  Rows: {len(df):,}
  Columns: {list(df.columns)}
  Sample data:
{df.head()}""")
            except Exception as e:
                print(f"  FAIL: Error converting: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            print(f"\nNo GeoTIFF files found in {input_dir}")
            print("Note: Place GeoTIFF files in data/processed/ to test conversion")
    else:
        print(f"\nInput directory not found: {input_dir}")
        print("Note: Create data/processed/ directory and add GeoTIFF files to test")
    
    print("""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.data.raster_to_csv import convert_all_rasters_to_csv
  csv_files = convert_all_rasters_to_csv(
      input_dir=Path('data/processed'),
      output_dir=Path('data/processed'),
      nodata_handling='skip'
  )
------------------------------------------------------------""")

