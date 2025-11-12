"""
Suitability Score Calculator

Calculates suitability scores based on soil property thresholds.
Merges tabular datasets (CSV files or in-memory DataFrames) and calculates
individual property scores before producing the final suitability score.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analysis.thresholds import load_thresholds, get_property_thresholds


def calculate_property_score(value: float, thresholds: Dict[str, Any]) -> float:
    """
    Calculate score (0-10) for a single property value based on thresholds.
    
    Scoring Logic:
    - Values within optimal range: score 6-10
      * Middle value of optimal range = 10 (best value)
      * Edges of optimal range = 6
      * Linear interpolation between center and edges
    
    - Values outside optimal range (above or below): score 0-6
      * At optimal boundary = 6
      * Further from optimal range = lower score (closer to 0)
      * Normalized distance from optimal boundary to acceptable boundary
    
    Note: We assume the middle value of the optimal range is the best value.
    
    Parameters
    ----------
    value : float
        Property value
    thresholds : Dict[str, Any]
        Threshold dictionary for the property
    
    Returns
    -------
    float
        Score between 0 and 10 (higher = better soil health, less biochar needed)
    """
    if pd.isna(value):
        return np.nan
    
    # Get optimal range (high range = optimal)
    scoring = thresholds.get('scoring', {})
    
    if 'high' not in scoring:
        # No optimal range defined, return 0
        return 0.0
    
    high_range = scoring['high']
    if not isinstance(high_range, (list, tuple)) or len(high_range) != 2:
        # Invalid high range format, return 0
        return 0.0
    
    optimal_min = float(high_range[0])
    optimal_max = float(high_range[1])
    
    # Validate range
    if optimal_min >= optimal_max:
        # Invalid range (min >= max), return 0
        return 0.0
    
    # Get acceptable range bounds for distance calculation
    acceptable_min = thresholds.get('acceptable_min', optimal_min)
    acceptable_max = thresholds.get('acceptable_max', optimal_max)
    
    # Calculate center of optimal range (assumed to be the best value)
    center = (optimal_min + optimal_max) / 2.0
    
    # Calculate distance from optimal range
    if optimal_min <= value <= optimal_max:
        # Value is within optimal range - score 6-10
        # Middle value (center) = 10, edges = 6
        if optimal_min == optimal_max:
            return 10.0  # Single optimal value (center)
        
        # Calculate distance from center
        distance_from_center = abs(value - center)
        max_distance_from_center = (optimal_max - optimal_min) / 2.0
        
        if max_distance_from_center == 0:
            return 10.0
        
        # Score decreases from 10 (center) to 6 (edges) as distance from center increases
        # Linear interpolation: at center (distance=0) -> score=10, at edges (distance=max) -> score=6
        ratio = 1.0 - (distance_from_center / max_distance_from_center)
        score = 6.0 + (ratio * 4.0)  # 6 to 10
        return max(6.0, min(10.0, score))
    
    elif value < optimal_min:
        # Value is below optimal range - score 0-6
        # At optimal_min (boundary) = 6, further away = lower
        
        # Check if value is below acceptable range (very poor)
        if value < acceptable_min:
            # Value is beyond acceptable range - score 0
            return 0.0
        
        # Calculate distance from optimal boundary
        distance = optimal_min - value
        
        # Calculate maximum possible distance (from acceptable_min to optimal_min)
        max_distance = optimal_min - acceptable_min
        
        if max_distance <= 0:
            # No range below optimal, use a default penalty
            # Score decreases from 6 to 0 as distance increases
            return max(0.0, 6.0 - (distance * 6.0 / abs(optimal_min) if optimal_min != 0 else distance * 6.0))
        
        # Score decreases from 6 to 0 as distance increases
        # Linear interpolation: at optimal_min (distance=0) -> score=6, at acceptable_min (distance=max_distance) -> score=0
        ratio = 1.0 - (distance / max_distance)
        score = ratio * 6.0  # 0 to 6
        return max(0.0, min(6.0, score))
    
    else:  # value > optimal_max
        # Value is above optimal range - score 0-6
        # At optimal_max (boundary) = 6, further away = lower
        
        # Check if value is above acceptable range (very poor)
        if value > acceptable_max:
            # Value is beyond acceptable range - score 0
            return 0.0
        
        # Calculate distance from optimal boundary
        distance = value - optimal_max
        
        # Calculate maximum possible distance (from optimal_max to acceptable_max)
        max_distance = acceptable_max - optimal_max
        
        if max_distance <= 0:
            # No range above optimal, use a default penalty
            # Score decreases from 6 to 0 as distance increases
            return max(0.0, 6.0 - (distance * 6.0 / abs(optimal_max) if optimal_max != 0 else distance * 6.0))
        
        # Score decreases from 6 to 0 as distance increases
        # Linear interpolation: at optimal_max (distance=0) -> score=6, at acceptable_max (distance=max_distance) -> score=0
        ratio = 1.0 - (distance / max_distance)
        score = ratio * 6.0  # 0 to 6
        return max(0.0, min(6.0, score))


def calculate_suitability_scores(
    df: pd.DataFrame,
    thresholds: Dict[str, Any],
    property_weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Calculate suitability scores for all properties and final combined score.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with soil property columns (lon, lat, h3_index, soil_moisture, etc.)
    thresholds : Dict[str, Any]
        Full thresholds dictionary
    property_weights : Dict[str, float], optional
        Weights for each property. If None, uses equal weights (default: None)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with added score columns and final suitability_score
    """
    df = df.copy()
    
    # Property names to score (only the 4 with thresholds)
    properties_to_score = ['soil_moisture', 'soil_temperature', 'soil_organic_carbon', 'soil_pH']
    
    # Map property names to column name patterns (handle different naming conventions)
    property_column_patterns = {
        'soil_moisture': ['soil_moisture', 'sm_surface'],
        'soil_temperature': ['soil_temp', 'soil_temperature', 'soil_temp_layer1'],
        'soil_organic_carbon': ['soc', 'soil_organic_carbon'],
        'soil_pH': ['soil_ph', 'soil_pH']
    }
    
    # Find columns that match property names (handle resolution suffixes)
    def find_property_column(prop_name: str) -> Optional[str]:
        """Find column name that matches property name."""
        patterns = property_column_patterns.get(prop_name, [prop_name])
        
        # First try exact matches
        for pattern in patterns:
            if pattern in df.columns:
                return pattern
        
        # Then try columns that start with or contain the pattern (handles resolution suffixes)
        for col in df.columns:
            col_lower = col.lower()
            # Exclude score columns and coordinate columns
            if 'score' in col_lower or col_lower in ['lon', 'lat', 'h3_index']:
                continue
            
            # Check if column matches any pattern
            for pattern in patterns:
                pattern_lower = pattern.lower()
                # Check if column starts with pattern or contains it
                if col_lower.startswith(pattern_lower) or pattern_lower in col_lower:
                    return col
        
        return None
    
    # Calculate individual property scores
    score_columns = []
    for prop_name in properties_to_score:
        # Find the actual column name in the DataFrame
        column_name = find_property_column(prop_name)
        
        if column_name is None:
            # Property not found in DataFrame, skip
            print(f"  Warning: Column for {prop_name} not found in DataFrame")
            continue
        
        # Get thresholds for this property
        try:
            prop_thresholds = get_property_thresholds(thresholds, prop_name)
        except KeyError:
            # Property not in thresholds, skip
            continue
        
        # Calculate scores
        score_col_name = f"{prop_name}_score"
        df[score_col_name] = df[column_name].apply(
            lambda x: calculate_property_score(x, prop_thresholds)
        )
        score_columns.append(score_col_name)
    
    # Calculate final suitability score (weighted average)
    if not score_columns:
        # No scores calculated, return original DataFrame
        return df
    
    # Set default weights (equal weights)
    if property_weights is None:
        property_weights = {col: 1.0 for col in score_columns}
    
    # Normalize weights
    total_weight = sum(property_weights.get(col, 1.0) for col in score_columns)
    if total_weight > 0:
        normalized_weights = {col: property_weights.get(col, 1.0) / total_weight for col in score_columns}
    else:
        normalized_weights = {col: 1.0 / len(score_columns) for col in score_columns}
    
    # Calculate weighted average (only for rows with at least one valid score)
    def calculate_final_score(row):
        scores = [row[col] for col in score_columns if pd.notna(row[col])]
        weights = [normalized_weights[col] for col in score_columns if pd.notna(row[col])]
        
        if not scores:
            return np.nan
        
        # Normalize weights for available scores
        total_available_weight = sum(weights)
        if total_available_weight > 0:
            weights = [w / total_available_weight for w in weights]
        
        # Weighted average
        final_score = sum(s * w for s, w in zip(scores, weights))
        return min(10.0, max(0.0, final_score))  # Clamp to 0-10
    
    df['suitability_score'] = df.apply(calculate_final_score, axis=1)
    
    return df


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
            print(f"Warning: CSV file not found: {csv_file}")
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


