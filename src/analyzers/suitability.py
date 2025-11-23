"""
Soil Data Merging and Aggregation Module

Merges tabular datasets (CSV files or in-memory DataFrames) by coordinates
and aggregates data by H3 hexagon regions if available.

This module handles data preparation for suitability scoring:
- Merges multiple soil property datasets by coordinates
- Aggregates data by H3 hexagon regions (if H3 indexes are available)
- Adds H3 boundary geometries for visualization (after aggregation for memory efficiency)

Note: Actual suitability scoring is performed by `biochar_suitability.py` module.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import h3

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def merge_csv_files_by_coordinates(
    csv_files: List[Path],
    lon_column: str = "lon",
    lat_column: str = "lat",
    precision: int = 6
) -> pd.DataFrame:
    """
    Merge multiple CSV files by coordinates (lon, lat).
    
    Parameters
    ----------
    csv_files : List[Path]
        List of CSV file paths to merge
    lon_column : str, optional
        Name of longitude column (default: "lon")
    lat_column : str, optional
        Name of latitude column (default: "lat")
    precision : int, optional
        Decimal precision for coordinate matching (default: 6)
    
    Returns
    -------
    pd.DataFrame
        Merged DataFrame with all columns from all CSV files
    """
    if not csv_files:
        raise ValueError("No CSV files provided for merging")
    
    dataframes = []
    for csv_file in csv_files:
        if not csv_file.exists():
            print(f"CSV file not found: {csv_file}")
            continue
        
        try:
            df = pd.read_csv(csv_file)
            
            # Round coordinates for matching
            if lon_column in df.columns and lat_column in df.columns:
                df[lon_column] = df[lon_column].round(precision)
                df[lat_column] = df[lat_column].round(precision)
            
            dataframes.append(df)
            print(f"Loaded {csv_file.name}: {len(df):,} rows, {len(df.columns)} columns")
            
        except Exception as e:
            print(f"Error reading {csv_file.name}: {type(e).__name__}: {e}")
            continue
    
    if not dataframes:
        raise ValueError("No valid CSV files could be read")
    
    # Merge all dataframes by coordinates
    merged_df = dataframes[0]
    for df in dataframes[1:]:
        # Merge on coordinates
        if lon_column in merged_df.columns and lat_column in merged_df.columns:
            merged_df = pd.merge(
                merged_df,
                df,
                on=[lon_column, lat_column],
                how='outer',
                suffixes=('', '_dup')
            )
        else:
            # If no coordinates, just concatenate (shouldn't happen)
            merged_df = pd.concat([merged_df, df], axis=1)
    
    # Remove duplicate columns (keep first occurrence)
    merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_dup')]
    
    # Remove any duplicate columns
    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
    
    # Sort by coordinates
    if lon_column in merged_df.columns and lat_column in merged_df.columns:
        merged_df = merged_df.sort_values([lat_column, lon_column])
    
    return merged_df


def add_h3_boundaries_to_dataframe(df: pd.DataFrame, h3_column: str = "h3_index") -> pd.DataFrame:
    """
    Add h3_boundary_geojson column to a DataFrame with H3 indexes.
    
    This function generates hexagon boundary geometries from H3 index strings.
    Used after aggregation to add boundaries only for the aggregated hexagons
    (much more memory-efficient than generating boundaries for all points).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with h3_index column
    h3_column : str, default "h3_index"
        Name of the H3 index column
        
    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame with h3_boundary_geojson column added
    """
    if h3_column not in df.columns:
        raise KeyError(f"Missing required column '{h3_column}' in DataFrame.")
    
    working = df.copy()
    
    # Generate boundaries for each unique H3 index
    working["h3_boundary_geojson"] = working[h3_column].apply(
        lambda cell: [[lon, lat] for lat, lon in h3.cell_to_boundary(cell)]
    )
    
    return working


def merge_and_aggregate_soil_data(
    csv_dir: Path,
    pattern: str = "*.csv",
    lon_column: str = "lon",
    lat_column: str = "lat",
    dataframes: Optional[Dict[str, pd.DataFrame]] = None,
    output_csv: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Merge tabular datasets by coordinates and aggregate by H3 hexagons if available.
    
    This function handles the data processing pipeline:
    1. Loads DataFrames (from in-memory dict or CSV files)
    2. Merges all datasets by coordinates
    3. Aggregates data by H3 hexagon regions if H3 indexes are available
    4. Adds H3 boundaries for visualization
    
    If H3 indexes are available, aggregates data by hexagon regions (averages values per hexagon).
    This creates one row per hexagon region instead of per point, reducing data size significantly.
    
    Parameters
    ----------
    csv_dir : Path
        Directory containing CSV files (with optional H3 indexes)
    pattern : str, optional
        File pattern to match (default: "*.csv")
    lon_column : str, optional
        Name of longitude column (default: "lon")
    lat_column : str, optional
        Name of latitude column (default: "lat")
    dataframes : Dict[str, pd.DataFrame], optional
        Optional mapping of dataset names to DataFrames. When provided, the function
        operates on these in-memory tables instead of loading CSV files from disk.
    output_csv : Path, optional
        Path to save merged CSV. If None, no CSV is saved (default: None)
    
    Returns
    -------
    pd.DataFrame
        Merged and aggregated DataFrame (one row per hexagon if H3 indexes available, 
        otherwise one row per point)
    """
    if dataframes is None and not csv_dir.exists():
        raise FileNotFoundError(f"Directory not found: {csv_dir}")
    
    loaded_frames: List[pd.DataFrame] = []
    source_names: List[str] = []

    if dataframes is not None:
        if not dataframes:
            print("No DataFrames provided for suitability scoring.")
            return pd.DataFrame()

        print(f"\nReceived {len(dataframes)} DataFrame(s) to process")
        for name, df in dataframes.items():
            if df.empty:
                print(f"  DataFrame '{name}' is empty, skipping")
                continue
            if lon_column not in df.columns or lat_column not in df.columns:
                print(f"  DataFrame '{name}' missing coordinates, skipping")
                continue
            # Round coordinates in-place to avoid copy (if possible)
            df[lon_column] = df[lon_column].round(6)
            df[lat_column] = df[lat_column].round(6)
            loaded_frames.append(df)
            source_names.append(name)
            print(f"  Loaded '{name}': {len(df):,} rows, {len(df.columns)} columns")
    else:
        csv_files = [f for f in csv_dir.glob(pattern) if 'suitability' not in f.name.lower()]
        if not csv_files:
            print(f"No CSV files found in {csv_dir} matching pattern {pattern}")
            return pd.DataFrame()

        print(f"\nFound {len(csv_files)} CSV file(s) to process")
        print("\nLoading CSV files...")

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                if df.empty:
                    print(f"  {csv_file.name} is empty, skipping")
                    continue
                if lon_column not in df.columns or lat_column not in df.columns:
                    print(f"  {csv_file.name} missing coordinates, skipping")
                    continue

                df[lon_column] = df[lon_column].round(6)
                df[lat_column] = df[lat_column].round(6)
                loaded_frames.append(df)
                source_names.append(csv_file.stem)
                print(f"  Loaded {csv_file.name}: {len(df):,} rows, {len(df.columns)} columns")

            except Exception as e:
                print(f"  Error reading {csv_file.name}: {type(e).__name__}: {e}")
                continue

    if not loaded_frames:
        print("No valid tabular datasets available for scoring.")
        return pd.DataFrame()
    
    # Drop boundary columns before merging (memory optimization - will add back after aggregation)
    boundary_col = 'h3_boundary_geojson'
    for i, df in enumerate(loaded_frames):
        if boundary_col in df.columns:
            loaded_frames[i] = df.drop(columns=[boundary_col])
    
    print("\nMerging datasets by coordinates...")
    merged_df = loaded_frames[0].copy()
    
    for i, df in enumerate(loaded_frames[1:], start=2):
        # Merge on coordinates
        merged_df = pd.merge(
            merged_df,
            df,
            on=[lon_column, lat_column],
            how='outer',
            suffixes=('', f'_file{i}')
        )
        source_label = source_names[i - 1] if i - 1 < len(source_names) else i
        print(f"  Merged dataset {source_label} ({i}/{len(loaded_frames)}): {len(merged_df):,} rows")
    
    # Remove duplicate columns (keep first occurrence)
    # Remove columns that end with '_file' suffix (from merging)
    cols_to_remove = [col for col in merged_df.columns if col.endswith('_file')]
    merged_df = merged_df.drop(columns=cols_to_remove)
    
    # Remove any remaining duplicate columns
    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
    
    # Ensure boundary column is not present (in case it somehow got through)
    if boundary_col in merged_df.columns:
        merged_df = merged_df.drop(columns=[boundary_col])
    
    # Sort by coordinates
    merged_df = merged_df.sort_values([lat_column, lon_column])
    
    print(f"Merged DataFrame: {len(merged_df):,} rows, {len(merged_df.columns)} columns")
    
    # Check if H3 indexes are available and aggregate by hexagon
    if 'h3_index' in merged_df.columns:
        print("\nH3 indexes found - aggregating by hexagon regions...")
        
        # Identify property columns (exclude coordinates, H3 index, and score columns)
        exclude_cols = {lon_column, lat_column, 'h3_index'}
        property_cols = [col for col in merged_df.columns 
                        if col not in exclude_cols 
                        and not col.endswith('_score')]
        
        # Filter to only numeric columns for aggregation
        # Check which columns are numeric
        numeric_cols = []
        for col in property_cols:
            try:
                # Try to convert to numeric
                pd.to_numeric(merged_df[col], errors='raise')
                numeric_cols.append(col)
            except (ValueError, TypeError):
                # Skip non-numeric columns (like color codes, strings, etc.)
                print(f"  Skipping non-numeric column: {col}")
                continue
        
        # Build aggregation dictionary
        # Use mean for numeric property columns (continuous values)
        agg_dict = {}
        for col in numeric_cols:
            agg_dict[col] = 'mean'
        
        # Aggregate coordinates (use mean)
        agg_dict[lon_column] = 'mean'
        agg_dict[lat_column] = 'mean'
        
        if not agg_dict:
            print("  No numeric columns to aggregate")
            data_for_scoring = merged_df
        else:
            # Group by H3 index and aggregate
            hexagon_df = merged_df.groupby('h3_index').agg(agg_dict).reset_index()
            
            # Calculate point count per hexagon
            point_counts = merged_df.groupby('h3_index').size().reset_index(name='point_count')
            hexagon_df = hexagon_df.merge(point_counts, on='h3_index')
            
            print(f"Aggregated to {len(hexagon_df):,} hexagon regions")
            print(f"  Average points per hexagon: {len(merged_df) / len(hexagon_df):.1f}")
            print(f"  Total points: {len(merged_df):,}")
            print(f"  Aggregated {len(numeric_cols)} numeric columns")
            
            # Generate boundaries for aggregated hexagons (memory-efficient: only ~1,491 vs ~130,000)
            hexagon_df = add_h3_boundaries_to_dataframe(hexagon_df, h3_column='h3_index')
            
            # Use hexagon-aggregated data
            data_for_scoring = hexagon_df
    else:
        print("\nNo H3 indexes found - processing individual points...")
        data_for_scoring = merged_df
    
    print(f"\nMerged and aggregated DataFrame: {len(data_for_scoring):,} rows, {len(data_for_scoring.columns)} columns")
    
    # Save to output CSV if requested
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        data_for_scoring.to_csv(output_csv, index=False)
        print(f"  Saved merged data to: {output_csv}")
    
    return data_for_scoring

