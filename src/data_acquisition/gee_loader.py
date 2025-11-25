"""
Optional Google Earth Engine Data Loader Module (Template/Reference Only)

NOTE: This module is OPTIONAL. Data acquisition is done manually outside the codebase.
GeoTIFF files should be manually placed in data/ directory (flat structure).

This module serves as a TEMPLATE/REFERENCE showing how to export data from Google Earth Engine
if you need to obtain new data. It is NOT required for the core pipeline to function.

See README_TEMPLATE.md in this directory for usage instructions.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List, Union

import ee

try:
    import yaml
except ImportError:
    raise ImportError(
        "PyYAML is not installed. Please install it using: pip install pyyaml\n"
        "Or install all dependencies: pip install -r requirements.txt"
    )

# Import downscaling module (bicubic resampling only)
try:
    from src.data_acquisition.smap_downscaling import downscale_smap_datasets
except ImportError:
    # Fallback when running as script
    import sys
    SCRIPT_ROOT = Path(__file__).resolve().parents[3]
    if str(SCRIPT_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPT_ROOT))
    from src.data_acquisition.smap_downscaling import downscale_smap_datasets


# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Mapping from internal dataset names to simplified file names (matching biochar-brazil convention)
DATASET_NAME_MAPPING = {
    'soil_organic_carbon': 'SOC',
    'soil_temperature': 'soil_temp',
    'soil_moisture': 'soil_moisture',
    'soil_pH': 'soil_pH',
    'soil_type': 'soil_type',
    'land_cover': 'land_cover',
}

# Native resolutions for each dataset (in meters)
# Datasets with native resolution > 250m will be exported at native resolution
# Others will be exported at 250m
# Note: SMAP datasets (soil_moisture, soil_temperature) are downscaled to 250m
# before export, so they will export at 250m
DATASET_NATIVE_RESOLUTIONS = {
    'soil_moisture': 250,        # NASA SMAP downscaled to 250m
    'soil_temperature': 250,     # NASA SMAP downscaled to 250m
    'soil_organic_carbon': 250,  # OpenLandMap native ~250m
    'soil_pH': 250,              # OpenLandMap native ~250m
    'soil_type': 250,            # OpenLandMap native ~250m
    'land_cover': 10,            # ESA WorldCover native ~10m (will export at 250m)
}

# Default export resolution (250m)
DEFAULT_EXPORT_RESOLUTION = 250


# Datasets required for biochar suitability scoring
SCORING_REQUIRED_DATASETS = {
    'soil_moisture',      # Required for scoring
    'soil_organic_carbon',  # Required for scoring (b0 and b10)
    'soil_pH',            # Required for scoring (b0 and b10)
    'soil_temperature',   # Required for scoring
}

# Optional datasets (not used in scoring but may be useful for visualization/analysis)
OPTIONAL_DATASETS = {
    'land_cover',  # Not used in scoring
    'soil_type',   # Not used in scoring
}

# Specific datasets that require per-band exports (depth levels)
# Only export b0 and b10 for SOC and pH (used in scoring)
# soil_type is not used in scoring, so it's excluded from multi-band exports
MULTI_BAND_EXPORTS = {
    'soil_organic_carbon': ['b0', 'b10'],  # Only b0 and b10 used in scoring
    'soil_pH': ['b0', 'b10'],  # Only b0 and b10 used in scoring
    # Note: soil_type is not used in biochar suitability scoring
}


def get_scoring_required_datasets() -> List[str]:
    """
    Get list of datasets required for biochar suitability scoring.
    
    Returns
    -------
    List[str]
        List of dataset names required for scoring
    """
    return list(SCORING_REQUIRED_DATASETS)


def get_simplified_filename(dataset_name: str) -> str:
    """
    Get simplified filename for dataset (matching biochar-brazil convention).
    
    Parameters
    ----------
    dataset_name : str
        Internal dataset name
        
    Returns
    -------
    str
        Simplified filename (without extension)
    """
    return DATASET_NAME_MAPPING.get(dataset_name, dataset_name)


def get_export_resolution(dataset_name: str) -> int:
    """
    Get the export resolution for a dataset.
    Uses 250m by default, but keeps native resolution if it's > 250m.
    
    Parameters
    ----------
    dataset_name : str
        Internal dataset name
        
    Returns
    -------
    int
        Export resolution in meters
    """
    native_res = DATASET_NATIVE_RESOLUTIONS.get(dataset_name, DEFAULT_EXPORT_RESOLUTION)
    
    # If native resolution > 250m, use native; otherwise use 250m
    if native_res > DEFAULT_EXPORT_RESOLUTION:
        return native_res
    else:
        return DEFAULT_EXPORT_RESOLUTION


class GEEDataLoader:
    """
    Loads and standardizes soil property datasets from Google Earth Engine.
    Handles ImageCollections and Images, standardizes projections to EPSG:4326.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the GEE Data Loader.

        Parameters
        ----------
        config_path : str, optional
            Path to configuration file. Defaults to configs/config.yaml
        """
        # Get project root (parent of src directory)
        project_root = Path(__file__).parent.parent.parent.parent
        
        if config_path is None:
            config_path = project_root / "configs" / "config.yaml"
        else:
            config_path = Path(config_path)
            # If it's a relative path, resolve it relative to project root
            if not config_path.is_absolute():
                config_path = project_root / config_path

        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize attributes
        self.project_name = self.config.get("gee", {}).get("project_name")
        self.target_scale = self.config.get("gee", {}).get("default_scale", 1000)  # Fallback default
        self.feature = None
        self.images = {}
        self.images_names = []
        self.tasks = []
        # Store export resolutions for each dataset
        self.dataset_resolutions = {}
        # Human-readable task summaries for verification
        self.task_details: List[Dict[str, Optional[str]]] = []

    def _load_config(self) -> Dict:
        """
        Load configuration from YAML file.
        
        TEMPLATE: This will fail if config.yaml doesn't exist or doesn't have GEE credentials.
        User must create config.yaml from config.template.yaml and fill in their credentials.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"To use GEE export features:\n"
                f"  1. Copy configs/config.template.yaml to configs/config.yaml\n"
                f"  2. Fill in your GEE project_name and export_folder values\n"
                f"  3. See src/data/acquisition/README_TEMPLATE.md for instructions"
            )
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # Verify GEE credentials are present
            gee_config = config.get("gee", {})
            if not gee_config.get("project_name") or gee_config.get("project_name") == "YOUR_GEE_PROJECT_ID":
                raise ValueError(
                    "GEE project_name not configured in config.yaml\n"
                    "Please fill in your Google Earth Engine project ID in configs/config.yaml\n"
                    "See src/data/acquisition/README_TEMPLATE.md for instructions"
                )
            if not gee_config.get("export_folder") or gee_config.get("export_folder") == "YOUR_GOOGLE_DRIVE_FOLDER_ID":
                raise ValueError(
                    "GEE export_folder not configured in config.yaml\n"
                    "Please fill in your Google Drive folder ID in configs/config.yaml\n"
                    "See src/data/acquisition/README_TEMPLATE.md for instructions"
                )
            return config

    def initialize(self, project_name: Optional[str] = None) -> None:
        """
        Initialize Google Earth Engine.

        Parameters
        ----------
        project_name : str, optional
            GEE project name. If not provided, uses config file value.
        """
        if project_name:
            self.project_name = project_name
        elif self.project_name is None:
            raise ValueError(
                "GEE project name not set. "
                "Either provide project_name parameter or set gee.project_name in config.yaml"
            )

        try:
            # Try to initialize (may already be initialized)
            ee.Initialize(project=self.project_name)
            print(f"Google Earth Engine initialized with project: {self.project_name}")
        except Exception as e:
            # If not authenticated, authenticate first
            print("Authenticating with Google Earth Engine...")
            print("This will open a browser window for authentication.")
            ee.Authenticate()
            ee.Initialize(project=self.project_name)
            print(f"Google Earth Engine initialized with project: {self.project_name}")

    def get_dataset_images(self) -> Dict[str, ee.Image]:
        """
        Retrieve all soil property datasets from GEE based on config.

        Returns
        -------
        Dict[str, ee.Image]
            Dictionary mapping dataset names to ee.Image objects
        """
        datasets_config = self.config.get("datasets", {})
        images = {}

        for dataset_name, dataset_config in datasets_config.items():
            print(f"\nRetrieving {dataset_name}...")
            
            if "image" in dataset_config:
                # Single image
                image_id = dataset_config["image"]
                image = ee.Image(image_id)
                
                # Select specific band if provided (OpenLandMap images often have multiple bands)
                band = dataset_config.get("band", None)
                if band:
                    image = image.select(band)
                    print(f"  Selected band: {band}")
                
                images[dataset_name] = image
                print(f"  Loaded image: {image_id}")
                
            elif "collection" in dataset_config:
                # ImageCollection - need to process
                collection_id = dataset_config["collection"]
                band = dataset_config.get("band", None)
                date_range = dataset_config.get("date_range", None)
                aggregation_method = dataset_config.get("aggregation", "median")  # Default to median
                
                # Create collection
                collection = ee.ImageCollection(collection_id)
                
                # Filter by date if provided
                if date_range:
                    collection = collection.filterDate(date_range[0], date_range[1])
                
                # Select band if provided
                if band:
                    collection = collection.select(band)
                
                # Apply aggregation method
                if aggregation_method == "recent":
                    # Use most recent image only (fastest)
                    collection = collection.sort('system:time_start', False).limit(1)
                    images[dataset_name] = collection.first()
                    print(f"  Using most recent image")
                elif aggregation_method == "mean":
                    # Use mean (more accurate for continuous data)
                    images[dataset_name] = collection.mean()
                    print(f"  Using mean aggregation")
                else:
                    # Default to median (faster, good for categorical data)
                    images[dataset_name] = collection.median()
                    print(f"  Using median aggregation")
                
                print(f"  Loaded collection: {collection_id}")
                if date_range:
                    print(f"  Date range: {date_range[0]} to {date_range[1]}")
                if band:
                    print(f"  Selected band: {band}")
        
        print(f"\nRetrieved {len(images)} datasets")
        return images

    @staticmethod
    def _standardize_images(images: Dict[str, ee.Image]) -> Dict[str, ee.Image]:
        """
        Standardize images to EPSG:4326 projection.

        Parameters
        ----------
        images : Dict[str, ee.Image]
            Dictionary of images to standardize

        Returns
        -------
        Dict[str, ee.Image]
            Dictionary of standardized images
        """
        standardized = {}
        target_crs = 'EPSG:4326'
        
        # Define categorical layers (use nearest neighbor resampling)
        categorical_layers = {"land_cover", "soil_type"}

        for key_name, image in images.items():
            print(f"\nStandardizing {key_name}...")
            
            # Choose resampling method
            resample_method = 'nearest' if key_name in categorical_layers else 'bilinear'

            # Get projection info
            try:
                proj_info = image.projection().getInfo()
                crs = proj_info.get("crs", None)
                nominal_scale = proj_info.get("nominalScale", None)
                
                print(f"  Current CRS: {crs}")
                print(f"  Nominal scale: {nominal_scale}m" if nominal_scale else "  Nominal scale: N/A")

                # Reproject if needed
                if crs != target_crs or (nominal_scale and nominal_scale > 1000):
                    print(f"  Reprojecting to {target_crs} using {resample_method} resampling")
                    image = image.resample(resample_method).reproject(crs=target_crs)
                else:
                    print(f"  Already in {target_crs}")

            except Exception as e:
                print(f"  Could not retrieve CRS info: {e}")
                print(f"  Attempting reprojection to {target_crs} anyway")
                image = image.resample(resample_method).reproject(crs=target_crs)

            standardized[key_name] = image

        print("\nAll images standardized successfully")
        return standardized

    def load_datasets(self, downscale_smap: bool = True) -> Dict[str, ee.Image]:
        """
        Load and standardize all datasets from config.
        
        Optionally downscales SMAP datasets (soil moisture and temperature) 
        to 250m resolution using bicubic resampling.

        Parameters
        ----------
        downscale_smap : bool, optional
            If True (default), downscales SMAP datasets to 250m resolution using bicubic resampling.
            If False, keeps SMAP datasets at their original resolution.

        Returns
        -------
        Dict[str, ee.Image]
            Dictionary of standardized images ready for clipping/export
            
        """
        # Get raw images from GEE
        raw_images = self.get_dataset_images()
        
        # Standardize projections
        standardized_images = self._standardize_images(raw_images)
        
        # Downscale SMAP datasets to 250m if requested (simple bicubic only)
        if downscale_smap:
            standardized_images = downscale_smap_datasets(
                standardized_images,
                method='bicubic'
            )
        
        # Store images
        self.images = standardized_images
        self.images_names = list(standardized_images.keys())
        
        return standardized_images

    def clip_to_mato_grosso(self) -> Dict[str, ee.Image]:
        """
        Clip all images to Mato Grosso state boundaries.

        Returns
        -------
        Dict[str, ee.Image]
            Dictionary of clipped images
        """
        if not self.images:
            raise ValueError("No images loaded. Call load_datasets() first.")

        print("\nClipping images to Mato Grosso boundaries...")
        
        # Load Mato Grosso boundaries
        mato_grosso = (
            ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
            .filter(ee.Filter.eq('ADM1_NAME', 'Mato Grosso'))
        )
        
        self.feature = 'mato_grosso'
        
        # Clip all images
        clipped_images = {}
        for name, image in self.images.items():
            print(f"  Clipping {name}...")
            clipped_images[name] = image.clip(mato_grosso)
        
        # Update stored images
        self.images = clipped_images
        
        print("\nAll images clipped to Mato Grosso successfully")
        return clipped_images

    def get_region_geometry(self) -> ee.Geometry:
        """
        Get the geometry for Mato Grosso state.

        Returns
        -------
        ee.Geometry
            Geometry of Mato Grosso state
        """
        if self.feature == 'mato_grosso':
            return (
                ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level1")
                .filter(ee.Filter.eq('ADM1_NAME', 'Mato Grosso'))
                .geometry()
            )
        else:
            raise ValueError("Feature not set. Call clip_to_mato_grosso() first.")

    def set_export_scale(self, scale: int) -> None:
        """
        Set the target scale for export.

        Parameters
        ----------
        scale : int
            Scale in meters
        """
        self.target_scale = scale
        print(f"Export scale set to {scale} meters")

    def create_export_tasks(self, folder_name: Optional[str] = None, selected_layers: Optional[List[str]] = None) -> List[ee.batch.Task]:
        """
        Create export tasks for images to Google Drive.

        Parameters
        ----------
        folder_name : str, optional
            Folder name in Google Drive. Uses config default if not provided.
        selected_layers : List[str], optional
            List of layer names to export. If None, exports all loaded images.

        Returns
        -------
        List[ee.batch.Task]
            List of export tasks
        """
        if not self.images:
            raise ValueError("No images loaded. Call load_datasets() and clip_to_mato_grosso() first.")

        if folder_name is None:
            folder_name = self.config.get("gee", {}).get("export_folder")
            if folder_name is None:
                raise ValueError("Google Drive export folder ID not configured. Set 'gee.export_folder' in config.yaml or environment variables.")

        # Filter images by selected layers if provided
        images_to_export = self.images.copy()
        if selected_layers is not None:
            # Validate that all selected layers exist
            missing_layers = [layer for layer in selected_layers if layer not in self.images]
            if missing_layers:
                raise ValueError(f"Selected layers not found in loaded images: {missing_layers}")
            
            images_to_export = {name: image for name, image in images_to_export.items() if name in selected_layers}
            print(f"\nExporting {len(images_to_export)} of {len(self.images)} available layer(s)")
        else:
            print(f"\nExporting {len(images_to_export)} dataset(s) to Google Drive")

        # Get region geometry for export
        region = self.get_region_geometry()
        
        print(f"\nCreating export tasks for {len(images_to_export)} dataset(s)...")
        print(f"Export folder ID: '{folder_name}'")
        print(f"Export folder URL: https://drive.google.com/drive/folders/{folder_name}")
        print(f"Selected layers: {list(images_to_export.keys()) if images_to_export else 'None'}")
        
        self.tasks = []
        self.dataset_resolutions = {}
        self.task_details = []
        
        for name, image in images_to_export.items():
            # Get export resolution for this dataset (250m default, or native if > 250m)
            export_res = get_export_resolution(name)
            self.dataset_resolutions[name] = export_res
            
            # Use simplified filename (matching biochar-brazil convention)
            simplified_name = get_simplified_filename(name)
            
            # Add resolution suffix to filename
            filename_base = f"{simplified_name}_res_{export_res}"
            
            # Prepare image for export - ensure single band
            export_image = image
            
            # Only unmask OpenLandMap images (single images) that might have NoData issues
            # Don't unmask SMAP collections as they handle their own masking properly
            if name in ['soil_organic_carbon', 'soil_pH', 'soil_type']:
                # OpenLandMap images - unmask to handle potential NoData issues
                export_image = export_image.unmask()
            
            # Determine which bands to export
            bands_to_export: List[Optional[str]] = [None]
            available_bands: List[str] = []
            try:
                available_bands = export_image.bandNames().getInfo()
            except Exception as e:
                print(f"  Could not check bands for {name}: {e}")
                available_bands = []

            if name in MULTI_BAND_EXPORTS:
                desired_bands = MULTI_BAND_EXPORTS[name]
                bands_to_export = [band for band in desired_bands if not available_bands or band in available_bands]
                if not bands_to_export:
                    print(f"  None of the desired bands {desired_bands} found for {name}, skipping dataset.")
                    continue
            elif available_bands:
                # Default to first available band for other multi-band images
                bands_to_export = [available_bands[0]]

            for band in bands_to_export:
                if band is not None:
                    band_image = export_image.select(band)
                    filename = f"{filename_base}_{band}"
                    print(f"  Preparing band '{band}' for export")
                else:
                    band_image = export_image
                    filename = filename_base

                print(f"  Creating export task for {name} ({'band ' + band if band else 'single-band'})...")
                print(f"    Folder ID: {folder_name}")
                print(f"    Filename: {filename}.tif")
                print(f"    Resolution: {export_res}m")

                task = ee.batch.Export.image.toDrive(
                    image=band_image,
                    description=f"{filename}",
                    folder=folder_name,
                    fileNamePrefix=f"{filename}",
                    scale=export_res,
                    region=region,
                    crs='EPSG:4326',
                    fileFormat='GeoTIFF',
                    maxPixels=1e13  # Increase max pixels to avoid export limits for large regions
                )
                self.tasks.append(task)
                self.task_details.append({
                    "dataset": name,
                    "band": band,
                    "filename": filename,
                    "resolution": export_res,
                    "folder": folder_name,
                })
                print(f"  Created task for {name} -> {filename}.tif (resolution: {export_res}m)")

        print(f"\nCreated {len(self.tasks)} export task(s)")
        return self.tasks

    def start_export_tasks(self) -> List[str]:
        """
        Start all export tasks.

        Returns
        -------
        List[str]
            List of task IDs
        """
        if not self.tasks:
            raise ValueError("No tasks created. Call create_export_tasks() first.")

        print(f"\nStarting {len(self.tasks)} export task(s)...")
        
        task_ids = []
        for i, task in enumerate(self.tasks, 1):
            try:
                print(f"  Starting task {i}/{len(self.tasks)}...")
                task.start()
                task_id = task.id
                task_ids.append(task_id)
                print(f"  Started task: {task_id}")
            except Exception as e:
                print(f"  Error starting task {i}: {e}")
                raise

        print(f"\nAll {len(self.tasks)} task(s) started successfully")
        print("\nNote: Exports may take time to complete.")
        print("You can check task status in Google Earth Engine Code Editor:")
        print("  https://code.earthengine.google.com/")
        print(f"Or wait for automatic download (configured in STEP 4)")
        
        return task_ids

    def get_expected_file_names(self) -> List[str]:
        """
        Get list of expected file names for exports (simplified names with resolution suffix).

        Returns
        -------
        List[str]
            List of expected file name prefixes (without extension, e.g., "SOC_res_250")
        """
        if not self.images_names:
            return []
        
        expected = []
        
        for name in self.images_names:
            # Get export resolution for this dataset
            export_res = self.dataset_resolutions.get(name, get_export_resolution(name))
            
            # Use simplified filename (matching biochar-brazil convention)
            simplified_name = get_simplified_filename(name)
            
            if name in MULTI_BAND_EXPORTS:
                for band in MULTI_BAND_EXPORTS[name]:
                    expected.append(f"{simplified_name}_res_{export_res}_{band}")
            else:
                # Add resolution suffix
                filename = f"{simplified_name}_res_{export_res}"
                expected.append(filename)
        
        return expected


