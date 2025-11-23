"""
Biochar Suitability Calculator for DataFrames

Applies the new biochar suitability grading system to soil data DataFrames.
Converts data units and calculates biochar suitability scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

from src.analyzers.soil_quality_biochar import calculate_soil_quality_for_biochar


def convert_moisture_to_percent(moisture_m3_m3: float) -> float:
    """
    Convert soil moisture from m³/m³ (volume fraction) to percentage.
    
    Parameters
    ----------
    moisture_m3_m3 : float
        Soil moisture in m³/m³ (0-0.9 range)
    
    Returns
    -------
    float
        Soil moisture as percentage (0-100)
    """
    if pd.isna(moisture_m3_m3):
        return np.nan
    # Convert volume fraction to percentage
    return moisture_m3_m3 * 100.0


def convert_soc_to_percent(soc_g_kg: float) -> float:
    """
    Convert soil organic carbon from g/kg to percentage.
    
    Parameters
    ----------
    soc_g_kg : float
        SOC in g/kg
    
    Returns
    -------
    float
        SOC as percentage
    """
    if pd.isna(soc_g_kg):
        return np.nan
    # Convert g/kg to percentage (divide by 10)
    return soc_g_kg / 10.0


def convert_temperature_to_celsius(temp_kelvin: float) -> float:
    """
    Convert soil temperature from Kelvin to Celsius.
    
    Parameters
    ----------
    temp_kelvin : float
        Temperature in Kelvin
    
    Returns
    -------
    float
        Temperature in Celsius
    """
    if pd.isna(temp_kelvin):
        return np.nan
    # Convert Kelvin to Celsius
    return temp_kelvin - 273.15


def find_property_column(df: pd.DataFrame, property_name: str) -> Optional[str]:
    """
    Find the column name for a property in the DataFrame.
    
    For SOC and pH, prefers b0 layer, but will use b10 if b0 is not available.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with soil properties
    property_name : str
        Property name to find ('moisture', 'soc', 'ph', 'temperature')
    
    Returns
    -------
    str or None
        Column name if found, None otherwise
    """
    property_patterns = {
        'moisture': ['moisture', 'sm_surface'],
        'soc': ['soc', 'soil_organic_carbon', 'soil_organic'],
        'ph': ['ph', 'soil_ph', 'soil_pH'],
        'temperature': ['temp', 'temperature', 'soil_temp', 'soil_temperature']
    }
    
    patterns = property_patterns.get(property_name.lower(), [property_name.lower()])
    
    # For SOC and pH, prefer b0 over b10
    matching_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if 'score' in col_lower or col_lower in ['lon', 'lat', 'h3_index']:
            continue
        
        for pattern in patterns:
            if pattern in col_lower:
                matching_cols.append(col)
                break
    
    if not matching_cols:
        return None
    
    # For SOC and pH, prefer b0 over b10
    if property_name.lower() in ['soc', 'ph']:
        # First try to find b0
        for col in matching_cols:
            if '_b0' in col.lower():
                return col
        # If no b0, use b10
        for col in matching_cols:
            if '_b10' in col.lower():
                return col
        # If neither b0 nor b10, return first match
        return matching_cols[0]
    
    # For other properties, return first match
    return matching_cols[0]


def find_property_columns_with_depth(df: pd.DataFrame, property_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Find both b0 and b10 column names for SOC or pH properties.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with soil properties
    property_name : str
        Property name to find ('soc' or 'ph')
    
    Returns
    -------
    tuple[str or None, str or None]
        (b0_column, b10_column) - returns (None, None) if neither found
    """
    if property_name.lower() not in ['soc', 'ph']:
        return None, None
    
    property_patterns = {
        'soc': ['soc', 'soil_organic_carbon', 'soil_organic'],
        'ph': ['ph', 'soil_ph', 'soil_pH']
    }
    
    patterns = property_patterns.get(property_name.lower(), [])
    b0_col = None
    b10_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'score' in col_lower or col_lower in ['lon', 'lat', 'h3_index']:
            continue
        
        for pattern in patterns:
            if pattern in col_lower:
                if '_b0' in col_lower:
                    b0_col = col
                elif '_b10' in col_lower:
                    b10_col = col
                break
    
    return b0_col, b10_col