def process_csv_files_with_suitability_scores(
    csv_dir: Path,
    thresholds_path: Optional[str] = None,
    output_csv: Optional[Path] = None,
    property_weights: Optional[Dict[str, float]] = None,
    pattern: str = "*.csv",
    lon_column: str = "lon",
    lat_column: str = "lat",
    dataframes: Optional[Dict[str, pd.DataFrame]] = None,
) -> pd.DataFrame:
    """
    Process tabular datasets by merging them and calculating suitability scores.
    
    If H3 indexes are available, aggregates data by hexagon regions (averages values per hexagon)
    before calculating scores. This creates one score per hexagon region instead of per point.
    
    Parameters
    ----------
    csv_dir : Path
        Directory containing CSV files (with optional H3 indexes)
    thresholds_path : str, optional
        Path to thresholds file (default: configs/thresholds.yaml)
    output_csv : Path, optional
        Path to save merged CSV with scores. If None, saves to csv_dir/suitability_scores.csv (default: None)
    property_weights : Dict[str, float], optional
        Weights for each property. If None, uses equal weights (default: None)
    pattern : str, optional
        File pattern to match (default: "*.csv")
    lon_column : str, optional
        Name of longitude column (default: "lon")
    lat_column : str, optional
        Name of latitude column (default: "lat")
    dataframes : Dict[str, pd.DataFrame], optional
        Optional mapping of dataset names to DataFrames. When provided, the function
        operates on these in-memory tables instead of loading CSV files from disk.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with suitability scores (one row per hexagon if H3 indexes available, otherwise one row per point)
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
                print(f"  Warning: DataFrame '{name}' is empty, skipping")
                continue
            if lon_column not in df.columns or lat_column not in df.columns:
                print(f"  Warning: DataFrame '{name}' missing coordinates, skipping")
                continue
            working = df.copy()
            working[lon_column] = working[lon_column].round(6)
            working[lat_column] = working[lat_column].round(6)
            loaded_frames.append(working)
            source_names.append(name)
            print(f"  Loaded '{name}': {len(working):,} rows, {len(working.columns)} columns")
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
                    print(f"  Warning: {csv_file.name} is empty, skipping")
                    continue
                if lon_column not in df.columns or lat_column not in df.columns:
                    print(f"  Warning: {csv_file.name} missing coordinates, skipping")
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
            print("  Warning: No numeric columns to aggregate")
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
            
            # Use hexagon-aggregated data for scoring
            data_for_scoring = hexagon_df
    else:
        print("\nNo H3 indexes found - scoring individual points...")
        data_for_scoring = merged_df
    
    # Load thresholds
    print("\nLoading thresholds...")
    thresholds = load_thresholds(thresholds_path)
    
    # Calculate suitability scores
    print("\nCalculating suitability scores...")
    scored_df = calculate_suitability_scores(
        df=data_for_scoring,
        thresholds=thresholds,
        property_weights=property_weights
    )
    
    # Save to output CSV
    if output_csv is None:
        output_csv = csv_dir / "suitability_scores.csv"
    
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    scored_df.to_csv(output_csv, index=False)
    
    # Get score columns that were actually created
    actual_score_columns = [col for col in scored_df.columns if 'score' in col.lower()]
    
    if 'suitability_score' in scored_df.columns:
        score_range = f"{scored_df['suitability_score'].min():.2f} - {scored_df['suitability_score'].max():.2f}"
    else:
        score_range = "N/A (no scores calculated)"
    
    print(f"""
