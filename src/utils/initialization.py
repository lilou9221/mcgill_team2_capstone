"""
Shared Initialization Module

Step 1: Project Structure Setup
Provides shared initialization for both data acquisition and data processing workflows.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

# Add project root to path for imports
# Calculate project root once at module level (src/utils/ -> src/ -> project root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.utils.config_loader import load_config


def initialize_project(config_path: str = "configs/config.yaml") -> Tuple[Dict, Path, Path, Path]:
    """
    Initialize project structure and load configuration.
    
    This is Step 1: Project Structure Setup
    Shared by both data acquisition and data processing workflows.
    
    Parameters
    ----------
    config_path : str, optional
        Path to configuration file (default: "configs/config.yaml")
        Can be absolute or relative to project root.
    
    Returns
    -------
    Tuple[Dict, Path, Path, Path]
        Tuple containing:
        - config: Loaded configuration dictionary
        - project_root: Path to project root directory
        - raw_dir: Path to data/ directory (flat structure)
        - processed_dir: Path to data/processed/ directory
    """
    # Use module-level project root (calculated once)
    project_root = _PROJECT_ROOT
    
    # Load configuration (works with defaults if config.yaml doesn't exist)
    # config.yaml is only needed for optional data acquisition features (GEE/Drive)
    # Core pipeline works with default configuration
    config = load_config(config_path)
    
    # Get data directories from config
    data_config = config.get("data", {})
    raw_dir = Path(data_config.get("raw", "data"))  # Flat structure: all input files in data/
    processed_dir = Path(data_config.get("processed", "data/processed"))
    
    # Resolve relative paths relative to project root
    if not raw_dir.is_absolute():
        raw_dir = project_root / raw_dir
    if not processed_dir.is_absolute():
        processed_dir = project_root / processed_dir
    
    # Ensure directories exist
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    return config, project_root, raw_dir, processed_dir


if __name__ == "__main__":
    """Debug and test initialization."""
    import sys
    
    print("""============================================================
Project Initialization - Debug Mode
============================================================""")
    
    try:
        config, project_root, raw_dir, processed_dir = initialize_project()
        print(f"""
PASS: Project initialized successfully
  Project root: {project_root}
  Raw data directory: {raw_dir}
  Processed data directory: {processed_dir}
  Configuration loaded: {len(config)} sections""")
        
        # Check if directories exist
        if raw_dir.exists():
            tif_files = list(raw_dir.glob("*.tif"))
            print(f"  GeoTIFF files in raw/: {len(tif_files)}")
        else:
            print("  raw/ directory does not exist (will be created on first run)")
        
        if processed_dir.exists():
            csv_files = list(processed_dir.glob("*.csv"))
            print(f"  CSV files in processed/: {len(csv_files)}")
        else:
            print("  processed/ directory does not exist (will be created on first run)")
        
    except Exception as e:
        print(f"  FAIL: Error initializing project: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("""
------------------------------------------------------------
Usage Example:
------------------------------------------------------------
  from src.utils.initialization import initialize_project
  config, project_root, raw_dir, processed_dir = initialize_project()
------------------------------------------------------------""")

