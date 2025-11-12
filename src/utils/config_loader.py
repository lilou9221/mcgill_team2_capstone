"""
Configuration Loader Utility

Loads and validates configuration from YAML files.
"""

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is not installed. Please install it using: pip install pyyaml\n"
        "Or install all dependencies: pip install -r requirements.txt"
    )

from pathlib import Path
from typing import Dict, Any, Optional


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Parameters
    ----------
    config_path : str, optional
        Path to config file. Defaults to configs/config.yaml relative to project root.
        If a relative path is provided, it will be resolved relative to the project root.

    Returns
    -------
    Dict[str, Any]
        Configuration dictionary
    """
    # Get project root (parent of src directory)
    project_root = Path(__file__).parent.parent.parent
    
    if config_path is None:
        config_path = project_root / "configs" / "config.yaml"
    else:
        config_path = Path(config_path)
        # If it's a relative path, resolve it relative to project root
        if not config_path.is_absolute():
            config_path = project_root / config_path
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Project root: {project_root}\n"
            f"Current working directory: {Path.cwd()}"
        )
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


if __name__ == "__main__":
    """Debug and test configuration loader."""
    import sys
    
    print("=" * 60)
    print("Configuration Loader - Debug Mode")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test loading default config
    print("\n" + "-" * 60)
    print("1. Loading default configuration:")
    print("-" * 60)
    try:
        config = load_config()
        print("  PASS: Configuration loaded successfully")
        print(f"    Config file: {Path(__file__).parent.parent.parent / 'configs' / 'config.yaml'}")
        print(f"    Project name: {config.get('gee', {}).get('project_name', 'Not set')}")
        print(f"    Export folder: {config.get('gee', {}).get('export_folder', 'Not set')}")
        print(f"    Default scale: {config.get('gee', {}).get('default_scale', 'Not set')}m")
        print(f"    Number of datasets: {len(config.get('datasets', {}))}")
        
        # Show dataset names
        datasets = config.get('datasets', {})
        if datasets:
            print(f"    Datasets: {', '.join(datasets.keys())}")
        
        passed += 1
    except FileNotFoundError as e:
        print(f"  FAIL: Configuration file not found")
        print(f"    Error: {e}")
        failed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {type(e).__name__}: {e}")
        failed += 1
    
    # Test loading with explicit path
    print("\n" + "-" * 60)
    print("2. Loading configuration with explicit path:")
    print("-" * 60)
    try:
        config = load_config("configs/config.yaml")
        print("  PASS: Configuration loaded successfully with explicit path")
        passed += 1
    except FileNotFoundError as e:
        print(f"  FAIL: Configuration file not found")
        print(f"    Error: {e}")
        failed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error: {type(e).__name__}: {e}")
        failed += 1
    
    # Test with invalid path
    print("\n" + "-" * 60)
    print("3. Testing with invalid path:")
    print("-" * 60)
    try:
        config = load_config("configs/nonexistent.yaml")
        print("  FAIL: Should have raised FileNotFoundError")
        failed += 1
    except FileNotFoundError as e:
        print("  PASS: Correctly raised FileNotFoundError for invalid path")
        print(f"    Error: {e}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Unexpected error type: {type(e).__name__}: {e}")
        failed += 1
    
    # Show project structure
    print("\n" + "-" * 60)
    print("4. Project Structure:")
    print("-" * 60)
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "configs" / "config.yaml"
    print(f"  Project root: {project_root}")
    print(f"  Config path: {config_path}")
    print(f"  Config exists: {config_path.exists()}")
    print(f"  Current working directory: {Path.cwd()}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)

