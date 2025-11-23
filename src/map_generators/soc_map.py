"""
Soil Organic Carbon (SOC) Map Generator

Creates interactive maps showing SOC values aggregated by H3 hexagons.
Uses b0 and b10 layers: mean_SOC = (mean(b0) + mean(b10)) / 2
"""

from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import numpy as np
import pydeck as pdk

from src.data_processors.raster_to_csv import raster_to_dataframe
from src.data_processors.h3_converter import add_h3_to_dataframe


def get_soc_color_rgb(soc_value: float, min_soc: float, max_soc: float) -> tuple:
    """
    Get RGB color for SOC value using a sequential color scheme (beige to dark green/brown).
    
    Parameters
    ----------
    soc_value : float
        SOC value in g/kg
    min_soc : float
        Minimum SOC value for color range (absolute: 0.0 g/kg)
    max_soc : float
        Maximum SOC value for color range (absolute: 60.0 g/kg)
    
    Returns
    -------
    tuple
        RGB color tuple (r, g, b) with values 0-255
    """
    if np.isnan(soc_value) or min_soc == max_soc:
        return (128, 128, 128)  # Gray for NaN or constant values
    
    # Normalize to 0-1 range
    normalized = (soc_value - min_soc) / (max_soc - min_soc)
    normalized = max(0.0, min(1.0, normalized))  # Clamp to [0, 1]
    
    # Sequential color scheme: beige (#F5DEB3) to dark green (#2E7D32)
    # Interpolate between beige and dark green through yellow-green
    if normalized < 0.5:
        # Beige to yellow-green
        ratio = normalized * 2.0  # 0 to 1
        r = int(245 - (245 - 173) * ratio)  # 245 -> 173
        g = int(222 - (222 - 255) * ratio)  # 222 -> 255
        b = int(179 - (179 - 47) * ratio)   # 179 -> 47
    else:
        # Yellow-green to dark green
        ratio = (normalized - 0.5) * 2.0  # 0 to 1
        r = int(173 - (173 - 46) * ratio)  # 173 -> 46
        g = int(255 - (255 - 125) * ratio)  # 255 -> 125
        b = int(47 - (47 - 50) * ratio)     # 47 -> 50
    
    return (r, g, b)