def calculate_biochar_suitability_scores(
    df: pd.DataFrame,
    moisture_column: Optional[str] = None,
    soc_column: Optional[str] = None,
    ph_column: Optional[str] = None,
    temp_column: Optional[str] = None
) -> pd.DataFrame:
    """
    Calculate biochar suitability scores for a DataFrame using the new grading system.
    
    For SOC and pH properties, automatically detects and averages both b0 (surface) 
    and b10 (10cm depth) layers when both are available. This provides a more 
    representative soil profile assessment than using a single depth layer.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with soil property columns. Should contain columns for SOC and pH
        with b0 and/or b10 depth layers (e.g., 'SOC_res_250_b0 (g/kg)', 
        'SOC_res_250_b10 (g/kg)').
    moisture_column : str, optional
        Name of moisture column (auto-detected if None). Looks for columns containing
        'moisture' or 'sm_surface'.
    soc_column : str, optional
        Name of SOC column (auto-detected if None). If both b0 and b10 columns are
        found, they will be averaged. Otherwise uses the available column.
    ph_column : str, optional
        Name of pH column (auto-detected if None). If both b0 and b10 columns are
        found, they will be averaged. Otherwise uses the available column.
    temp_column : str, optional
        Name of temperature column (auto-detected if None). Looks for columns 
        containing 'temp' or 'temperature'.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with added biochar suitability columns:
        - biochar_suitability_score: float (0-100)
        - soil_quality_index: float (0-100)
        - suitability_grade: str
        - color_hex: str
        - recommendation: str
        - property_ratings_*: individual property ratings
        - property_scores_*: individual property scores
    
    Notes
    -----
    - SOC and pH values are averaged from b0 and b10 layers when both are available
    - If only one layer (b0 or b10) is available, that layer is used
    - Processing is done in chunks (10k rows) to manage memory for large datasets
    - Missing moisture or temperature values use defaults (50% moisture, 20°C temp)
    - SOC and pH are required - rows with missing values are excluded from scoring
    """
    # Find property columns if not provided
    if moisture_column is None:
        moisture_column = find_property_column(df, 'moisture')
    if temp_column is None:
        temp_column = find_property_column(df, 'temperature')
    
    # For SOC and pH, find both b0 and b10 columns
    if soc_column is None:
        soc_b0_col, soc_b10_col = find_property_columns_with_depth(df, 'soc')
    else:
        # If explicitly provided, treat as single column (no depth averaging)
        soc_b0_col, soc_b10_col = soc_column, None
    
    if ph_column is None:
        ph_b0_col, ph_b10_col = find_property_columns_with_depth(df, 'ph')
    else:
        # If explicitly provided, treat as single column (no depth averaging)
        ph_b0_col, ph_b10_col = ph_column, None
    
    # Check if all required columns are found
    missing_cols = []
    if moisture_column is None:
        missing_cols.append('moisture')
    if not soc_b0_col and not soc_b10_col:
        missing_cols.append('SOC')
    if not ph_b0_col and not ph_b10_col:
        missing_cols.append('pH')
    if temp_column is None:
        missing_cols.append('temperature')
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Set fallback columns for single-column case (used in else branches)
    soc_column = soc_b0_col if soc_b0_col else soc_b10_col
    ph_column = ph_b0_col if ph_b0_col else ph_b10_col
    
    print(f"\nCalculating biochar suitability scores using new grading system...")
    print(f"  Moisture column: {moisture_column}")
    if soc_b0_col and soc_b10_col:
        print(f"  SOC columns: {soc_b0_col} and {soc_b10_col} (averaging b0 and b10)")
    elif soc_b0_col:
        print(f"  SOC column: {soc_b0_col} (b0 layer)")
    elif soc_b10_col:
        print(f"  SOC column: {soc_b10_col} (b10 layer)")
    else:
        print(f"  SOC column: {soc_column}")
    
    if ph_b0_col and ph_b10_col:
        print(f"  pH columns: {ph_b0_col} and {ph_b10_col} (averaging b0 and b10)")
    elif ph_b0_col:
        print(f"  pH column: {ph_b0_col} (b0 layer)")
    elif ph_b10_col:
        print(f"  pH column: {ph_b10_col} (b10 layer)")
    else:
        print(f"  pH column: {ph_column}")
    print(f"  Temperature column: {temp_column}")
    
    # Vectorized unit conversions with defaults (avoid unnecessary copies)
    # Convert moisture: m³/m³ to percentage, default 50% if missing
    moisture_percent = df[moisture_column].apply(
        lambda x: convert_moisture_to_percent(x) if pd.notna(x) else 50.0
    )
    
    # Convert SOC: g/kg to percentage, average b0 and b10 if both available
    if soc_b0_col and soc_b10_col:
        # Average b0 and b10 layers using vectorized operations
        soc_b0_percent = df[soc_b0_col].apply(
            lambda x: convert_soc_to_percent(x) if pd.notna(x) else np.nan
        )
        soc_b10_percent = df[soc_b10_col].apply(
            lambda x: convert_soc_to_percent(x) if pd.notna(x) else np.nan
        )
        # Average where both are available, use available one if only one exists
        # Vectorized: combine both series, average where both valid
        soc_percent = soc_b0_percent.combine_first(soc_b10_percent)
        # Where both are valid, use average
        both_valid = pd.notna(soc_b0_percent) & pd.notna(soc_b10_percent)
        soc_percent[both_valid] = (soc_b0_percent[both_valid] + soc_b10_percent[both_valid]) / 2.0
    else:
        # Use single column (b0 or b10)
        soc_percent = df[soc_column].apply(
            lambda x: convert_soc_to_percent(x) if pd.notna(x) else np.nan
        )
    
    # pH: average b0 and b10 if both available, already in correct units
    if ph_b0_col and ph_b10_col:
        # Average b0 and b10 layers using vectorized operations
        ph_b0_series = df[ph_b0_col]
        ph_b10_series = df[ph_b10_col]
        # Average where both are available, use available one if only one exists
        # Vectorized: combine both series, average where both valid
        ph_series = ph_b0_series.combine_first(ph_b10_series)
        # Where both are valid, use average
        both_valid = pd.notna(ph_b0_series) & pd.notna(ph_b10_series)
        ph_series[both_valid] = (ph_b0_series[both_valid] + ph_b10_series[both_valid]) / 2.0
    else:
        # Use single column (b0 or b10)
        ph_series = df[ph_column]
    
    # Convert temperature: Kelvin to Celsius, default 20°C if missing
    temp_celsius = df[temp_column].apply(
        lambda x: convert_temperature_to_celsius(x) if pd.notna(x) else 20.0
    )
    
    # Filter rows: need SOC and pH (both required)
    valid_mask = pd.notna(soc_percent) & pd.notna(ph_series)
    valid_count = valid_mask.sum()
    invalid_count = (~valid_mask).sum()
    
    if valid_count == 0:
        print("  No valid rows found (missing SOC or pH data)")
        # Return DataFrame with NaN scores
        result_cols = {
            'biochar_suitability_score': np.nan,
            'soil_quality_index': np.nan,
            'suitability_grade': '',
            'color_hex': '',
            'recommendation': ''
        }
        for prop in ['moisture', 'soc', 'ph', 'temperature']:
            result_cols[f'property_ratings_{prop}'] = ''
            result_cols[f'property_scores_{prop}'] = np.nan
        
        for col, default_val in result_cols.items():
            df[col] = default_val
        return df
    
    # Initialize result columns with NaN/empty defaults
    df['biochar_suitability_score'] = np.nan
    df['soil_quality_index'] = np.nan
    df['suitability_grade'] = ''
    df['color_hex'] = ''
    df['recommendation'] = ''
    
    for prop in ['moisture', 'soc', 'ph', 'temperature']:
        df[f'property_ratings_{prop}'] = ''
        df[f'property_scores_{prop}'] = np.nan
    
    # Process in chunks to reduce memory usage for large datasets
    # Only process valid rows
    valid_indices = df.index[valid_mask]
    chunk_size = 10000  # Process 10k rows at a time to limit memory usage
    
    # Prepare input arrays for vectorized processing
    valid_moisture = moisture_percent[valid_mask].values
    valid_soc = soc_percent[valid_mask].values
    valid_ph = ph_series[valid_mask].values
    valid_temp = temp_celsius[valid_mask].values
    
    # Process in chunks to avoid loading all results into memory at once
    num_chunks = (len(valid_indices) + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min((chunk_idx + 1) * chunk_size, len(valid_indices))
        chunk_indices = valid_indices[start_idx:end_idx]
        
        # Calculate results for this chunk
        chunk_results = [
            calculate_soil_quality_for_biochar(
                moisture=valid_moisture[i],
                soc=valid_soc[i],
                ph=valid_ph[i],
                temp=valid_temp[i]
            )
            for i in range(start_idx, end_idx)
        ]
        
        # Assign results to DataFrame immediately (frees chunk_results memory)
        df.loc[chunk_indices, 'biochar_suitability_score'] = [r['biochar_suitability_score'] for r in chunk_results]
        df.loc[chunk_indices, 'soil_quality_index'] = [r['soil_quality_index'] for r in chunk_results]
        df.loc[chunk_indices, 'suitability_grade'] = [r['suitability_grade'] for r in chunk_results]
        df.loc[chunk_indices, 'color_hex'] = [r['color_hex'] for r in chunk_results]
        df.loc[chunk_indices, 'recommendation'] = [r['recommendation'] for r in chunk_results]
        
        # Assign property ratings and scores
        for prop in ['moisture', 'soc', 'ph', 'temperature']:
            df.loc[chunk_indices, f'property_ratings_{prop}'] = [r['property_ratings'][prop] for r in chunk_results]
            df.loc[chunk_indices, f'property_scores_{prop}'] = [r['property_scores'][prop] for r in chunk_results]
        
        # Free chunk memory
        del chunk_results
        
        if num_chunks > 1 and (chunk_idx + 1) % 10 == 0:
            print(f"  Processed {chunk_idx + 1}/{num_chunks} chunks...")
    
    print(f"  Calculated scores for {valid_count:,} rows")
    if invalid_count > 0:
        print(f"  Skipped {invalid_count:,} rows with invalid/missing data")
    
    # Report score statistics
    valid_scores = df['biochar_suitability_score'].dropna()
    if len(valid_scores) > 0:
        print(f"\nBiochar Suitability Score Statistics:")
        print(f"  Range: {valid_scores.min():.2f} - {valid_scores.max():.2f}")
        print(f"  Mean: {valid_scores.mean():.2f}")
        
        # Count by grade
        grades = df['suitability_grade'].value_counts()
        print(f"\nSuitability Grades:")
        for grade, count in grades.items():
            if grade:
                print(f"  {grade}: {count:,} ({count/len(valid_scores)*100:.1f}%)")
    
    return df

