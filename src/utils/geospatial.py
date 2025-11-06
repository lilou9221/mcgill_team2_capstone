"""
Geospatial Utility Functions

Helper functions for geometry operations, coordinate transformations,
and spatial calculations.
"""

from typing import Tuple
from shapely.geometry import Point
from shapely.ops import transform
import pyproj
from functools import partial


def create_circle_buffer(lat: float, lon: float, radius_km: float):
    """
    Create a circular buffer around a point using WGS84 coordinates.
    
    Parameters
    ----------
    lat : float
        Latitude of the center point (WGS84)
    lon : float
        Longitude of the center point (WGS84)
    radius_km : float
        Radius in kilometers
    
    Returns
    -------
    shapely.geometry.Polygon
        Circular buffer polygon in WGS84 (EPSG:4326)
    """
    # Create center point in WGS84
    center = Point(lon, lat)
    
    # Convert radius from km to degrees (approximate)
    # At the equator: 1 degree latitude ≈ 111 km
    # For longitude, it varies by latitude: 1 degree ≈ 111 km * cos(latitude)
    # We'll use an average approximation for the buffer
    # For more accuracy, we could project to a local CRS, but for clipping purposes
    # this approximation should work fine
    
    # Use a more accurate method: project to a local UTM zone, create buffer, then reproject back
    # For Mato Grosso, we're around -12 to -15 latitude, which is in UTM Zone 21S (EPSG:32721)
    
    # Get approximate UTM zone for the latitude
    utm_zone = int((lon + 180) / 6) + 1
    # For southern hemisphere (negative latitude), use EPSG:32700 + zone
    # For northern hemisphere, use EPSG:32600 + zone
    if lat < 0:
        utm_epsg = 32700 + utm_zone
    else:
        utm_epsg = 32600 + utm_zone
    
    # Project to UTM for accurate buffer creation
    wgs84 = pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS(f'EPSG:{utm_epsg}')
    
    project_to_utm = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    project_to_wgs84 = pyproj.Transformer.from_crs(utm, wgs84, always_xy=True).transform
    
    # Transform point to UTM
    center_utm = transform(project_to_utm, center)
    
    # Create buffer in meters (radius_km * 1000)
    radius_m = radius_km * 1000
    buffer_utm = center_utm.buffer(radius_m)
    
    # Transform back to WGS84
    buffer_wgs84 = transform(project_to_wgs84, buffer_utm)
    
    return buffer_wgs84


def get_utm_zone(lon: float, lat: float) -> int:
    """
    Get UTM zone number for given coordinates.
    
    Parameters
    ----------
    lon : float
        Longitude
    lat : float
        Latitude
    
    Returns
    -------
    int
        UTM zone number
    """
    return int((lon + 180) / 6) + 1


def get_utm_crs(lon: float, lat: float) -> str:
    """
    Get UTM CRS string for given coordinates.
    
    Parameters
    ----------
    lon : float
        Longitude
    lat : float
        Latitude
    
    Returns
    -------
    str
        UTM CRS string (e.g., 'EPSG:32721' for southern hemisphere)
    """
    utm_zone = get_utm_zone(lon, lat)
    if lat < 0:
        # Southern hemisphere
        return f'EPSG:{32700 + utm_zone}'
    else:
        # Northern hemisphere
        return f'EPSG:{32600 + utm_zone}'


def transform_geometry(geometry, from_crs: str, to_crs: str):
    """
    Transform a geometry from one CRS to another.
    
    Parameters
    ----------
    geometry : shapely.geometry
        Geometry to transform
    from_crs : str
        Source CRS (e.g., 'EPSG:4326')
    to_crs : str
        Target CRS (e.g., 'EPSG:32721')
    
    Returns
    -------
    shapely.geometry
        Transformed geometry
    """
    from_crs_obj = pyproj.CRS(from_crs)
    to_crs_obj = pyproj.CRS(to_crs)
    
    transformer = pyproj.Transformer.from_crs(from_crs_obj, to_crs_obj, always_xy=True)
    return transform(transformer.transform, geometry)


if __name__ == "__main__":
    """Debug and test geospatial functions."""
    import sys
    
    print("""============================================================
Geospatial Utilities - Debug Mode
============================================================

------------------------------------------------------------
1. Testing create_circle_buffer():
------------------------------------------------------------""")
    
    test_cases = [
        (-12.0, -55.0, 100.0, "Cuiaba area, 100km radius"),
        (-15.0, -60.0, 50.0, "Central Mato Grosso, 50km radius"),
        (-10.0, -52.0, 250.0, "Northern Mato Grosso, 250km radius"),
    ]
    
    passed = 0
    failed = 0
    
    for lat, lon, radius_km, description in test_cases:
        try:
            circle = create_circle_buffer(lat, lon, radius_km)
            print(f"""  PASS: {description}
    Center: ({lat}, {lon})
    Radius: {radius_km} km
    Circle type: {type(circle).__name__}
    Circle area (approx): {circle.area:.6f} square degrees
    Bounds: {circle.bounds}""")
            passed += 1
        except Exception as e:
            print(f"""  FAIL: {description}
    Error: {type(e).__name__}: {e}""")
            failed += 1
    
    # Test UTM zone calculation
    print("""
------------------------------------------------------------
2. Testing UTM zone functions:
------------------------------------------------------------""")
    
    test_coords = [
        (-12.0, -55.0, "Cuiaba area"),
        (-15.0, -60.0, "Central Mato Grosso"),
        (0.0, 0.0, "Equator/Prime Meridian"),
    ]
    
    for lat, lon, description in test_coords:
        try:
            utm_zone = get_utm_zone(lon, lat)
            utm_crs = get_utm_crs(lon, lat)
            print(f"""  {description}: ({lat}, {lon})
    UTM Zone: {utm_zone}
    UTM CRS: {utm_crs}""")
            passed += 1
        except Exception as e:
            print(f"""  FAIL: {description}
    Error: {type(e).__name__}: {e}""")
            failed += 1
    
    # Summary
    print(f"""
============================================================
Test Summary: {passed} passed, {failed} failed
============================================================""")
    
    if failed > 0:
        sys.exit(1)