def create_soc_map(
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
    Create interactive SOC map using H3 hexagons.
    
    Uses processed data from merged_soil_data.csv (same as suitability map) which already
    has H3 indexes and is clipped if coordinates were provided. Extracts SOC columns (b0 and b10)
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
    print("\nCreating SOC map...")
    print(f"  Loading SOC data from processed data: {processed_dir}")
    
    # Load merged soil data (already has H3 indexes and is clipped if coordinates were provided)
    merged_csv = processed_dir / "merged_soil_data.csv"
    if not merged_csv.exists():
        raise FileNotFoundError(f"Processed data not found: {merged_csv}. Please run the analysis first.")
    
    print(f"  Loading merged soil data: {merged_csv.name}")
    merged_df = pd.read_csv(merged_csv)
    print(f"    Loaded {len(merged_df):,} rows from merged data")
    
    # Find SOC columns (b0 and b10)
    soc_cols = [col for col in merged_df.columns if 'soc' in col.lower() or 'soil_organic' in col.lower()]
    if not soc_cols:
        raise ValueError(f"No SOC columns found in merged data. Available columns: {list(merged_df.columns)}")
    
    # Find b0 and b10 columns
    b0_cols = [col for col in soc_cols if 'b0' in col.lower() and 'b10' not in col.lower()]
    b10_cols = [col for col in soc_cols if 'b10' in col.lower()]
    
    print(f"    Found SOC columns: {soc_cols}")
    
    # Check if H3 index is already present
    if 'h3_index' not in merged_df.columns:
        raise ValueError("H3 index not found in merged data. Data may not have been processed correctly.")
    
    # Calculate mean SOC from b0 and b10
    if b0_cols and b10_cols:
        # Use first b0 and first b10 column
        b0_col = b0_cols[0]
        b10_col = b10_cols[0]
        print(f"  Calculating mean SOC from {b0_col} and {b10_col}")
        merged_df['soc'] = merged_df[[b0_col, b10_col]].mean(axis=1, skipna=True)
    elif b0_cols:
        print(f"  Using b0 only: {b0_cols[0]}")
        merged_df['soc'] = merged_df[b0_cols[0]]
    elif b10_cols:
        print(f"  Using b10 only: {b10_cols[0]}")
        merged_df['soc'] = merged_df[b10_cols[0]]
    else:
        raise ValueError("No b0 or b10 SOC columns found in merged data")
    
    # Drop rows with NaN SOC values
    merged_df = merged_df.dropna(subset=['soc', 'h3_index'])
    print(f"    {len(merged_df):,} rows with valid SOC and H3 index")
    
    if merged_df.empty:
        raise ValueError("No valid SOC data points found")
    
    # Check if data is already aggregated (one row per hexagon) or needs aggregation
    unique_hexagons = merged_df['h3_index'].nunique()
    total_rows = len(merged_df)
    
    if unique_hexagons == total_rows:
        # Data is already aggregated - one row per hexagon
        print("  Data is already aggregated by hexagon")
        hexagon_data = merged_df[['h3_index', 'soc', 'lat', 'lon']].copy()
        # Add point_count if available, otherwise set to 1
        if 'point_count' in merged_df.columns:
            hexagon_data['point_count'] = merged_df['point_count']
        else:
            hexagon_data['point_count'] = 1
        print(f"    Using {len(hexagon_data):,} hexagons (already aggregated)")
    else:
        # Data needs aggregation - multiple points per hexagon
        print("  Aggregating SOC by hexagon...")
        hexagon_data = merged_df.groupby('h3_index').agg({
            'soc': 'mean',
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
    hexagon_data = _prepare_soc_hexagon_data(hexagon_data)
    
    # Create PyDeck layer
    layer = _create_soc_h3_hexagon_layer(hexagon_data)
    
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
        <b>Soil Organic Carbon:</b> {soc_formatted} g/kg<br>
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
    print(f"  SOC map created: {file_size_mb:.2f} MB")
    
    return {
        'method': 'pydeck',
        'file_size_mb': file_size_mb,
        'file_path': output_path
    }


def _prepare_soc_hexagon_data(hexagon_data: pd.DataFrame) -> pd.DataFrame:
    """Prepare hexagon data for SOC map visualization."""
    # Format values for tooltip
    hexagon_data['lat_formatted'] = hexagon_data['lat'].apply(lambda x: f"{x:.2f}")
    hexagon_data['lon_formatted'] = hexagon_data['lon'].apply(lambda x: f"{x:.2f}")
    hexagon_data['soc_formatted'] = hexagon_data['soc'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    
    # Calculate color based on SOC value using fixed absolute range (0-60 g/kg)
    # This ensures consistent color grading across the entire state
    ABSOLUTE_MIN_SOC = 0.0  # g/kg
    ABSOLUTE_MAX_SOC = 60.0  # g/kg
    
    def get_color_rgba(soc_value):
        """Get RGBA color array for SOC value using absolute range."""
        r, g, b = get_soc_color_rgb(soc_value, ABSOLUTE_MIN_SOC, ABSOLUTE_MAX_SOC)
        return [r, g, b, 255]  # Full opacity
    
    hexagon_data['color'] = hexagon_data['soc'].apply(get_color_rgba)
    
    # Calculate actual range for reporting
    actual_min_soc = hexagon_data['soc'].min()
    actual_max_soc = hexagon_data['soc'].max()
    
    print(f"  Prepared {len(hexagon_data):,} H3 hexagons")
    print(f"  SOC range (actual): {actual_min_soc:.2f} - {actual_max_soc:.2f} g/kg")
    print(f"  SOC range (absolute for coloring): {ABSOLUTE_MIN_SOC:.2f} - {ABSOLUTE_MAX_SOC:.2f} g/kg")
    
    return hexagon_data


def _create_soc_h3_hexagon_layer(hexagon_data: pd.DataFrame) -> pdk.Layer:
    """Create H3 hexagon layer for SOC map."""
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

