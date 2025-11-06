"""
Folium Map Module

Creates interactive maps using Folium.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
import folium
from folium import plugins
import h3

from src.visualization.color_scheme import get_color_for_score, get_color_scheme_info


def create_folium_map(
    df: pd.DataFrame,
    output_path: Path,
    use_h3: bool = True,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    zoom_start: int = 6
) -> None:
    """
    Create interactive Folium map with suitability scores.
    
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
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )
    
    # Add tile layers
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark Matter').add_to(m)
    
    # Check if H3 indexes are available
    has_h3 = use_h3 and 'h3_index' in df.columns
    
    if has_h3:
        # Create H3 hexagon layer
        _add_h3_hexagons(m, df)
    else:
        # Create point markers
        _add_point_markers(m, df)
    
    # Add legend
    _add_legend(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add fullscreen button
    plugins.Fullscreen().add_to(m)
    
    # Save map
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))


def _add_h3_hexagons(m: folium.Map, df: pd.DataFrame) -> None:
    """
    Add H3 hexagons to Folium map.
    
    Parameters
    ----------
    m : folium.Map
        Folium map object
    df : pd.DataFrame
        DataFrame with H3 indexes and suitability scores
    """
    # Group by H3 index and get mean score
    h3_groups = df.groupby('h3_index').agg({
        'suitability_score': 'mean',
        'lat': 'first',
        'lon': 'first'
    }).reset_index()
    
    print(f"  Adding {len(h3_groups):,} H3 hexagons...")
    
    for idx, row in h3_groups.iterrows():
        h3_index = row['h3_index']
        score = row['suitability_score']
        lat = row['lat']
        lon = row['lon']
        
        # Get hexagon boundary
        try:
            hex_boundary = h3.cell_to_boundary(h3_index, geo_json=True)
            # h3.cell_to_boundary returns (lat, lon) pairs when geo_json=True
            # Convert to list of [lat, lon] pairs for Folium
            hex_coords = [[lat, lon] for lat, lon in hex_boundary]
            
            # Get color for score
            color = get_color_for_score(score)
            
            # Create polygon
            folium.Polygon(
                locations=hex_coords,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1,
                popup=folium.Popup(
                    f"""
                    <b>Suitability Score:</b> {score:.2f}<br>
                    <b>H3 Index:</b> {h3_index}<br>
                    <b>Location:</b> {lat:.4f}, {lon:.4f}
                    """,
                    max_width=200
                ),
                tooltip=f"Score: {score:.2f}"
            ).add_to(m)
        except Exception as e:
            # Skip invalid H3 indexes
            continue


def _add_point_markers(m: folium.Map, df: pd.DataFrame) -> None:
    """
    Add point markers to Folium map.
    
    Parameters
    ----------
    m : folium.Map
        Folium map object
    df : pd.DataFrame
        DataFrame with coordinates and suitability scores
    """
    print(f"  Adding {len(df):,} point markers...")
    
    # Sample data if too large (Folium can be slow with many points)
    max_points = 100000
    if len(df) > max_points:
        print(f"  Sampling to {max_points:,} points for performance...")
        df = df.sample(n=max_points, random_state=42)
    
    for idx, row in df.iterrows():
        lat = row['lat']
        lon = row['lon']
        score = row['suitability_score']
        
        # Get color for score
        color = get_color_for_score(score)
        
        # Create circle marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=1,
            popup=folium.Popup(
                f"""
                <b>Suitability Score:</b> {score:.2f}<br>
                <b>Location:</b> {lat:.4f}, {lon:.4f}
                """,
                max_width=200
            ),
            tooltip=f"Score: {score:.2f}"
        ).add_to(m)


def _add_legend(m: folium.Map) -> None:
    """
    Add legend to Folium map.
    
    Parameters
    ----------
    m : folium.Map
        Folium map object
    """
    color_info = get_color_scheme_info()
    
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4 style="margin-top:0">Suitability Score</h4>
    """
    
    for range_info in color_info['ranges']:
        legend_html += f"""
        <p style="margin: 5px 0;">
            <i class="fa fa-square" style="color:{range_info['color']}"></i>
            {range_info['label']}
        </p>
        """
    
    legend_html += """
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))

