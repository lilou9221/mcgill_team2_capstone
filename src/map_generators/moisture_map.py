"""
Soil Moisture Map Generator

Creates interactive maps showing soil moisture values aggregated by H3 hexagons.
Soil moisture is displayed as percentage (0-100%).
"""

from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import numpy as np
import pydeck as pdk

from src.data_processors.raster_to_csv import raster_to_dataframe
from src.data_processors.h3_converter import add_h3_to_dataframe


def get_moisture_color_rgb(moisture_value: float, min_moisture: float, max_moisture: float) -> tuple:
    """
    Get RGB color for soil moisture value using a sequential color scheme (dry to wet).
    
    Color mapping:
    - Light brown/yellow for dry soils (low moisture)
    - Green for moderate moisture
    - Blue for wet soils (high moisture)
    
    Parameters
    ----------
    moisture_value : float
        Soil moisture percentage (0-100)
    min_moisture : float
        Minimum moisture value for color range (absolute: 0.0 %)
    max_moisture : float
        Maximum moisture value for color range (absolute: 100.0 %)
    
    Returns
    -------
    tuple
        RGB color tuple (r, g, b) with values 0-255
    """
    if np.isnan(moisture_value) or min_moisture == max_moisture:
        return (128, 128, 128)  # Gray for NaN or constant values
    
    # Normalize to 0-1 range
    normalized = (moisture_value - min_moisture) / (max_moisture - min_moisture)
    normalized = max(0.0, min(1.0, normalized))  # Clamp to [0, 1]
    
    # Sequential color scheme: light brown (#D2B48C) to green (#228B22) to blue (#4169E1)
    # Interpolate through: brown -> yellow-green -> green -> blue-green -> blue
    if normalized < 0.33:
        # Light brown to yellow-green
        ratio = normalized / 0.33  # 0 to 1
        r = int(210 - (210 - 173) * ratio)  # 210 -> 173
        g = int(180 - (180 - 255) * ratio)  # 180 -> 255
        b = int(140 - (140 - 47) * ratio)   # 140 -> 47
    elif normalized < 0.67:
        # Yellow-green to green
        ratio = (normalized - 0.33) / 0.34  # 0 to 1
        r = int(173 - (173 - 34) * ratio)   # 173 -> 34
        g = int(255 - (255 - 139) * ratio)  # 255 -> 139
        b = int(47 - (47 - 34) * ratio)     # 47 -> 34
    else:
        # Green to blue
        ratio = (normalized - 0.67) / 0.33  # 0 to 1
        r = int(34 - (34 - 65) * ratio)     # 34 -> 65
        g = int(139 - (139 - 105) * ratio)  # 139 -> 105
        b = int(34 - (34 - 225) * ratio)     # 34 -> 225
    
    return (r, g, b)


