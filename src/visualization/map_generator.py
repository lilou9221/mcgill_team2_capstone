"""
Map Generator Module

Creates interactive maps with suitability scores.
Tries Folium first, falls back to PyDeck if file size > 100MB.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from src.visualization.color_scheme import get_color_for_score, get_color_scheme_info
from src.visualization.folium_map import create_folium_map
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

