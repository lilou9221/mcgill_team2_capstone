"""
SMAP Downscaling Module

Bicubic resampling for SMAP data (3000m -> 250m).
"""

from typing import Dict, Optional
import ee


def resample_smap_to_250m(image: ee.Image, method: str = 'bicubic') -> ee.Image:
    """
    Resample SMAP image from native resolution (~3000m) to 250m using specified method.
    
    Parameters
    ----------
    image : ee.Image
        SMAP image to resample (soil moisture or temperature)
    method : str, optional
        Resampling method: 'bicubic' (default, best for continuous variables),
        'bilinear', or 'nearest'
    
    Returns
    -------
    ee.Image
        Resampled image at 250m resolution
    """
    # Target resolution in meters
    target_scale = 250
    
    # Reproject to 250m resolution using specified method
    # Bicubic is best for continuous variables like soil moisture/temperature
    resampled = image.resample(method).reproject(
        crs='EPSG:4326',
        scale=target_scale
    )
    
    return resampled


def downscale_smap_datasets(
    images: Dict[str, ee.Image],
    method: str = 'bicubic'
) -> Dict[str, ee.Image]:
    """
    Downscale SMAP datasets (soil moisture and temperature) to 250m resolution.
    
    Uses simple bicubic resampling for the data acquisition pipeline.
    
    Parameters
    ----------
    images : Dict[str, ee.Image]
        Dictionary of images, should include 'soil_moisture' and 'soil_temperature'
    method : str, optional
        Resampling method: 'bicubic' (default, best for continuous variables),
        'bilinear', or 'nearest'
    
    Returns
    -------
    Dict[str, ee.Image]
        Dictionary with downscaled SMAP images at 250m resolution
        Other images are returned unchanged
    """
    downscaled = {}
    smap_datasets = ['soil_moisture', 'soil_temperature']
    
    print(f"\nDownscaling SMAP datasets to 250m resolution using {method} resampling...")
    
    for name, image in images.items():
        if name in smap_datasets:
            print(f"  Downscaling {name} from ~3000m to 250m...")
            downscaled[name] = resample_smap_to_250m(image, method=method)
            print(f"  [OK] {name} downscaled to 250m using {method}")
        else:
            # Keep other datasets unchanged
            downscaled[name] = image
    
    print(f"\nDownscaling complete. {len([n for n in downscaled.keys() if n in smap_datasets])} dataset(s) downscaled to 250m using {method}")
    
    return downscaled

