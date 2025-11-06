"""
Coordinate Validation Module

Validates user-provided coordinates for the biochar suitability mapping tool.
Ensures coordinates are within valid ranges and within Mato Grosso state boundaries.
"""

from typing import Tuple, Optional
from dataclasses import dataclass


# Mato Grosso state approximate boundaries (WGS84)
# These are approximate bounds - can be refined with actual state geometry
MATO_GROSSO_BOUNDS = {
    'min_lat': -18.0,  # Southern boundary
    'max_lat': -7.0,   # Northern boundary
    'min_lon': -65.0,  # Western boundary
    'max_lon': -50.0,  # Eastern boundary
}


@dataclass
class AreaOfInterest:
    """Represents a user-defined area of interest."""
    lat: Optional[float]
    lon: Optional[float]
    radius_km: float
    use_full_state: bool
    
    def __post_init__(self):
        """Validate the area of interest after initialization."""
        if not self.use_full_state:
            if self.lat is None or self.lon is None:
                raise ValueError("Coordinates must be provided when not using full state")
            if not validate_coordinates(self.lat, self.lon):
                raise ValueError(f"Invalid coordinates: ({self.lat}, {self.lon})")
            if not is_within_mato_grosso(self.lat, self.lon):
                raise ValueError(f"Coordinates ({self.lat}, {self.lon}) are outside Mato Grosso bounds")


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Parameters
    ----------
    lat : float
        Latitude (-90 to 90)
    lon : float
        Longitude (-180 to 180)
    
    Returns
    -------
    bool
        True if coordinates are valid, False otherwise
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    
    # Check latitude range
    if lat < -90.0 or lat > 90.0:
        return False
    
    # Check longitude range
    if lon < -180.0 or lon > 180.0:
        return False
    
    return True


def is_within_mato_grosso(lat: float, lon: float) -> bool:
    """
    Check if coordinates are within Mato Grosso state boundaries.
    
    Parameters
    ----------
    lat : float
        Latitude
    lon : float
        Longitude
    
    Returns
    -------
    bool
        True if coordinates are within Mato Grosso bounds, False otherwise
    """
    if not validate_coordinates(lat, lon):
        return False
    
    bounds = MATO_GROSSO_BOUNDS
    return (
        bounds['min_lat'] <= lat <= bounds['max_lat'] and
        bounds['min_lon'] <= lon <= bounds['max_lon']
    )


def is_latitude_within_mato_grosso(lat: float) -> bool:
    """
    Check if latitude is within Mato Grosso state boundaries.
    
    Parameters
    ----------
    lat : float
        Latitude
    
    Returns
    -------
    bool
        True if latitude is within Mato Grosso bounds, False otherwise
    """
    if not isinstance(lat, (int, float)) or lat < -90.0 or lat > 90.0:
        return False
    
    bounds = MATO_GROSSO_BOUNDS
    return bounds['min_lat'] <= lat <= bounds['max_lat']


def is_longitude_within_mato_grosso(lon: float) -> bool:
    """
    Check if longitude is within Mato Grosso state boundaries.
    
    Parameters
    ----------
    lon : float
        Longitude
    
    Returns
    -------
    bool
        True if longitude is within Mato Grosso bounds, False otherwise
    """
    if not isinstance(lon, (int, float)) or lon < -180.0 or lon > 180.0:
        return False
    
    bounds = MATO_GROSSO_BOUNDS
    return bounds['min_lon'] <= lon <= bounds['max_lon']


def get_mato_grosso_bounds() -> dict:
    """
    Get Mato Grosso state boundaries.
    
    Returns
    -------
    dict
        Dictionary with min_lat, max_lat, min_lon, max_lon keys
    """
    return MATO_GROSSO_BOUNDS.copy()


def validate_radius(radius_km: float, min_radius: float = 1.0, max_radius: float = 500.0) -> bool:
    """
    Validate that radius is within acceptable range.
    
    Parameters
    ----------
    radius_km : float
        Radius in kilometers
    min_radius : float, optional
        Minimum allowed radius (default: 1.0 km)
    max_radius : float, optional
        Maximum allowed radius (default: 500.0 km)
    
    Returns
    -------
    bool
        True if radius is valid, False otherwise
    """
    if not isinstance(radius_km, (int, float)):
        return False
    
    if radius_km < min_radius or radius_km > max_radius:
        return False
    
    return True


