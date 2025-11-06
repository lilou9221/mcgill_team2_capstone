"""
Google Earth Engine Data Loader Module

Retrieves soil property datasets from Google Earth Engine.
Handles authentication, image retrieval, and standardization.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Union
import ee


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
DATASET_NATIVE_RESOLUTIONS = {
    'soil_moisture': 3000,      # NASA SMAP native ~3000m
    'soil_temperature': 3000,   # NASA SMAP native ~3000m
    'soil_organic_carbon': 250,  # OpenLandMap native ~250m
    'soil_pH': 250,              # OpenLandMap native ~250m
    'soil_type': 250,            # OpenLandMap native ~250m
    'land_cover': 10,            # ESA WorldCover native ~10m (will export at 250m)
}

# Default export resolution (250m)
DEFAULT_EXPORT_RESOLUTION = 250


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

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

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
                print(f"  Warning: Could not retrieve CRS info: {e}")
                print(f"  Attempting reprojection to {target_crs} anyway")
                image = image.resample(resample_method).reproject(crs=target_crs)

            standardized[key_name] = image

        print("\nAll images standardized successfully")
        return standardized

    def load_datasets(self) -> Dict[str, ee.Image]:
        """
        Load and standardize all datasets from config.

        Returns
        -------
        Dict[str, ee.Image]
            Dictionary of standardized images ready for clipping/export
        """
        # Get raw images from GEE
        raw_images = self.get_dataset_images()
        
        # Standardize projections
        standardized_images = self._standardize_images(raw_images)
        
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
            folder_name = self.config.get("gee", {}).get("export_folder", "1IIBYV68TBZ2evWnUYgBZY9mKI2PalciE")

        # Filter images by selected layers if provided
        images_to_export = self.images
        if selected_layers is not None:
            # Validate that all selected layers exist
            missing_layers = [layer for layer in selected_layers if layer not in self.images]
            if missing_layers:
                raise ValueError(f"Selected layers not found in loaded images: {missing_layers}")
            
            images_to_export = {name: image for name, image in self.images.items() if name in selected_layers}
            print(f"\nExporting {len(images_to_export)} of {len(self.images)} available layer(s)")

        # Get region geometry
        region = self.get_region_geometry()
        
        print(f"\nCreating export tasks for {len(images_to_export)} dataset(s)...")
        print(f"Export folder ID: '{folder_name}'")
        print(f"Export folder URL: https://drive.google.com/drive/folders/{folder_name}")
        print(f"Selected layers: {list(images_to_export.keys()) if images_to_export else 'None'}")
        
        self.tasks = []
        self.dataset_resolutions = {}
        
        for name, image in images_to_export.items():
            # Get export resolution for this dataset (250m default, or native if > 250m)
            export_res = get_export_resolution(name)
            self.dataset_resolutions[name] = export_res
            
            # Use simplified filename (matching biochar-brazil convention)
            simplified_name = get_simplified_filename(name)
            
            # Add resolution suffix to filename
            filename = f"{simplified_name}_res_{export_res}"
            
            # Prepare image for export - ensure single band
            export_image = image
            
            # Only unmask OpenLandMap images (single images) that might have NoData issues
            # Don't unmask SMAP collections as they handle their own masking properly
            if name in ['soil_organic_carbon', 'soil_pH', 'soil_type']:
                # OpenLandMap images - unmask to handle potential NoData issues
                export_image = export_image.unmask()
            
            # Check if image has multiple bands and select first one if needed
            try:
                band_names = export_image.bandNames().getInfo()
                if len(band_names) > 1:
                    print(f"  Warning: {name} has {len(band_names)} bands, selecting first band: {band_names[0]}")
                    export_image = export_image.select(band_names[0])
            except Exception as e:
                print(f"  Warning: Could not check bands for {name}: {e}")
                # Continue with export_image as-is
            
            # Create export task with proper parameters
            print(f"  Creating export task for {name}...")
            print(f"    Folder ID: {folder_name}")
            print(f"    Filename: {filename}.tif")
            print(f"    Resolution: {export_res}m")
            
            task = ee.batch.Export.image.toDrive(
                image=export_image,
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
            
            # Add resolution suffix
            filename = f"{simplified_name}_res_{export_res}"
            expected.append(filename)
        
        return expected


if __name__ == "__main__":
    """Debug and test GEE Data Loader functionality."""
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
        ('soil_moisture', 3000),  # Native > 250m
        ('soil_temperature', 3000),  # Native > 250m
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
    from src.data.gee_loader import DATASET_NAME_MAPPING, DATASET_NATIVE_RESOLUTIONS
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
    print("To test GEE operations, run: python src/main.py")
    print("-" * 60)