def _run_debug_mode():
    """Execute the verbose debug routine that exercises helper utilities."""
    print("=" * 60)
    print("Google Earth Engine Data Loader - Debug Mode")
    print("=" * 60)
    
    # Test utility functions (no GEE authentication required)
    print("\n" + "-" * 60)
    print("1. Testing utility functions (no GEE auth required):")
    print("-" * 60)
    
    print("\nTesting get_simplified_filename():")
    test_names = [
        ('soil_organic_carbon', 'SOC'),
        ('soil_temperature', 'soil_temp'),
        ('soil_moisture', 'soil_moisture'),
        ('soil_pH', 'soil_pH'),
        ('soil_type', 'soil_type'),
        ('land_cover', 'land_cover'),
        ('unknown_dataset', 'unknown_dataset'),  # Should return as-is
    ]
    
    for dataset_name, expected in test_names:
        result = get_simplified_filename(dataset_name)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: {dataset_name} -> {result} (expected {expected})")
    
    print("\nTesting get_export_resolution():")
    test_resolutions = [
        ('soil_moisture', 250),  # Downscaled to 250m
        ('soil_temperature', 250),  # Downscaled to 250m
        ('soil_organic_carbon', 250),  # Native = 250m
        ('soil_pH', 250),  # Native = 250m
        ('soil_type', 250),  # Native = 250m
        ('land_cover', 250),  # Native < 250m (10m), but exports at 250m
        ('unknown_dataset', 250),  # Default
    ]
    
    for dataset_name, expected in test_resolutions:
        result = get_export_resolution(dataset_name)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: {dataset_name} -> {result}m (expected {expected}m)")
    
    # Show dataset mappings
    print("\n" + "-" * 60)
    print("2. Dataset Name Mappings:")
    print("-" * 60)
    print("\nName Mappings:")
    for key, value in DATASET_NAME_MAPPING.items():
        print(f"  {key} -> {value}")
    
    print("\nNative Resolutions:")
    for key, value in DATASET_NATIVE_RESOLUTIONS.items():
        export_res = get_export_resolution(key)
        print(f"  {key}: {value}m native -> {export_res}m export")
    
    # Test config loading (if available)
    print("\n" + "-" * 60)
    print("3. Testing configuration loading:")
    print("-" * 60)
    try:
        loader = GEEDataLoader()
        print("  PASS: Successfully initialized GEEDataLoader")
        print(f"    Project name: {loader.project_name}")
        print(f"    Default scale: {loader.target_scale}m")
        print(f"    Config path: {loader.config_path}")
    except Exception as e:
        print(f"  FAIL: Could not initialize GEEDataLoader: {e}")
    
    print("\n" + "-" * 60)
    print("Note: Full GEE functionality requires authentication.")
    print("To test GEE operations, run with '--run'.")
    print("-" * 60)