Suitability scores calculated successfully
Output saved to: {output_csv}
Total rows: {len(scored_df):,}
Score columns: {actual_score_columns}
Suitability score range: {score_range}""")
    
    return scored_df


if __name__ == "__main__":
    """Debug and test suitability scoring."""
    import sys
    
    print("""============================================================
Suitability Score Calculator - Debug Mode
============================================================
    
------------------------------------------------------------
1. Testing calculate_property_score():
------------------------------------------------------------""")
    
    # Load thresholds
    try:
        thresholds = load_thresholds()
        print("PASS: Thresholds loaded successfully")
    except Exception as e:
        print(f"FAIL: Error loading thresholds: {type(e).__name__}: {e}")
        sys.exit(1)
    
    # Test scoring for each property
    test_cases = [
        ('soil_moisture', 0.2, "Optimal range"),
        ('soil_moisture', 0.05, "Below optimal (dry)"),
        ('soil_moisture', 0.5, "Above optimal (saturated)"),
        ('soil_temperature', 290.0, "Optimal range (17°C)"),
        ('soil_temperature', 275.0, "Below optimal (2°C)"),
        ('soil_organic_carbon', 100.0, "High organic matter"),
        ('soil_organic_carbon', 50.0, "Medium organic matter"),
        ('soil_pH', 6.5, "Optimal pH"),
        ('soil_pH', 4.5, "Below optimal pH"),
    ]
    
    for prop_name, value, description in test_cases:
        try:
            prop_thresholds = get_property_thresholds(thresholds, prop_name)
            score = calculate_property_score(value, prop_thresholds)
            print(f"""  PASS: {prop_name} = {value} ({description})
    Score: {score:.2f}""")
        except Exception as e:
            print(f"  FAIL: {prop_name} = {value}: {type(e).__name__}: {e}")
    
    # Test with actual CSV files if available
    print("""
