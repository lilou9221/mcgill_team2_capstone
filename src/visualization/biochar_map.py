"""
Biochar Suitability Map Generator

Creates interactive maps with biochar suitability scores using the new grading system.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import pydeck as pdk

from src.visualization.color_scheme import get_biochar_suitability_color_rgb


def create_biochar_suitability_map(
    df: pd.DataFrame,
    output_path: Path,
    max_file_size_mb: float = 100.0,
    use_h3: bool = True,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6
) -> dict:
    """
    Create interactive biochar suitability map using the new grading system.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with biochar suitability scores (must have 'lon', 'lat', 'biochar_suitability_score')
    output_path : Path
        Path to save HTML file
    max_file_size_mb : float, optional
        Maximum file size in MB (default: 100.0)
    use_h3 : bool, optional
        Use H3 hexagons if available (default: True)
    center_lat : float, optional
        Center latitude for map (default: None, auto-calculated)
    center_lon : float, optional
        Center longitude for map (default: None, auto-calculated)
    zoom_start : int, optional
        Initial zoom level (default: 6)
    
    Returns
    -------
    dict
        Map generation info with keys: 'method', 'file_size_mb', 'file_path'
    """
    # Validate required columns
    required_cols = ['lon', 'lat', 'biochar_suitability_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Filter out NaN scores
    df = df.dropna(subset=['biochar_suitability_score']).copy()
    
    if df.empty:
        raise ValueError("No valid biochar suitability scores found in DataFrame")
    
    # Calculate center if not provided
    if center_lat is None:
        center_lat = df['lat'].mean()
    if center_lon is None:
        center_lon = df['lon'].mean()
    
    # Check if H3 indexes are available
    has_h3 = use_h3 and 'h3_index' in df.columns
    
    print(f"\nCreating biochar suitability map with PyDeck...")
    print(f"  Data points: {len(df):,}")
    print(f"  Using H3 hexagons: {has_h3}")
    
    # Prepare data
    if has_h3:
        hexagon_data = _prepare_biochar_hexagon_data(df)
        layer = _create_biochar_h3_hexagon_layer(hexagon_data)
    else:
        point_data = _prepare_biochar_point_data(df)
        layer = _create_biochar_point_layer(point_data)
    
    # Create view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_start,
        pitch=0,
        bearing=0
    )
    
    # Create tooltip
    if has_h3:
        tooltip = {
            'html': '''
            <b>Biochar Suitability:</b> {biochar_suitability_score_formatted}<br>
            <b>Grade:</b> {suitability_grade}<br>
            <b>H3 Index:</b> {h3_index}<br>
            <b>Location:</b> {lat_formatted}, {lon_formatted}<br>
            <b>Points:</b> {point_count}
            ''',
            'style': {
                'backgroundColor': 'white',
                'color': 'black'
            }
        }
    else:
        tooltip = {
            'html': '''
            <b>Biochar Suitability:</b> {biochar_suitability_score_formatted}<br>
            <b>Grade:</b> {suitability_grade}<br>
            <b>Location:</b> {lat_formatted}, {lon_formatted}
            ''',
            'style': {
                'backgroundColor': 'white',
                'color': 'black'
            }
        }
    
    # Create deck
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )
    
    # Save map
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(str(output_path))
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Biochar suitability map created: {file_size_mb:.2f} MB")
    
    return {
        'method': 'pydeck',
        'file_size_mb': file_size_mb,
        'file_path': output_path
    }


def _prepare_biochar_hexagon_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare hexagon data for biochar suitability map."""
    # Check if data is already aggregated
    if 'point_count' in df.columns:
        hexagon_data = df.groupby('h3_index').agg({
            'biochar_suitability_score': 'first',
            'suitability_grade': 'first',
            'lat': 'first',
            'lon': 'first',
            'point_count': 'first'
        }).reset_index()
    else:
        hexagon_data = df.groupby('h3_index').agg({
            'biochar_suitability_score': 'mean',
            'suitability_grade': lambda x: x.mode()[0] if len(x.mode()) > 0 else '',
            'lat': 'first',
            'lon': 'first'
        }).reset_index()
        
        point_counts = df.groupby('h3_index').size().reset_index(name='point_count')
        hexagon_data = hexagon_data.merge(point_counts, on='h3_index')
    
    # Format values for tooltip
    hexagon_data['lat_formatted'] = hexagon_data['lat'].apply(lambda x: f"{x:.2f}")
    hexagon_data['lon_formatted'] = hexagon_data['lon'].apply(lambda x: f"{x:.2f}")
    hexagon_data['biochar_suitability_score_formatted'] = hexagon_data['biochar_suitability_score'].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    
    # Add color as RGBA array
    def get_color_rgba(score):
        """Get RGBA color array for biochar suitability score."""
        r, g, b = get_biochar_suitability_color_rgb(score)
        return [r, g, b, 255]  # Full opacity
    
    hexagon_data['color'] = hexagon_data['biochar_suitability_score'].apply(get_color_rgba)
    
    # Ensure suitability_grade is string
    hexagon_data['suitability_grade'] = hexagon_data['suitability_grade'].fillna('').astype(str)
    
    print(f"  Prepared {len(hexagon_data):,} H3 hexagons")
    return hexagon_data


def _prepare_biochar_point_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare point data for biochar suitability map."""
    point_data = df[['lon', 'lat', 'biochar_suitability_score', 'suitability_grade']].copy()
    
    # Format values for tooltip
    point_data['lat_formatted'] = point_data['lat'].apply(lambda x: f"{x:.2f}")
    point_data['lon_formatted'] = point_data['lon'].apply(lambda x: f"{x:.2f}")
    point_data['biochar_suitability_score_formatted'] = point_data['biochar_suitability_score'].apply(
        lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
    )
    
    # Add color as RGBA array
    def get_color_rgba(score):
        """Get RGBA color array for biochar suitability score."""
        r, g, b = get_biochar_suitability_color_rgb(score)
        return [r, g, b, 255]  # Full opacity
    
    point_data['color'] = point_data['biochar_suitability_score'].apply(get_color_rgba)
    
    # Ensure suitability_grade is string
    point_data['suitability_grade'] = point_data['suitability_grade'].fillna('').astype(str)
    
    print(f"  Prepared {len(point_data):,} points")
    return point_data


def _create_biochar_h3_hexagon_layer(hexagon_data: pd.DataFrame) -> pdk.Layer:
    """Create H3 hexagon layer for biochar suitability map."""
    return pdk.Layer(
        'H3HexagonLayer',
        data=hexagon_data,
        get_hexagon='h3_index',
        get_fill_color='color',
        get_line_color=[255, 255, 255, 200],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        extruded=False
    )


def _create_biochar_point_layer(point_data: pd.DataFrame) -> pdk.Layer:
    """Create point layer for biochar suitability map."""
    return pdk.Layer(
        'ScatterplotLayer',
        data=point_data,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius=100,
        pickable=True,
        auto_highlight=True
    )

