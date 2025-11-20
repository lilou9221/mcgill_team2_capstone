"""
Optional Data Acquisition Module (Template/Reference Only)

NOTE: This module is OPTIONAL. Data acquisition is done manually outside the codebase.
GeoTIFF files should be manually placed in data/raw/ directory.

This module serves as a TEMPLATE/REFERENCE showing how to export data from Google Earth Engine
if you need to obtain new data. It is NOT required for the core pipeline to function.

See README_TEMPLATE.md in this directory for usage instructions.
"""

from src.data.acquisition.gee_loader import GEEDataLoader

__all__ = ['GEEDataLoader']

