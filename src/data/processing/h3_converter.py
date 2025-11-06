"""
H3 Index Conversion Module

Adds H3 indexes to CSV files based on lat/lon coordinates.
"""

from pathlib import Path
from typing import List
import pandas as pd
import h3
import tempfile
import shutil


def process_all_csv_files_with_h3(
    csv_dir: Path,
    resolution: int = 7,
    pattern: str = "*.csv",
    lat_column: str = "lat",
    lon_column: str = "lon"
) -> List[Path]:
    """
    Add H3 indexes to all CSV files in a directory.
    
    Parameters
    ----------
    csv_dir : Path
        Directory containing CSV files
    resolution : int, optional
        H3 resolution (0-15, higher = finer hexagons) (default: 7)
    pattern : str, optional
        File pattern to match (default: "*.csv")
    lat_column : str, optional
        Name of latitude column (default: "lat")
    lon_column : str, optional
        Name of longitude column (default: "lon")
    
    Returns
    -------
    List[Path]
        List of processed CSV file paths
    """
    if not csv_dir.exists():
        raise FileNotFoundError(f"Directory not found: {csv_dir}")
    
    # Validate H3 resolution
    if not isinstance(resolution, int) or resolution < 0 or resolution > 15:
        raise ValueError(f"H3 resolution must be an integer between 0 and 15, got {resolution}")
    
    # Find all CSV files
    csv_files = list(csv_dir.glob(pattern))
    
    # Exclude suitability_scores.csv (output file, not input)
    csv_files = [f for f in csv_files if 'suitability' not in f.name.lower()]
    
    if not csv_files:
        print(f"No CSV files found in {csv_dir} matching pattern {pattern}")
        return []
    
    print(f"\nProcessing {len(csv_files)} CSV file(s) with H3 resolution {resolution}...")
    
    processed_files = []
    for csv_path in csv_files:
        try:
            # Skip if already has h3_index column
            df_check = pd.read_csv(csv_path, nrows=1)
            if 'h3_index' in df_check.columns:
                print(f"  Skipping {csv_path.name} (already has H3 indexes)")
                processed_files.append(csv_path)
                continue
            
            print(f"  Processing {csv_path.name}...")
            
            # Read CSV
            df = pd.read_csv(csv_path)
            
            if df.empty:
                print(f"    Warning: CSV file is empty, skipping")
                continue
            
            # Check for required columns
            if lat_column not in df.columns:
                print(f"    Warning: Missing '{lat_column}' column, skipping")
                continue
            
            if lon_column not in df.columns:
                print(f"    Warning: Missing '{lon_column}' column, skipping")
                continue
            
            # Check for NaN values in coordinates
            nan_lat = df[lat_column].isna().sum()
            nan_lon = df[lon_column].isna().sum()
            if nan_lat > 0 or nan_lon > 0:
                print(f"    Warning: Found {nan_lat} NaN lat values and {nan_lon} NaN lon values")
                # Filter out rows with NaN coordinates
                df = df.dropna(subset=[lat_column, lon_column])
                if df.empty:
                    print(f"    Warning: No valid coordinates after filtering, skipping")
                    continue
            
            # Validate coordinate ranges
            invalid_lat = ((df[lat_column] < -90) | (df[lat_column] > 90)).sum()
            invalid_lon = ((df[lon_column] < -180) | (df[lon_column] > 180)).sum()
            if invalid_lat > 0 or invalid_lon > 0:
                print(f"    Warning: Found {invalid_lat} invalid lat values and {invalid_lon} invalid lon values")
                # Filter out rows with invalid coordinates
                df = df[(df[lat_column] >= -90) & (df[lat_column] <= 90)]
                df = df[(df[lon_column] >= -180) & (df[lon_column] <= 180)]
                if df.empty:
                    print(f"    Warning: No valid coordinates after filtering, skipping")
                    continue
            
            # Add H3 indexes
            df['h3_index'] = df.apply(
                lambda row: h3.latlng_to_cell(row[lat_column], row[lon_column], resolution),
                axis=1
            )
            
            # Save back to CSV (use a temporary file first to avoid permission errors)
            # Create temporary file in same directory
            temp_file = csv_path.parent / f".{csv_path.name}.tmp"
            try:
                # Write to temporary file
                df.to_csv(temp_file, index=False)
                # Replace original file atomically (works on Windows too)
                if csv_path.exists():
                    csv_path.unlink()  # Delete original first
                shutil.move(str(temp_file), str(csv_path))
            except PermissionError as e:
                # Clean up temp file if move fails
                if temp_file.exists():
                    temp_file.unlink()
                print(f"    Error: Cannot write to {csv_path.name} - file may be open in another program")
                raise e
            except Exception as e:
                # Clean up temp file if move fails
                if temp_file.exists():
                    temp_file.unlink()
                raise e
            
            print(f"    Added H3 indexes: {len(df):,} rows")
            processed_files.append(csv_path)
            
        except KeyError as e:
            print(f"  Error processing {csv_path.name}: Missing required column: {e}")
            continue
        except ValueError as e:
            print(f"  Error processing {csv_path.name}: Invalid value: {e}")
            continue
        except Exception as e:
            print(f"  Error processing {csv_path.name}: {type(e).__name__}: {e}")
            continue
    
    return processed_files


if __name__ == "__main__":
    """Debug and test H3 conversion."""
    import sys
    
    print("""============================================================
H3 Index Conversion - Debug Mode
============================================================""")
    
    # Test with actual CSV files if available
    project_root = Path(__file__).parent.parent.parent.parent
    csv_dir = project_root / "data" / "processed"
    
    if csv_dir.exists():
        csv_files = list(csv_dir.glob("*.csv"))
        if csv_files:
            print(f"\nFound {len(csv_files)} CSV file(s) in {csv_dir}")
            print("Testing with first file...")
            
            try:
                # Test processing
                processed = process_all_csv_files_with_h3(
                    csv_dir=csv_dir,
                    resolution=7,
                    pattern=csv_files[0].name
                )
                print(f"PASS: Successfully processed {len(processed)} file(s)")
            except Exception as e:
                print(f"FAIL: Error: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            print(f"\nNo CSV files found in {csv_dir}")
    else:
        print(f"\nDirectory not found: {csv_dir}")
