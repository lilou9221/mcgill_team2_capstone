"""
Biochar Thresholds Module

Loads and manages soil property thresholds for suitability scoring.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


def load_thresholds(thresholds_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load thresholds from YAML file.
    
    Parameters
    ----------
    thresholds_path : str, optional
        Path to thresholds file. Defaults to configs/thresholds.yaml relative to project root.
        If a relative path is provided, it will be resolved relative to the project root.
    
    Returns
    -------
    Dict[str, Any]
        Thresholds dictionary
    """
    # Get project root (parent of src directory)
    project_root = Path(__file__).parent.parent.parent
    
    if thresholds_path is None:
        thresholds_path = project_root / "configs" / "thresholds.yaml"
    else:
        thresholds_path = Path(thresholds_path)
        # If it's a relative path, resolve it relative to project root
        if not thresholds_path.is_absolute():
            thresholds_path = project_root / thresholds_path
    
    if not thresholds_path.exists():
        raise FileNotFoundError(
            f"Thresholds file not found: {thresholds_path}\n"
            f"Project root: {project_root}\n"
            f"Current working directory: {Path.cwd()}"
        )
    
    with open(thresholds_path, 'r') as f:
        thresholds = yaml.safe_load(f)
    
    return thresholds


def get_property_thresholds(thresholds: Dict[str, Any], property_name: str) -> Dict[str, Any]:
    """
    Get thresholds for a specific soil property.
    
    Parameters
    ----------
    thresholds : Dict[str, Any]
        Full thresholds dictionary
    property_name : str
        Name of soil property (e.g., 'soil_moisture', 'soil_temperature')
    
    Returns
    -------
    Dict[str, Any]
        Thresholds for the specified property
    
    Raises
    ------
    KeyError
        If property not found in thresholds
    """
    if property_name not in thresholds:
        available = list(thresholds.keys())
        raise KeyError(
            f"Property '{property_name}' not found in thresholds. "
            f"Available properties: {available}"
        )
    
    return thresholds[property_name]


if __name__ == "__main__":
    """Debug and test thresholds loading."""
    import sys
    
    print("""============================================================
Biochar Thresholds - Debug Mode
============================================================""")
    
    try:
        thresholds = load_thresholds()
        print(f"""
PASS: Thresholds loaded successfully
  Properties with thresholds: {list(thresholds.keys())}
  Total properties: {len(thresholds)}""")
        
        # Display thresholds for each property
        for prop_name, prop_thresholds in thresholds.items():
            print(f"""
  {prop_name}:""")
            if 'optimal_min' in prop_thresholds:
                print(f"    Optimal range: {prop_thresholds.get('optimal_min')} - {prop_thresholds.get('optimal_max')}")
            if 'acceptable_min' in prop_thresholds:
                print(f"    Acceptable range: {prop_thresholds.get('acceptable_min')} - {prop_thresholds.get('acceptable_max')}")
            if 'scoring' in prop_thresholds:
                scoring = prop_thresholds['scoring']
                print(f"    Scoring ranges:")
                if 'high' in scoring:
                    print(f"      High (8-10): {scoring['high']}")
                if 'medium' in scoring:
                    print(f"      Medium (5-7): {scoring['medium']}")
                if 'low' in scoring:
                    print(f"      Low (0-4): {scoring['low']}")
        
        # Test getting individual property thresholds
        print("""
------------------------------------------------------------
Testing get_property_thresholds():
------------------------------------------------------------""")
        
        test_properties = ['soil_moisture', 'soil_temperature', 'soil_organic_carbon', 'soil_pH']
        for prop in test_properties:
            try:
                prop_thresholds = get_property_thresholds(thresholds, prop)
                print(f"  PASS: {prop} thresholds retrieved successfully")
                print(f"    Optimal: {prop_thresholds.get('optimal_min')} - {prop_thresholds.get('optimal_max')}")
            except KeyError as e:
                print(f"  FAIL: {e}")
        
    except FileNotFoundError as e:
        print(f"""
FAIL: Thresholds file not found: {e}

Please create configs/thresholds.yaml""")
        sys.exit(1)
    except Exception as e:
        print(f"""
FAIL: Error loading thresholds: {type(e).__name__}: {e}""")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.analysis.thresholds import load_thresholds, get_property_thresholds
  
  thresholds = load_thresholds()
  moisture_thresholds = get_property_thresholds(thresholds, 'soil_moisture')
------------------------------------------------------------""")

