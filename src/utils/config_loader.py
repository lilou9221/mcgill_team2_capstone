"""
Configuration Loader Utility

Loads and validates configuration from YAML files.
"""

try:
    import yaml
except ImportError:
    # Try to install PyYAML automatically (for Streamlit Cloud compatibility)
    import subprocess
    import sys
    try:
        print("PyYAML not found. Attempting to install...", file=sys.stderr, flush=True)
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "pyyaml>=6.0",
            "--quiet", "--disable-pip-version-check", "--user"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        import yaml
        print("PyYAML installed successfully.", file=sys.stderr, flush=True)
    except (subprocess.CalledProcessError, ImportError):
        # If installation fails or import still fails, raise helpful error
        raise ImportError(
            "PyYAML is not installed and could not be installed automatically.\n"
            "Please install it using: pip install pyyaml\n"
            "Or install all dependencies: pip install -r requirements.txt\n"
            "For Streamlit Cloud, ensure 'pyyaml>=6.0' is in requirements.txt and restart deployment."
        )

from pathlib import Path
from typing import Dict, Any, Optional
import sys
import os

# Try to load python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False


def _load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Environment variables should be prefixed with 'RC_' (Residual Carbon).
    Nested values use double underscore: RC_GEE__PROJECT_NAME
    
    Returns
    -------
    Dict[str, Any]
        Configuration dictionary from environment variables, empty if none found
    """
    config = {}
    prefix = "RC_"
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Remove prefix and convert to nested dict path
            config_key = key[len(prefix):].lower()
            # Convert double underscore to nested dict
            keys = config_key.split("__")
            
            # Build nested dictionary
            current = config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
    
    return config


def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two configuration dictionaries.
    
    Parameters
    ----------
    base : Dict[str, Any]
        Base configuration
    override : Dict[str, Any]
        Override configuration (takes precedence)
    
    Returns
    -------
    Dict[str, Any]
        Merged configuration
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration with fallback system:
    1. Load .env file if available (using python-dotenv)
    2. Try config.yaml (local file with secrets)
    3. If not found, try environment variables
    4. If still not found, try config.example.yaml (with warning)
    
    Environment variables can override config values:
    - Use prefix RC_ (e.g., RC_GEE__PROJECT_NAME for gee.project_name)
    - Use double underscore __ for nested keys
    - Or use .env file with same naming convention

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
    
    # Load .env file if available (before reading other configs)
    if _DOTENV_AVAILABLE:
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    
    if config_path is None:
        config_path = project_root / "configs" / "config.yaml"
    else:
        config_path = Path(config_path)
        # If it's a relative path, resolve it relative to project root
        if not config_path.is_absolute():
            config_path = project_root / config_path
    
    config = None
    config_source = None
    
    # Fallback 1: Try config.yaml (local file with secrets)
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        config_source = str(config_path)
    
    # Fallback 2: Try environment variables
    env_config = _load_config_from_env()
    if env_config:
        if config:
            # Merge env vars into file config (env vars take precedence)
            config = _merge_configs(config, env_config)
            config_source = f"{config_path} + environment variables"
        else:
            config = env_config
            config_source = "environment variables"
    
    # Fallback 3: Try config.example.yaml (with warning)
    if config is None:
        example_path = config_path.parent / "config.example.yaml"
        if example_path.exists():
            with open(example_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            config_source = str(example_path)
            print(
                f"WARNING: Using example configuration from {example_path}\n"
                f"This contains placeholder values. For production:\n"
                f"  1. Copy {example_path} to {config_path}\n"
                f"  2. Fill in your actual values (GEE project ID, Google Drive folder IDs, etc.)\n"
                f"  3. Or set environment variables with RC_ prefix (e.g., RC_GEE__PROJECT_NAME)\n",
                file=sys.stderr
            )
        else:
            # No config found anywhere
            error_msg = (
                f"Configuration file not found: {config_path}\n"
                f"Project root: {project_root}\n"
                f"Current working directory: {Path.cwd()}\n"
                f"\nPlease do one of the following:\n"
                f"  1. Copy configs/config.example.yaml to {config_path} and fill in your values\n"
                f"  2. Set environment variables with RC_ prefix (e.g., RC_GEE__PROJECT_NAME)\n"
                f"  3. Create {config_path} manually"
            )
            raise FileNotFoundError(error_msg)
    
    # Override sensitive values from environment variables (even if config file exists)
    env_config = _load_config_from_env()
    if env_config:
        config = _merge_configs(config, env_config)
        if config_source and "environment variables" not in config_source:
            config_source = f"{config_source} + environment variables"
    
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

