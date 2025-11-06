"""
User Input Processing Module

Handles user input for area of interest specification.
Processes coordinates and radius for biochar suitability analysis.
"""

from typing import Optional
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.coordinate_validator import (
    AreaOfInterest,
    validate_coordinates,
    is_within_mato_grosso,
    is_latitude_within_mato_grosso,
    is_longitude_within_mato_grosso,
    validate_radius,
    format_coordinates,
    get_mato_grosso_bounds
)


def get_user_area_of_interest(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 100.0,
    interactive: bool = False
) -> AreaOfInterest:
    """
    Get user-defined area of interest.
    
    Parameters
    ----------
    lat : float, optional
        Latitude (if provided via CLI)
    lon : float, optional
        Longitude (if provided via CLI)
    radius_km : float, optional
        Radius in kilometers (default: 100.0)
    interactive : bool, optional
        If True, prompt user for input interactively (default: False)
    
    Returns
    -------
    AreaOfInterest
        Area of interest object with coordinates and radius
    
    Raises
    ------
    ValueError
        If coordinates are invalid or outside Mato Grosso bounds
    """
    # If only one coordinate provided, warn and use full state
    if (lat is not None and lon is None) or (lat is None and lon is not None):
        print("Warning: Only one coordinate provided. Using full Mato Grosso state.")
        return AreaOfInterest(
            lat=None,
            lon=None,
            radius_km=radius_km,
            use_full_state=True
        )
    
    # If both coordinates provided, validate them
    if lat is not None and lon is not None:
        if not validate_coordinates(lat, lon):
            raise ValueError(f"Invalid coordinates: ({lat}, {lon}). "
                           f"Latitude must be between -90 and 90, "
                           f"longitude must be between -180 and 180.")
        
        if not is_within_mato_grosso(lat, lon):
            bounds = get_mato_grosso_bounds()
            raise ValueError(
                f"Coordinates ({lat}, {lon}) are outside Mato Grosso bounds.\n"
                f"Mato Grosso bounds: "
                f"Latitude: {bounds['min_lat']} to {bounds['max_lat']}, "
                f"Longitude: {bounds['min_lon']} to {bounds['max_lon']}"
            )
        
        # Validate radius
        if not validate_radius(radius_km):
            raise ValueError(f"Invalid radius: {radius_km} km. "
                           f"Radius must be between 1 and 500 km.")
        
        return AreaOfInterest(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            use_full_state=False
        )
    
    # If interactive mode, prompt user
    if interactive:
        return _get_interactive_input(radius_km)
    
    # If no coordinates provided, use full state (default behavior)
    return AreaOfInterest(
        lat=None,
        lon=None,
        radius_km=radius_km,
        use_full_state=True
    )


def _get_interactive_input(default_radius: float = 100.0) -> AreaOfInterest:
    """
    Get user input interactively.
    
    Parameters
    ----------
    default_radius : float, optional
        Default radius in kilometers (default: 100.0)
    
    Returns
    -------
    AreaOfInterest
        Area of interest object
    """
    print("\n" + "=" * 60)
    print("Area of Interest Selection")
    print("=" * 60)
    
    # Ask if user wants to specify coordinates
    while True:
        choice = input("\nDo you want to specify coordinates for a 100km radius analysis? (y/n): ").strip().lower()
        if choice in ['y', 'yes', 'n', 'no']:
            break
        print("Please enter 'y' or 'n'")
    
    if choice in ['n', 'no']:
        print("\nUsing full Mato Grosso state for analysis")
        return AreaOfInterest(
            lat=None,
            lon=None,
            radius_km=default_radius,
            use_full_state=True
        )
    
    # Get coordinates
    bounds = get_mato_grosso_bounds()
    print(f"\nMato Grosso bounds:")
    print(f"  Latitude: {bounds['min_lat']} to {bounds['max_lat']}")
    print(f"  Longitude: {bounds['min_lon']} to {bounds['max_lon']}")
    
    # Get latitude
    while True:
        try:
            lat_input = input("\nEnter latitude (-90 to 90): ").strip()
            lat = float(lat_input)
            
            if not validate_coordinates(lat, 0):  # Use 0 as placeholder for lon validation
                print("Invalid latitude. Must be between -90 and 90.")
                continue
            
            if not is_latitude_within_mato_grosso(lat):  # Check lat bounds only
                print(f"Latitude {lat} is outside Mato Grosso bounds "
                      f"({bounds['min_lat']} to {bounds['max_lat']})")
                continue
            
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Get longitude
    while True:
        try:
            lon_input = input("Enter longitude (-180 to 180): ").strip()
            lon = float(lon_input)
            
            if not validate_coordinates(0, lon):  # Use 0 as placeholder for lat validation
                print("Invalid longitude. Must be between -180 and 180.")
                continue
            
            if not is_longitude_within_mato_grosso(lon):  # Check lon bounds only
                print(f"Longitude {lon} is outside Mato Grosso bounds "
                      f"({bounds['min_lon']} to {bounds['max_lon']})")
                continue
            
            # Final check: both coordinates together
            if not is_within_mato_grosso(lat, lon):
                print(f"Coordinates ({lat}, {lon}) are outside Mato Grosso bounds.")
                continue
            
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Get radius
    while True:
        try:
            radius_input = input(f"Enter radius in kilometers (default: {default_radius}): ").strip()
            if not radius_input:
                radius_km = default_radius
            else:
                radius_km = float(radius_input)
            
            if not validate_radius(radius_km):
                print(f"Invalid radius. Must be between 1 and 500 km.")
                continue
            
            break
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nSelected area: {radius_km}km radius around {format_coordinates(lat, lon)}")
    
    return AreaOfInterest(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        use_full_state=False
    )