------------------------------------------------------------
2. Testing with actual CSV files:
------------------------------------------------------------""")
    
    project_root = Path(__file__).parent.parent.parent
    csv_dir = project_root / "data" / "processed"
    
    if csv_dir.exists():
        csv_files = list(csv_dir.glob("*.csv"))
        if csv_files:
            print(f"  Found {len(csv_files)} CSV file(s) in {csv_dir}")
            print("  Testing suitability score calculation...")
            
            try:
                scored_df = process_csv_files_with_suitability_scores(
                    csv_dir=csv_dir,
                    output_csv=csv_dir / "suitability_scores_test.csv"
                )
                print(f"""  PASS: Successfully calculated suitability scores
    Output rows: {len(scored_df):,}
    Score columns: {[col for col in scored_df.columns if 'score' in col]}
    Sample scores:
{scored_df[['lon', 'lat', 'suitability_score']].head() if 'suitability_score' in scored_df.columns else 'No scores calculated'}""")
            except Exception as e:
                print(f"  FAIL: Error calculating scores: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  No CSV files found in {csv_dir}")
    else:
        print(f"  Directory not found: {csv_dir}")
    
    print("""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.analysis.suitability import process_csv_files_with_suitability_scores
  from pathlib import Path
  
  csv_dir = Path('data/processed')
  scored_df = process_csv_files_with_suitability_scores(csv_dir=csv_dir)
------------------------------------------------------------""")