def create_moisture_map(
    processed_dir: Path,
    output_path: Path,
    h3_resolution: int = 7,
    use_coords: bool = False,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6,
    config_path: Optional[Path] = None
) -> dict:
    """
    Create interactive soil moisture map using H3 hexagons.
    
    Uses processed data from merged_soil_data.csv (same as suitability map) which already
    has H3 indexes and is clipped if coordinates were provided. Extracts moisture column
    and aggregates by hexagon.
    
    Parameters
    ----------
    processed_dir : Path
        Directory containing processed data (merged_soil_data.csv)
    output_path : Path
        Path to save HTML file
    h3_resolution : int, default 7
        H3 resolution that was used in the analysis (for validation)
    use_coords : bool, default False
        Whether coordinates were provided (affects resolution logic)
    center_lat : float, optional
        Center latitude for map (default: None, auto-calculated)
    center_lon : float, optional
        Center longitude for map (default: None, auto-calculated)
    zoom_start : int, optional
        Initial zoom level (default: 6)
    config_path : Path, optional
        Path to config file (for initialization if needed)
    
    Returns
    -------
    dict
        Map generation info with keys: 'method', 'file_size_mb', 'file_path'
    """
    print("\nCreating soil moisture map...")
    print(f"  Loading moisture data from processed data: {processed_dir}")
    
    # Load merged soil data (already has H3 indexes and is clipped if coordinates were provided)
    merged_csv = processed_dir / "merged_soil_data.csv"
    if not merged_csv.exists():
        raise FileNotFoundError(f"Processed data not found: {merged_csv}. Please run the analysis first.")
    
    print(f"  Loading merged soil data: {merged_csv.name}")
    merged_df = pd.read_csv(merged_csv)
    print(f"    Loaded {len(merged_df):,} rows from merged data")
    
    # Find moisture column
    moisture_cols = [col for col in merged_df.columns if 'moisture' in col.lower() or 'sm_surface' in col.lower()]
    if not moisture_cols:
        raise ValueError(f"No moisture columns found in merged data. Available columns: {list(merged_df.columns)}")
    
    # Use first moisture column found
    moisture_col = moisture_cols[0]
    print(f"    Found moisture column: {moisture_col}")
    
    # Check if H3 index is already present
    if 'h3_index' not in merged_df.columns:
        raise ValueError("H3 index not found in merged data. Data may not have been processed correctly.")
    
    # Extract moisture values and convert from m³/m³ to percentage (0-100)
    # Check if values are already in percentage (range 0-100) or in m³/m³ (range 0-1)
    sample_value = merged_df[moisture_col].dropna().iloc[0] if not merged_df[moisture_col].dropna().empty else None
    if sample_value is not None and sample_value <= 1.0:
        # Values are in m³/m³, convert to percentage
        merged_df['moisture'] = merged_df[moisture_col] * 100.0
    else:
        # Values are already in percentage
        merged_df['moisture'] = merged_df[moisture_col]
    
    # Drop rows with NaN moisture values
    merged_df = merged_df.dropna(subset=['moisture', 'h3_index'])
    print(f"    {len(merged_df):,} rows with valid moisture and H3 index")
    
    if merged_df.empty:
        raise ValueError("No valid moisture data points found")
    
    # Check if data is already aggregated (one row per hexagon) or needs aggregation
    unique_hexagons = merged_df['h3_index'].nunique()
    total_rows = len(merged_df)
    
    if unique_hexagons == total_rows:
        # Data is already aggregated - one row per hexagon
        print("  Data is already aggregated by hexagon")
        hexagon_data = merged_df[['h3_index', 'moisture', 'lat', 'lon']].copy()
        # Add point_count if available, otherwise set to 1
        if 'point_count' in merged_df.columns:
            hexagon_data['point_count'] = merged_df['point_count']
        else:
            hexagon_data['point_count'] = 1
        print(f"    Using {len(hexagon_data):,} hexagons (already aggregated)")
    else:
        # Data needs aggregation - multiple points per hexagon
        print("  Aggregating moisture by hexagon...")
        hexagon_data = merged_df.groupby('h3_index').agg({
            'moisture': 'mean',
            'lat': 'first',
            'lon': 'first'
        }).reset_index()
        
        # Add point count
        point_counts = merged_df.groupby('h3_index').size().reset_index(name='point_count')
        hexagon_data = hexagon_data.merge(point_counts, on='h3_index')
        
        print(f"    Aggregated to {len(hexagon_data):,} hexagons from {total_rows:,} points")
    
    # Calculate center if not provided
    if center_lat is None:
        center_lat = hexagon_data['lat'].mean()
    if center_lon is None:
        center_lon = hexagon_data['lon'].mean()
    
    # Prepare data for visualization
    hexagon_data = _prepare_moisture_hexagon_data(hexagon_data)
    
    # Create PyDeck layer
    layer = _create_moisture_h3_hexagon_layer(hexagon_data)
    
    # Create view state
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_start,
        pitch=0,
        bearing=0
    )
    
    # Create tooltip
    tooltip = {
        'html': '''
        <b>Soil Moisture:</b> {moisture_formatted}%<br>
        <b>Location:</b> {lat_formatted}, {lon_formatted}<br>
        <b>Points:</b> {point_count}
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
    print(f"  Soil moisture map created: {file_size_mb:.2f} MB")
    
    return {
        'method': 'pydeck',
        'file_size_mb': file_size_mb,
        'file_path': output_path
    }


def _prepare_moisture_hexagon_data(hexagon_data: pd.DataFrame) -> pd.DataFrame:
    """Prepare hexagon data for moisture map visualization."""
    # Format values for tooltip
    hexagon_data['lat_formatted'] = hexagon_data['lat'].apply(lambda x: f"{x:.2f}")
    hexagon_data['lon_formatted'] = hexagon_data['lon'].apply(lambda x: f"{x:.2f}")
    hexagon_data['moisture_formatted'] = hexagon_data['moisture'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    
    # Calculate color based on moisture value using fixed absolute range (0-100%)
    # This ensures consistent color grading across the entire state
    ABSOLUTE_MIN_MOISTURE = 0.0  # %
    ABSOLUTE_MAX_MOISTURE = 100.0  # %
    
    def get_color_rgba(moisture_value):
        """Get RGBA color array for moisture value using absolute range."""
        r, g, b = get_moisture_color_rgb(moisture_value, ABSOLUTE_MIN_MOISTURE, ABSOLUTE_MAX_MOISTURE)
        return [r, g, b, 255]  # Full opacity
    
    hexagon_data['color'] = hexagon_data['moisture'].apply(get_color_rgba)
    
    # Calculate actual range for reporting
    actual_min_moisture = hexagon_data['moisture'].min()
    actual_max_moisture = hexagon_data['moisture'].max()
    
    print(f"  Prepared {len(hexagon_data):,} H3 hexagons")
    print(f"  Moisture range (actual): {actual_min_moisture:.2f} - {actual_max_moisture:.2f} %")
    print(f"  Moisture range (absolute for coloring): {ABSOLUTE_MIN_MOISTURE:.2f} - {ABSOLUTE_MAX_MOISTURE:.2f} %")
    
    return hexagon_data


def _create_moisture_h3_hexagon_layer(hexagon_data: pd.DataFrame) -> pdk.Layer:
    """Create H3 hexagon layer for moisture map."""
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

