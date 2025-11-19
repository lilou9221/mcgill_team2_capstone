"""
Soil pH Map Generator

Creates interactive maps showing pH values aggregated by H3 hexagons.
Uses b0 and b10 layers: mean_pH = (mean(b0) + mean(b10)) / 2
"""

from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import numpy as np
import pydeck as pdk

from src.data.processing.raster_to_csv import raster_to_dataframe
from src.data.processing.h3_converter import add_h3_to_dataframe


def get_ph_color_rgb(ph_value: float, min_ph: float, max_ph: float) -> tuple:
    """
    Get RGB color for pH value using a diverging color scheme (light orange-yellow = acidic, yellow = neutral, blue = alkaline).
    
    Color mapping:
    - Light orange-yellow for acidic soils (<5.5)
    - Yellow for neutral (~7)
    - Blue for alkaline soils (>7.5)
    
    Parameters
    ----------
    ph_value : float
        pH value
    min_ph : float
        Minimum pH value in dataset
    max_ph : float
        Maximum pH value in dataset
    
    Returns
    -------
    tuple
        RGB color tuple (r, g, b) with values 0-255
    """
    if np.isnan(ph_value) or min_ph == max_ph:
        return (128, 128, 128)  # Gray for NaN or constant values
    
    # Map pH to color based on actual pH values, not normalized range
    # Light orange-yellow for acidic (<5.5), Yellow for neutral (~7), Blue for alkaline (>7.5)
    
    if ph_value < 5.5:
        # Acidic: Light orange-red to orange-yellow
        # Scale from light orange-red (pH ~4) to orange-yellow (pH 5.5)
        ratio = (ph_value - 4.0) / 1.5 if ph_value >= 4.0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        r = int(255)  # Keep red high
        g = int(140 + (200 - 140) * ratio)  # 140 (orange-red) -> 200 (orange-yellow)
        b = int(0)  # No blue
    elif ph_value < 7.0:
        # Slightly acidic to neutral: Orange-yellow to yellow
        # Scale from orange-yellow (pH 5.5) to yellow (pH 7.0)
        ratio = (ph_value - 5.5) / 1.5  # 0 to 1
        ratio = max(0.0, min(1.0, ratio))
        r = int(255 - (255 - 255) * ratio)    # 255 -> 255 (keep red high)
        g = int(200 + (255 - 200) * ratio)    # 200 -> 255 (increase green to yellow)
        b = int(0)                             # 0 (no blue)
    elif ph_value < 7.5:
        # Neutral to slightly alkaline: Yellow to light blue
        # Scale from yellow (pH 7.0) to light blue (pH 7.5)
        ratio = (ph_value - 7.0) / 0.5  # 0 to 1
        ratio = max(0.0, min(1.0, ratio))
        r = int(255 - (255 - 173) * ratio)    # 255 -> 173
        g = int(255 - (255 - 216) * ratio)    # 255 -> 216
        b = int(0 + (230 - 0) * ratio)        # 0 -> 230
    else:
        # Alkaline: Blue (light blue to dark blue)
        # Scale from light blue (pH 7.5) to dark blue (pH 9+)
        ratio = (ph_value - 7.5) / 1.5 if ph_value <= 9.0 else 1.0
        ratio = max(0.0, min(1.0, ratio))
        r = int(173 - (173 - 49) * ratio)     # 173 -> 49
        g = int(216 - (216 - 54) * ratio)     # 216 -> 54
        b = int(230 - (230 - 149) * ratio)    # 230 -> 149
    
    return (r, g, b)


