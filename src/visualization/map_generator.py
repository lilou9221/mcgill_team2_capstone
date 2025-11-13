"""
Map Generator Module

Creates interactive maps with suitability scores.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from src.visualization.color_scheme import (
    get_color_for_biochar_suitability,
    get_biochar_suitability_color_rgb
)
from src.visualization.pydeck_map import create_pydeck_map


def create_suitability_map(
    df: pd.DataFrame,
    output_path: Path,
    max_file_size_mb: float = 100.0,
    use_h3: bool = True,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6,
    prefer_pydeck: bool = True  # Prefer PyDeck for H3 hexagons (matches Capstone format)
) -> Dict[str, Any]:
    """
    Create interactive suitability map.
    
    Uses PyDeck for H3 hexagons (matches Capstone format), 
    falls back to Folium for points or if PyDeck fails.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with suitability scores (must have 'lon', 'lat', 'suitability_score')
    output_path : Path
        Path to save HTML file
    max_file_size_mb : float, optional
        Maximum file size in MB before switching to PyDeck (default: 100.0)
    use_h3 : bool, optional
        Use H3 hexagons if available (default: True)
    center_lat : float, optional
        Center latitude for map (default: None, auto-calculated)
    center_lon : float, optional
        Center longitude for map (default: None, auto-calculated)
    zoom_start : int, optional
        Initial zoom level (default: 6)
    prefer_pydeck : bool, optional
        Prefer PyDeck for H3 hexagons (default: True, matches Capstone format)
    
    Returns
    -------
    dict
        Map generation info with keys: 'method', 'file_size_mb', 'file_path'
    """
    # Validate required columns
    required_cols = ['lon', 'lat', 'suitability_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Filter out NaN scores
    df = df.dropna(subset=['suitability_score']).copy()
    
    if df.empty:
        raise ValueError("No valid suitability scores found in DataFrame")
    
    # Calculate center if not provided
    if center_lat is None:
        center_lat = df['lat'].mean()
    if center_lon is None:
        center_lon = df['lon'].mean()
    
    # Check if H3 indexes are available
    has_h3 = use_h3 and 'h3_index' in df.columns
    
    # Prefer PyDeck for H3 hexagons (matches Capstone format)
    if has_h3 and prefer_pydeck:
        print(f"\nCreating map with PyDeck (H3 hexagons)...")
        print(f"  Data points: {len(df):,}")
        print(f"  Using H3 hexagons: {has_h3}")
        
        try:
            # Create PyDeck map
            create_pydeck_map(
                df=df,
                output_path=output_path,
                use_h3=has_h3,
                center_lat=center_lat,
                center_lon=center_lon,
                zoom_start=zoom_start
            )
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  PyDeck map created: {file_size_mb:.2f} MB")
            
            return {
                'method': 'pydeck',
                'file_size_mb': file_size_mb,
                'file_path': output_path
            }
        except Exception as e:
            print(f"  Error creating PyDeck map: {e}")
            print(f"  Falling back to Folium...")
            # Continue to Folium fallback
    
    # Try Folium (for points or as fallback)
    print(f"\nCreating map with Folium...")
    print(f"  Data points: {len(df):,}")
    print(f"  Using H3 hexagons: {has_h3}")
    
    try:
        # Create Folium map
        folium_path = output_path.parent / f"{output_path.stem}_folium.html"
        create_folium_map(
            df=df,
            output_path=folium_path,
            use_h3=has_h3,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom_start=zoom_start
        )
        
        # Check file size
        file_size_mb = folium_path.stat().st_size / (1024 * 1024)
        print(f"  Folium map created: {file_size_mb:.2f} MB")
        
        if file_size_mb > max_file_size_mb:
            print(f"  File size ({file_size_mb:.2f} MB) exceeds limit ({max_file_size_mb} MB)")
            print(f"  Switching to PyDeck...")
            
            # Delete Folium map and create PyDeck map
            folium_path.unlink()
            
            # Create PyDeck map
            create_pydeck_map(
                df=df,
                output_path=output_path,
                use_h3=has_h3,
                center_lat=center_lat,
                center_lon=center_lon,
                zoom_start=zoom_start
            )
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  PyDeck map created: {file_size_mb:.2f} MB")
            
            return {
                'method': 'pydeck',
                'file_size_mb': file_size_mb,
                'file_path': output_path
            }
        else:
            # Rename to final output path
            folium_path.rename(output_path)
            
            return {
                'method': 'folium',
                'file_size_mb': file_size_mb,
                'file_path': output_path
            }
    
    except Exception as e:
        print(f"  Error creating Folium map: {e}")
        print(f"  Falling back to PyDeck...")
        
        # Create PyDeck map
        create_pydeck_map(
            df=df,
            output_path=output_path,
            use_h3=has_h3,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom_start=zoom_start
        )
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  PyDeck map created: {file_size_mb:.2f} MB")
        
        return {
            'method': 'pydeck',
            'file_size_mb': file_size_mb,
            'file_path': output_path
        }


def create_property_map(
    df: pd.DataFrame,
    property_name: str,
    output_path: Path,
    property_column_pattern: Optional[str] = None,
    score_column: Optional[str] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6,
    use_h3: bool = True
) -> Dict[str, Any]:
    """
    Create an interactive map for a specific property (e.g., SOC, pH, moisture).
    
    Uses the property score to apply the color scheme.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with property data and scores
    property_name : str
        Name of the property (e.g., 'SOC', 'pH', 'moisture')
    output_path : Path
        Path to save HTML file
    property_column_pattern : str, optional
        Pattern to find the property column (e.g., 'SOC_res_250_b0', 'soil_pH_res_250_b0')
        If None, will try to find automatically
    score_column : str, optional
        Name of the score column (e.g., 'soil_organic_carbon_score', 'soil_pH_score')
        If None, will try to find automatically
    center_lat : float, optional
        Center latitude for map (default: None, auto-calculated)
    center_lon : float, optional
        Center longitude for map (default: None, auto-calculated)
    zoom_start : int, optional
        Initial zoom level (default: 6)
    use_h3 : bool, optional
        Use H3 hexagons if available (default: True)
    
    Returns
    -------
    dict
        Map generation info with keys: 'method', 'file_size_mb', 'file_path'
    """
    # Find property column if not provided
    if property_column_pattern is None:
        # Try to find column matching property name
        property_columns = [col for col in df.columns 
                          if property_name.lower() in col.lower() 
                          and 'score' not in col.lower()
                          and col.lower() not in ['lon', 'lat', 'h3_index']]
        if property_columns:
            property_column_pattern = property_columns[0]
        else:
            raise ValueError(f"Could not find property column for {property_name}")
    
    # Find score column if not provided
    if score_column is None:
        score_column_options = [
            f"{property_name}_score",
            f"soil_{property_name}_score",
            f"soil_organic_carbon_score" if "SOC" in property_name or "carbon" in property_name.lower() else None,
            f"soil_pH_score" if "pH" in property_name or "ph" in property_name.lower() else None,
            f"soil_moisture_score" if "moisture" in property_name.lower() else None
        ]
        score_column_options = [col for col in score_column_options if col and col in df.columns]
        if score_column_options:
            score_column = score_column_options[0]
        else:
            raise ValueError(f"Could not find score column for {property_name}")
    
    # Check if columns exist
    if property_column_pattern not in df.columns:
        raise ValueError(f"Property column '{property_column_pattern}' not found in DataFrame")
    if score_column not in df.columns:
        raise ValueError(f"Score column '{score_column}' not found in DataFrame")
    
    # Create DataFrame with required columns
    map_df = pd.DataFrame({
        'lon': df['lon'],
        'lat': df['lat'],
        'property_value': df[property_column_pattern],
        'score': df[score_column]
    })
    
    # Add H3 index if available
    if 'h3_index' in df.columns:
        map_df['h3_index'] = df['h3_index']
    
    # Filter out NaN scores
    map_df = map_df.dropna(subset=['score']).copy()
    
    if map_df.empty:
        raise ValueError(f"No valid scores found for {property_name}")
    
    # Rename score column to 'suitability_score' for compatibility with existing map functions
    map_df['suitability_score'] = map_df['score']
    
    # Format property value for tooltip
    map_df['value_formatted'] = map_df['property_value'].apply(
        lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
    )
    
    # Calculate center if not provided
    if center_lat is None:
        center_lat = map_df['lat'].mean()
    if center_lon is None:
        center_lon = map_df['lon'].mean()
    
    # Create map using existing function
    return create_suitability_map(
        df=map_df,
        output_path=output_path,
        max_file_size_mb=100.0,
        use_h3=use_h3,
        center_lat=center_lat,
        center_lon=center_lon,
        zoom_start=zoom_start,
        prefer_pydeck=True
    )