def _parse_layers(layers_arg: Optional[str]) -> Optional[List[str]]:
    if layers_arg is None:
        return None
    parsed = [layer.strip() for layer in layers_arg.split(",") if layer.strip()]
    return parsed or None


def _prompt_dataset_subset(available_layers: List[str]) -> Optional[List[str]]:
    """
    Interactively ask the user how many datasets to export.
    
    Returns a list of layer names or None to keep all layers.
    """
    if not available_layers:
        return None

    print("\nAvailable datasets:")
    for idx, layer_name in enumerate(available_layers, start=1):
        print(f"  {idx}. {layer_name}")

    total = len(available_layers)
    while True:
        user_input = input(
            f"\nHow many datasets should be exported? (1-{total}, or 0 for all): "
        ).strip()
        if not user_input:
            # Default = all
            return None
        if not user_input.isdigit():
            print("  Please enter a numeric value.")
            continue
        count = int(user_input)
        if count == 0:
            return None
        if 1 <= count <= total:
            return available_layers[:count]
        print(f"  Please choose a number between 1 and {total}, or 0 for all.")


def run_acquisition_pipeline(
    config_path: Optional[str],
    export_folder: Optional[str],
    selected_layers: Optional[List[str]],
    start_tasks: bool,
    clip_region: bool
) -> None:
    """Execute the acquisition/export workflow."""
    loader = GEEDataLoader(config_path=config_path)
    loader.initialize()
    loader.load_datasets()
    
    if selected_layers is None:
        ordered_layers = list(loader.images.keys())
        subset = _prompt_dataset_subset(ordered_layers)
        if subset:
            selected_layers = subset
    
    if clip_region:
        loader.clip_to_mato_grosso()
    
    tasks = loader.create_export_tasks(
        folder_name=export_folder,
        selected_layers=selected_layers
    )
    
    if not tasks:
        print("\nNo export tasks were created. Nothing to do.")
        return
    
    expected_files = loader.get_expected_file_names()
    if expected_files:
        print("\nExpected output filenames:")
        for name in expected_files:
            print(f"  - {name}.tif")
    
    if loader.task_details:
        print("\nPrepared export tasks:")
        for idx, info in enumerate(loader.task_details, start=1):
            band_label = f"band {info['band']}" if info.get("band") else "single band"
            print(
                f"  {idx}. dataset='{info['dataset']}', {band_label}, "
                f"filename='{info['filename']}.tif', resolution={info['resolution']}m, "
                f"folder='{info['folder']}'"
            )
    else:
        print("\nNo task details available.")
    
    if start_tasks:
        print("\n'--start-tasks' provided: starting export tasks immediately.")
        loader.start_export_tasks()
    else:
        while True:
            user_choice = input("\nStart export tasks now? [y/n]: ").strip().lower()
            if user_choice not in {"y", "n"}:
                print("  Please respond with 'y' or 'n'.")
                continue
            if user_choice == "y":
                print("\nStarting export tasks...")
                loader.start_export_tasks()
            else:
                print(
                    "\nExport tasks created but not started. Launch them manually in the "
                    "Google Earth Engine Code Editor task panel or rerun with '--start-tasks'."
                )
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Google Earth Engine data acquisition for Residual Carbon."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config YAML (defaults to configs/config.yaml)."
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Google Drive folder ID for exports (overrides config)."
    )
    parser.add_argument(
        "--layers",
        type=str,
        default=None,
        help="Comma-separated list of dataset keys to export (defaults to all)."
    )
    parser.add_argument(
        "--start-tasks",
        action="store_true",
        help="Start export tasks immediately after creation."
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Skip clipping to Mato Grosso (exports full image extent)."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run debug diagnostics instead of launching the export pipeline."
    )
    
    args = parser.parse_args()
    
    if args.debug:
        _run_debug_mode()
    else:
        run_acquisition_pipeline(
            config_path=args.config,
            export_folder=args.folder,
            selected_layers=_parse_layers(args.layers),
            start_tasks=args.start_tasks,
            clip_region=(not args.no_clip)
        )