def print_area_summary(area: AreaOfInterest) -> None:
    """
    Print a summary of the area of interest.
    
    Parameters
    ----------
    area : AreaOfInterest
        Area of interest to summarize
    """
    print("\n" + "-" * 60)
    print("Area of Interest Summary")
    print("-" * 60)
    
    if area.use_full_state:
        print("Mode: Full Mato Grosso state")
    else:
        print(f"Mode: {area.radius_km}km radius around point")
        print(f"Coordinates: {format_coordinates(area.lat, area.lon)}")
        print(f"Radius: {area.radius_km} km")
    
    print("-" * 60)


if __name__ == "__main__":
    """Debug and test user input processing functions."""
    import sys
    
    print("""============================================================
User Input Processing - Debug Mode
============================================================""")
    
    passed = 0
    failed = 0
    
    # Test with valid coordinates
    print("""
------------------------------------------------------------
1. Testing with valid coordinates in Mato Grosso:
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=-12.0, lon=-55.0, radius_km=100.0, interactive=False)
        print(f"""  PASS: Successfully created AreaOfInterest
    use_full_state: {area.use_full_state}
    lat: {area.lat}, lon: {area.lon}
    radius_km: {area.radius_km}""")
        print_area_summary(area)
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failed += 1
    
    # Test with no coordinates (full state)
    print("""
------------------------------------------------------------
2. Testing with no coordinates (full state):
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=None, lon=None, radius_km=100.0, interactive=False)
        print(f"""  PASS: Successfully created AreaOfInterest for full state
    use_full_state: {area.use_full_state}
    lat: {area.lat}, lon: {area.lon}""")
        print_area_summary(area)
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failed += 1
    
    # Test with only latitude provided
    print("""
------------------------------------------------------------
3. Testing with only latitude provided:
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=-12.0, lon=None, radius_km=100.0, interactive=False)
        print(f"""  PASS: Correctly handled partial coordinates (should use full state)
    use_full_state: {area.use_full_state}""")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {e}")
        failed += 1
    
    # Test with invalid coordinates
    print("""
------------------------------------------------------------
4. Testing with invalid coordinates:
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=91.0, lon=-55.0, radius_km=100.0, interactive=False)
        print("  FAIL: Should have raised ValueError for invalid coordinates")
        failed += 1
    except ValueError as e:
        print(f"""  PASS: Correctly raised ValueError for invalid coordinates
    Error message: {e}""")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error type: {type(e).__name__}: {e}")
        failed += 1
    
    # Test with coordinates outside Mato Grosso
    print("""
------------------------------------------------------------
5. Testing with coordinates outside Mato Grosso:
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=-20.0, lon=-50.0, radius_km=100.0, interactive=False)
        print("  FAIL: Should have raised ValueError for coordinates outside bounds")
        failed += 1
    except ValueError as e:
        print(f"""  PASS: Correctly raised ValueError for coordinates outside Mato Grosso
    Error message: {e}""")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error type: {type(e).__name__}: {e}")
        failed += 1
    
    # Test with invalid radius
    print("""
------------------------------------------------------------
6. Testing with invalid radius:
------------------------------------------------------------""")
    try:
        area = get_user_area_of_interest(lat=-12.0, lon=-55.0, radius_km=600.0, interactive=False)
        print("  FAIL: Should have raised ValueError for invalid radius")
        failed += 1
    except ValueError as e:
        print(f"""  PASS: Correctly raised ValueError for invalid radius
    Error message: {e}""")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error type: {type(e).__name__}: {e}")
        failed += 1
    
    # Summary
    print(f"""
============================================================
Test Summary: {passed} passed, {failed} failed
============================================================""")
    
    if failed > 0:
        sys.exit(1)

