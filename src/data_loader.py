"""
Data Loader Script

Downloads and exports soil property datasets from Google Earth Engine.
This script handles Steps 2, 3, and 4 of the workflow.

Usage:
    python src/data_loader.py
    python src/data_loader.py --config configs/config.yaml
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.acquisition.gee_loader import GEEDataLoader
from src.utils.initialization import initialize_project


def main():
    """Main entry point for data loading workflow."""
    parser = argparse.ArgumentParser(
        description="Download and export soil property datasets from Google Earth Engine"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Path to configuration file (default: configs/config.yaml)"
    )
    
    args = parser.parse_args()
    
    print("""============================================================
Residual_Carbon - Data Loader
Google Earth Engine Data Acquisition
============================================================
""")
    
    # STEP 1: Project Structure Setup (shared initialization)
    print("""
============================================================
STEP 1: Project Structure Setup
============================================================""")
    
    try:
        config, project_root, raw_dir, processed_dir = initialize_project(args.config)
        print(f"""Configuration loaded successfully
Project root: {project_root}
Raw data directory: {raw_dir}
Processed data directory: {processed_dir}""")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    
    print("\nSTEP 1 completed successfully!")
    
    # STEP 2: Initialize Google Earth Engine and load datasets
    print("""
============================================================
STEP 2: Google Earth Engine Data Retrieval
============================================================""")
    
    try:
        # Initialize GEE loader
        loader = GEEDataLoader(config_path=args.config)
        
        # Initialize GEE (will prompt for authentication if needed)
        print("\nInitializing Google Earth Engine...")
        loader.initialize()
        
        # Load datasets
        print("\nLoading soil property datasets...")
        images = loader.load_datasets()
        print(f"\nLoaded {len(images)} datasets: {list(images.keys())}")
        
        # Clip to Mato Grosso
        print("\nClipping datasets to Mato Grosso...")
        clipped_images = loader.clip_to_mato_grosso()
        print(f"\nClipped {len(clipped_images)} datasets to Mato Grosso boundaries")
        
        print("\nSTEP 2 completed successfully!")
        
        # STEP 3: Clipping to Mato Grosso State (already done in Step 2)
        print("""
============================================================
STEP 3: Clipping to Mato Grosso State
============================================================

Clipping already completed in Step 2
STEP 3 completed successfully!""")
        
        # STEP 4: Export to GeoTIFF Format
        print("""
============================================================
STEP 4: Export to GeoTIFF Format
============================================================""")
        
        # Get available layers from config
        available_layers = list(config.get("datasets", {}).keys())
        
        # Interactive layer selection
        print("""
------------------------------------------------------------
Layer Selection
------------------------------------------------------------""")
        
        # Show all available layers
        print("\nAvailable layers:")
        for idx, layer in enumerate(available_layers, 1):
            print(f"  {idx}. {layer}")
        
        while True:
            choice = input("\nDo you want to export all layers, just some, or none? (all/some/none): ").strip().lower()
            if choice in ['all', 'some', 'none']:
                break
            print("Please enter 'all', 'some', or 'none'")
        
        selected_layers = []
        if choice == 'none':
            print("\nSkipping export - no layers selected")
            selected_layers = []
        elif choice == 'all':
            selected_layers = available_layers
            print(f"\nSelected all {len(selected_layers)} layers")
        else:
            # Ask how many layers to select
            while True:
                try:
                    num_layers = int(input(f"\nHow many layers do you want to export? (1-{len(available_layers)}): ").strip())
                    if 1 <= num_layers <= len(available_layers):
                        break
                    print(f"Please enter a number between 1 and {len(available_layers)}")
                except ValueError:
                    print("Please enter a valid number")
            
            # Create a copy of available layers for selection (remove as they're selected)
            remaining_layers = available_layers.copy()
            
            # Ask for each layer one by one
            for i in range(num_layers):
                print(f"\n--- Selection {i+1} of {num_layers} ---")
                print("\nAvailable layers:")
                for idx, layer in enumerate(remaining_layers, 1):
                    print(f"  {idx}. {layer}")
                
                while True:
                    try:
                        layer_idx = int(input(f"\nSelect a layer (1-{len(remaining_layers)}): ").strip())
                        if 1 <= layer_idx <= len(remaining_layers):
                            selected_layer = remaining_layers[layer_idx - 1]
                            selected_layers.append(selected_layer)
                            remaining_layers.remove(selected_layer)
                            print(f"Selected: {selected_layer}")
                            break
                        else:
                            print(f"Please enter a number between 1 and {len(remaining_layers)}")
                    except ValueError:
                        print("Please enter a valid number")
            
            print(f"\nSelected {len(selected_layers)} layer(s): {', '.join(selected_layers)}")
        
        # Only export if layers were selected
        if selected_layers:
            try:
                # Create export tasks for selected layers only
                print("\nCreating export tasks...")
                tasks = loader.create_export_tasks(selected_layers=selected_layers)
                
                # Start export tasks
                print("\nStarting export tasks...")
                task_ids = loader.start_export_tasks()
                
                # Export tasks completed - user will download manually
                print("""
------------------------------------------------------------
Export tasks started successfully!
Files will be exported to Google Drive folder:
  https://drive.google.com/drive/folders/1IIBYV68TBZ2evWnUYgBZY9mKI2PalciE
------------------------------------------------------------

To download files manually:
  1. Wait for exports to complete in Google Earth Engine
  2. Check export status at: https://code.earthengine.google.com/
  3. Download files manually from the Google Drive folder (link above)
  4. Place downloaded files in the 'data/raw/' folder""")
                
                print("\nSTEP 4 completed successfully!")
            except Exception as e:
                print(f"""Error during export: {e}

Troubleshooting:
  1. Check that GEE export tasks are accessible
  2. Verify Google Drive API is enabled
  3. Check that you have sufficient Drive storage""")
                return 1
        else:
            print("\nSTEP 4 skipped (no layers selected for export)")
        
        print("""
============================================================
Data Loading Workflow Complete
============================================================

Next steps:
  1. Wait for exports to complete in Google Earth Engine
  2. Download files from Google Drive to data/raw/
  3. Run: python src/main.py to process the data
============================================================""")
        
    except ValueError as e:
        print(f"""Error: {e}

Please set gee.project_name in configs/config.yaml""")
        return 1
    except Exception as e:
        print(f"""Error during GEE initialization: {e}

Troubleshooting:
  1. Make sure you have earthengine-api installed: pip install earthengine-api
  2. Run: python -c 'import ee; ee.Authenticate()' to authenticate first""")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