def format_coordinates(lat: float, lon: float, decimals: int = 6) -> str:
    """
    Format coordinates as a string.
    
    Parameters
    ----------
    lat : float
        Latitude
    lon : float
        Longitude
    decimals : int, optional
        Number of decimal places (default: 6)
    
    Returns
    -------
    str
        Formatted coordinate string
    """
    return f"({lat:.{decimals}f}, {lon:.{decimals}f})"


if __name__ == "__main__":
    """Debug and test coordinate validation functions."""
    import sys
    
    print("""============================================================
Coordinate Validator - Debug Mode
============================================================

Mato Grosso State Bounds:""")
    bounds = get_mato_grosso_bounds()
    print(f"""  Latitude: {bounds['min_lat']} to {bounds['max_lat']}
  Longitude: {bounds['min_lon']} to {bounds['max_lon']}

------------------------------------------------------------
1. Testing validate_coordinates():
------------------------------------------------------------""")
    test_coords = [
        (-12.0, -55.0, True, "Valid coordinates in Mato Grosso"),
        (0.0, 0.0, True, "Valid coordinates (equator)"),
        (90.0, 180.0, True, "Valid edge case (max lat/lon)"),
        (-90.0, -180.0, True, "Valid edge case (min lat/lon)"),
        (91.0, -55.0, False, "Invalid latitude (too high)"),
        (-91.0, -55.0, False, "Invalid latitude (too low)"),
        (-12.0, 181.0, False, "Invalid longitude (too high)"),
        (-12.0, -181.0, False, "Invalid longitude (too low)"),
        ("invalid", -55.0, False, "Invalid type (string)"),
    ]
    
    passed = 0
    failed = 0
    for lat, lon, expected, description in test_coords:
        result = validate_coordinates(lat, lon)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"""  {status}: {description}
    Input: ({lat}, {lon}) -> Result: {result} (expected {expected})""")
    
    # Test Mato Grosso bounds
    print("""
------------------------------------------------------------
2. Testing is_within_mato_grosso():
------------------------------------------------------------""")
    test_bounds = [
        (-12.0, -55.0, True, "Cuiaba area (within bounds)"),
        (-15.0, -60.0, True, "Central Mato Grosso"),
        (-10.0, -52.0, True, "Northern Mato Grosso"),
        (-20.0, -50.0, False, "South of Mato Grosso"),
        (0.0, 0.0, False, "Equator (outside bounds)"),
        (-12.0, -70.0, False, "West of Mato Grosso"),
        (-12.0, -40.0, False, "East of Mato Grosso"),
    ]
    
    for lat, lon, expected, description in test_bounds:
        if validate_coordinates(lat, lon):
            result = is_within_mato_grosso(lat, lon)
            status = "PASS" if result == expected else "FAIL"
            if result == expected:
                passed += 1
            else:
                failed += 1
            print(f"""  {status}: {description}
    Input: ({lat}, {lon}) -> Result: {result} (expected {expected})""")
    
    # Test radius validation
    print("""
------------------------------------------------------------
3. Testing validate_radius():
------------------------------------------------------------""")
    test_radii = [
        (1.0, True, "Minimum valid radius"),
        (50.0, True, "Valid radius"),
        (100.0, True, "Default radius"),
        (250.0, True, "Valid radius"),
        (500.0, True, "Maximum valid radius"),
        (0.5, False, "Too small"),
        (600.0, False, "Too large"),
        (-10.0, False, "Negative radius"),
        (0.0, False, "Zero radius"),
    ]
    
    for radius, expected, description in test_radii:
        result = validate_radius(radius)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"""  {status}: {description}
    Input: {radius} km -> Result: {result} (expected {expected})""")
    
    # Test format_coordinates
    print("""
------------------------------------------------------------
4. Testing format_coordinates():
------------------------------------------------------------""")
    test_format = [
        (-12.0, -55.0, "(-12.000000, -55.000000)"),
        (-12.123456, -55.654321, "(-12.123456, -55.654321)"),
    ]
    
    for lat, lon, expected in test_format:
        result = format_coordinates(lat, lon)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"""  {status}: ({lat}, {lon}) -> {result}
    Expected: {expected}""")
    
    # Summary
    print(f"""
============================================================
Test Summary: {passed} passed, {failed} failed
============================================================""")
    
    if failed > 0:
        sys.exit(1)

