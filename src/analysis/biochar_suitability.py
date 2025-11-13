"""
Biochar Suitability Calculator for DataFrames

Applies the new biochar suitability grading system to soil data DataFrames.
Converts data units and calculates biochar suitability scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from src.analysis.soil_quality_biochar import calculate_soil_quality_for_biochar


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
    
    # Search for matching column
    for col in df.columns:
        col_lower = col.lower()
        if 'score' in col_lower or col_lower in ['lon', 'lat', 'h3_index']:
            continue
        
        for pattern in patterns:
            if pattern in col_lower:
                return col
    
    return None


def calculate_biochar_suitability_scores(
    df: pd.DataFrame,
    moisture_column: Optional[str] = None,
    soc_column: Optional[str] = None,
    ph_column: Optional[str] = None,
    temp_column: Optional[str] = None
) -> pd.DataFrame:
    """
    Calculate biochar suitability scores for a DataFrame using the new grading system.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with soil property columns
    moisture_column : str, optional
        Name of moisture column (auto-detected if None)
    soc_column : str, optional
        Name of SOC column (auto-detected if None)
    ph_column : str, optional
        Name of pH column (auto-detected if None)
    temp_column : str, optional
        Name of temperature column (auto-detected if None)
    
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
    """
    df = df.copy()
    
    # Find property columns if not provided
    if moisture_column is None:
        moisture_column = find_property_column(df, 'moisture')
    if soc_column is None:
        soc_column = find_property_column(df, 'soc')
    if ph_column is None:
        ph_column = find_property_column(df, 'ph')
    if temp_column is None:
        temp_column = find_property_column(df, 'temperature')
    
    # Check if all required columns are found
    missing_cols = []
    if moisture_column is None:
        missing_cols.append('moisture')
    if soc_column is None:
        missing_cols.append('SOC')
    if ph_column is None:
        missing_cols.append('pH')
    if temp_column is None:
        missing_cols.append('temperature')
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Initialize result columns
    df['biochar_suitability_score'] = np.nan
    df['soil_quality_index'] = np.nan
    df['suitability_grade'] = ''
    df['color_hex'] = ''
    df['recommendation'] = ''
    
    # Individual property ratings and scores
    for prop in ['moisture', 'soc', 'ph', 'temperature']:
        df[f'property_ratings_{prop}'] = ''
        df[f'property_scores_{prop}'] = np.nan
    
    print(f"\nCalculating biochar suitability scores using new grading system...")
    print(f"  Moisture column: {moisture_column}")
    print(f"  SOC column: {soc_column}")
    print(f"  pH column: {ph_column}")
    print(f"  Temperature column: {temp_column}")
    
    # Process each row
    valid_count = 0
    invalid_count = 0
    
    for idx, row in df.iterrows():
        try:
            # Extract values
            moisture_val = row[moisture_column] if moisture_column else np.nan
            soc_val = row[soc_column] if soc_column else np.nan
            ph_val = row[ph_column] if ph_column else np.nan
            temp_val = row[temp_column] if temp_column else np.nan
            
            # Check which values are available
            has_moisture = not pd.isna(moisture_val)
            has_soc = not pd.isna(soc_val)
            has_ph = not pd.isna(ph_val)
            has_temp = not pd.isna(temp_val)
            
            # Need at least SOC and pH for basic calculation
            # If moisture is missing, use a default value (50% - moderate)
            # If temperature is missing, use a default value (20°C - good)
            if not has_soc or not has_ph:
                invalid_count += 1
                continue
            
            # Convert units with defaults for missing values
            if has_moisture:
                moisture_percent = convert_moisture_to_percent(moisture_val)
            else:
                # Use default moderate moisture (50%)
                moisture_percent = 50.0
            
            if has_soc:
                soc_percent = convert_soc_to_percent(soc_val)
            else:
                invalid_count += 1
                continue
            
            # pH: already in correct units
            if has_ph:
                ph_value = ph_val
            else:
                invalid_count += 1
                continue
            
            if has_temp:
                temp_celsius = convert_temperature_to_celsius(temp_val)
            else:
                # Use default moderate temperature (20°C - good)
                temp_celsius = 20.0
            
            # Calculate biochar suitability
            result = calculate_soil_quality_for_biochar(
                moisture=moisture_percent,
                soc=soc_percent,
                ph=ph_value,
                temp=temp_celsius
            )
            
            # Store results
            df.at[idx, 'biochar_suitability_score'] = result['biochar_suitability_score']
            df.at[idx, 'soil_quality_index'] = result['soil_quality_index']
            df.at[idx, 'suitability_grade'] = result['suitability_grade']
            df.at[idx, 'color_hex'] = result['color_hex']
            df.at[idx, 'recommendation'] = result['recommendation']
            
            # Store property ratings and scores
            df.at[idx, 'property_ratings_moisture'] = result['property_ratings']['moisture']
            df.at[idx, 'property_ratings_soc'] = result['property_ratings']['soc']
            df.at[idx, 'property_ratings_ph'] = result['property_ratings']['ph']
            df.at[idx, 'property_ratings_temperature'] = result['property_ratings']['temperature']
            
            df.at[idx, 'property_scores_moisture'] = result['property_scores']['moisture']
            df.at[idx, 'property_scores_soc'] = result['property_scores']['soc']
            df.at[idx, 'property_scores_ph'] = result['property_scores']['ph']
            df.at[idx, 'property_scores_temperature'] = result['property_scores']['temperature']
            
            valid_count += 1
            
        except (ValueError, KeyError, TypeError) as e:
            # Skip invalid rows
            invalid_count += 1
            continue
    
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

