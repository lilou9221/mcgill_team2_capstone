"""
PyDeck Map Module

Creates interactive maps using PyDeck with H3 hexagons.
Simple, human-readable code that matches the Capstone reference format.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
import pydeck as pdk

from src.visualization.color_scheme import get_color_rgb


def create_pydeck_map(
    df: pd.DataFrame,
    output_path: Path,
    use_h3: bool = True,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6
) -> None:
    """
    Create interactive PyDeck map with suitability scores.
    
    Simple, human-readable code that matches the Capstone reference format.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with suitability scores (must have 'lon', 'lat', 'suitability_score')
    output_path : Path
        Path to save HTML file
    use_h3 : bool, optional
        Use H3 hexagons if available (default: True)
    center_lat : float, optional
        Center latitude for map (default: None, auto-calculated)
    center_lon : float, optional
        Center longitude for map (default: None, auto-calculated)
    zoom_start : int, optional
        Initial zoom level (default: 6)
    """
    # Calculate center if not provided
    if center_lat is None:
        center_lat = df['lat'].mean()
    if center_lon is None:
        center_lon = df['lon'].mean()
    
    # Check if H3 indexes are available
    has_h3 = use_h3 and 'h3_index' in df.columns
    
    if has_h3:
        # Create H3 hexagon layer
        hexagon_data = _prepare_hexagon_data(df)
        layer = _create_h3_hexagon_layer(hexagon_data)
    else:
        # Create point layer (fallback if no H3)
        point_data = _prepare_point_data(df)
        layer = _create_point_layer(point_data)
    
    # Create view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_start,
        pitch=0,  # 2D map, no pitch
        bearing=0
    )
    
    # Create tooltip
    # Note: PyDeck tooltips use {property} syntax, but format specifiers like .2f don't work
    # So we format the score in the data and use the formatted column
    # Check if property value is available for tooltip
    has_property_value = 'property_value' in df.columns or 'value_formatted' in df.columns
    
    # Determine tooltip template based on available columns
    # For H3 hexagons, value_formatted will be added in _prepare_hexagon_data if property_value exists
    # For points, we check directly in df
    if has_h3:
        # If property value exists, value_formatted will be created in _prepare_hexagon_data
        if has_property_value:
            tooltip = {
                'html': '''
                <b>Score:</b> {suitability_score_formatted}<br>
                <b>Value:</b> {value_formatted}<br>
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
                <b>Suitability Score:</b> {suitability_score_formatted}<br>
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
        # For points, check if value_formatted exists (will be added in _prepare_point_data)
        if has_property_value:
            # value_formatted will be created in _prepare_point_data
            tooltip = {
                'html': '''
                <b>Score:</b> {suitability_score_formatted}<br>
                <b>Value:</b> {value_formatted}<br>
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
                <b>Suitability Score:</b> {suitability_score_formatted}<br>
                <b>Location:</b> {lat_formatted}, {lon_formatted}<br>
                <b>Points:</b> {point_count}
                ''',
                'style': {
                    'backgroundColor': 'white',
                    'color': 'black'
                }
            }
    
    # Create deck with default Carto style background
    # Using default map_style (Carto's dark style) to test if background shows
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )
    
    # Save map
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(str(output_path))


def _prepare_hexagon_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare hexagon data for PyDeck H3HexagonLayer.
    
    Groups by H3 index and calculates aggregated values.
    Adds formatted coordinates and color information.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with H3 indexes and suitability scores
    
    Returns
    -------
    pd.DataFrame
        Prepared hexagon data
    """
    # Check if data is already aggregated (one row per h3_index)
    # If point_count column exists, use it; otherwise calculate it
    if 'point_count' in df.columns:
        # Data is already aggregated - group by h3_index and take first values
        hexagon_data = df.groupby('h3_index').agg({
            'suitability_score': 'first',
            'lat': 'first',
            'lon': 'first',
            'point_count': 'first'  # Preserve existing point_count
        }).reset_index()
    else:
        # Data is not aggregated - need to aggregate and count points
        hexagon_data = df.groupby('h3_index').agg({
            'suitability_score': 'mean',
            'lat': 'first',
            'lon': 'first'
        }).reset_index()
        
        # Count points per hexagon
        point_counts = df.groupby('h3_index').size().reset_index(name='point_count')
        hexagon_data = hexagon_data.merge(point_counts, on='h3_index')
    
    # Format coordinates for display
    hexagon_data['lat_formatted'] = hexagon_data['lat'].apply(lambda x: f"{x:.2f}")
    hexagon_data['lon_formatted'] = hexagon_data['lon'].apply(lambda x: f"{x:.2f}")
    
    # Format suitability score for tooltip display (2 decimal places)
    hexagon_data['suitability_score_formatted'] = hexagon_data['suitability_score'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    
    # Add property value to hexagon data if available
    if 'property_value' in df.columns:
        # Aggregate property value by hexagon (use mean)
        prop_values = df.groupby('h3_index')['property_value'].agg('mean').reset_index()
        prop_values.columns = ['h3_index', 'property_value']
        hexagon_data = hexagon_data.merge(prop_values, on='h3_index', how='left')
        # Format property value for tooltip
        hexagon_data['value_formatted'] = hexagon_data['property_value'].apply(
            lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
        )
    elif 'value_formatted' in df.columns:
        # If value_formatted already exists, aggregate it
        prop_values = df.groupby('h3_index')['value_formatted'].first().reset_index()
        hexagon_data = hexagon_data.merge(prop_values, on='h3_index', how='left')
    
    # Add color as RGBA array [R, G, B, A]
    def get_color_rgba(score):
        """Get RGBA color array for a suitability score."""
        r, g, b = get_color_rgb(score)
        return [r, g, b, 255]  # Full opacity
    
    hexagon_data['color'] = hexagon_data['suitability_score'].apply(get_color_rgba)
    
    print(f"  Prepared {len(hexagon_data):,} H3 hexagons")
    
    return hexagon_data


def _create_h3_hexagon_layer(hexagon_data: pd.DataFrame) -> pdk.Layer:
    """
    Create H3 hexagon layer for PyDeck.
    
    Uses H3HexagonLayer (not PolygonLayer) for better performance.
    
    Parameters
    ----------
    hexagon_data : pd.DataFrame
        Prepared hexagon data with h3_index, color, etc.
    
    Returns
    -------
    pdk.Layer
        PyDeck H3HexagonLayer
    """
    return pdk.Layer(
        'H3HexagonLayer',
        data=hexagon_data,
        get_hexagon='h3_index',
        get_fill_color='color',
        stroked=True,
        get_line_color=[0, 0, 0, 80],  # Black border with transparency
        line_width_min_pixels=1,
        pickable=True
    )


def _prepare_point_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare point data for PyDeck (fallback if no H3).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with coordinates and suitability scores
    
    Returns
    -------
    pd.DataFrame
        Prepared point data
    """
    point_data = df.copy()
    
    # Format coordinates for display
    point_data['lat_formatted'] = point_data['lat'].apply(lambda x: f"{x:.2f}")
    point_data['lon_formatted'] = point_data['lon'].apply(lambda x: f"{x:.2f}")
    
    # Format suitability score for tooltip display (2 decimal places)
    point_data['suitability_score_formatted'] = point_data['suitability_score'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    
    # Add property value to point data if available
    if 'property_value' in df.columns and 'value_formatted' not in point_data.columns:
        point_data['property_value'] = df['property_value']
        # Format property value for tooltip
        point_data['value_formatted'] = point_data['property_value'].apply(
            lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
        )
    elif 'value_formatted' in df.columns and 'value_formatted' not in point_data.columns:
        point_data['value_formatted'] = df['value_formatted']
    
    # Add point count (1 for each point)
    point_data['point_count'] = 1
    
    # Add color as RGBA array [R, G, B, A]
    def get_color_rgba(score):
        """Get RGBA color array for a suitability score."""
        r, g, b = get_color_rgb(score)
        return [r, g, b, 255]  # Full opacity
    
    point_data['color'] = point_data['suitability_score'].apply(get_color_rgba)
    
    print(f"  Prepared {len(point_data):,} points")
    
    return point_data


def _create_point_layer(point_data: pd.DataFrame) -> pdk.Layer:
    """
    Create point layer for PyDeck (fallback if no H3).
    
    Parameters
    ----------
    point_data : pd.DataFrame
        Prepared point data with coordinates, color, etc.
    
    Returns
    -------
    pdk.Layer
        PyDeck ScatterplotLayer
    """
    return pdk.Layer(
        'ScatterplotLayer',
        data=point_data,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius=100,  # Radius in meters
        radius_min_pixels=2,
        radius_max_pixels=10,
        pickable=True
    )