def create_ph_map(
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
    Create interactive pH map using H3 hexagons.
    
    Uses processed data from merged_soil_data.csv (same as suitability map) which already
    has H3 indexes and is clipped if coordinates were provided. Extracts pH columns (b0 and b10)
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
    print("\nCreating pH map...")
    print(f"  Loading pH data from processed data: {processed_dir}")
    
    # Load merged soil data (already has H3 indexes and is clipped if coordinates were provided)
    merged_csv = processed_dir / "merged_soil_data.csv"
    if not merged_csv.exists():
        raise FileNotFoundError(f"Processed data not found: {merged_csv}. Please run the analysis first.")
    
    print(f"  Loading merged soil data: {merged_csv.name}")
    merged_df = pd.read_csv(merged_csv)
    print(f"    Loaded {len(merged_df):,} rows from merged data")
    
    # Find pH columns (b0 and b10)
    ph_cols = [col for col in merged_df.columns if 'ph' in col.lower()]
    if not ph_cols:
        raise ValueError(f"No pH columns found in merged data. Available columns: {list(merged_df.columns)}")
    
    # Find b0 and b10 columns
    b0_cols = [col for col in ph_cols if 'b0' in col.lower() and 'b10' not in col.lower()]
    b10_cols = [col for col in ph_cols if 'b10' in col.lower()]
    
    print(f"    Found pH columns: {ph_cols}")
    
    # Check if H3 index is already present
    if 'h3_index' not in merged_df.columns:
        raise ValueError("H3 index not found in merged data. Data may not have been processed correctly.")
    
    # Calculate mean pH from b0 and b10
    if b0_cols and b10_cols:
        # Use first b0 and first b10 column
        b0_col = b0_cols[0]
        b10_col = b10_cols[0]
        print(f"  Calculating mean pH from {b0_col} and {b10_col}")
        merged_df['ph'] = merged_df[[b0_col, b10_col]].mean(axis=1, skipna=True)
    elif b0_cols:
        print(f"  Using b0 only: {b0_cols[0]}")
        merged_df['ph'] = merged_df[b0_cols[0]]
    elif b10_cols:
        print(f"  Using b10 only: {b10_cols[0]}")
        merged_df['ph'] = merged_df[b10_cols[0]]
    else:
        raise ValueError("No b0 or b10 pH columns found in merged data")
    
    # Drop rows with NaN pH values
    merged_df = merged_df.dropna(subset=['ph', 'h3_index'])
    print(f"    {len(merged_df):,} rows with valid pH and H3 index")
    
    if merged_df.empty:
        raise ValueError("No valid pH data points found")
    
    # Check if data is already aggregated (one row per hexagon) or needs aggregation
    unique_hexagons = merged_df['h3_index'].nunique()
    total_rows = len(merged_df)
    
    if unique_hexagons == total_rows:
        # Data is already aggregated - one row per hexagon
        print("  Data is already aggregated by hexagon")
        hexagon_data = merged_df[['h3_index', 'ph', 'lat', 'lon']].copy()
        # Add point_count if available, otherwise set to 1
        if 'point_count' in merged_df.columns:
            hexagon_data['point_count'] = merged_df['point_count']
        else:
            hexagon_data['point_count'] = 1
        print(f"    Using {len(hexagon_data):,} hexagons (already aggregated)")
    else:
        # Data needs aggregation - multiple points per hexagon
        print("  Aggregating pH by hexagon...")
        hexagon_data = merged_df.groupby('h3_index').agg({
            'ph': 'mean',
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
    hexagon_data = _prepare_ph_hexagon_data(hexagon_data)
    
    # Create PyDeck layer
    layer = _create_ph_h3_hexagon_layer(hexagon_data)
    
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
        <b>Soil pH:</b> {ph_formatted}<br>
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
    print(f"  pH map created: {file_size_mb:.2f} MB")
    
    return {
        'method': 'pydeck',
        'file_size_mb': file_size_mb,
        'file_path': output_path
    }


def _prepare_ph_hexagon_data(hexagon_data: pd.DataFrame) -> pd.DataFrame:
    """Prepare hexagon data for pH map visualization."""
    # Format values for tooltip
    hexagon_data['lat_formatted'] = hexagon_data['lat'].apply(lambda x: f"{x:.2f}")
    hexagon_data['lon_formatted'] = hexagon_data['lon'].apply(lambda x: f"{x:.2f}")
    hexagon_data['ph_formatted'] = hexagon_data['ph'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    
    # Calculate color based on pH value
    min_ph = hexagon_data['ph'].min()
    max_ph = hexagon_data['ph'].max()
    
    def get_color_rgba(ph_value):
        """Get RGBA color array for pH value."""
        r, g, b = get_ph_color_rgb(ph_value, min_ph, max_ph)
        return [r, g, b, 255]  # Full opacity
    
    hexagon_data['color'] = hexagon_data['ph'].apply(get_color_rgba)
    
    print(f"  Prepared {len(hexagon_data):,} H3 hexagons")
    print(f"  pH range: {min_ph:.2f} - {max_ph:.2f}")
    
    return hexagon_data


def _create_ph_h3_hexagon_layer(hexagon_data: pd.DataFrame) -> pdk.Layer:
    """Create H3 hexagon layer for pH map."""
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

