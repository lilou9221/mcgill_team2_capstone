"""
Data Processing Module

Handles data processing and transformation (Steps 5, 6, 7+).
"""

from src.data.processing.user_input import get_user_area_of_interest, print_area_summary
from src.data.processing.raster_clip import clip_all_rasters_to_circle, verify_clipping_success
from src.data.processing.raster_to_csv import (
    convert_all_rasters_to_dataframes,
    raster_to_dataframe,
)
from src.data.processing.h3_converter import (
    add_h3_to_dataframe,
    process_dataframes_with_h3,
)

__all__ = [
    'get_user_area_of_interest',
    'print_area_summary',
    'clip_all_rasters_to_circle',
    'verify_clipping_success',
    'raster_to_dataframe',
    'convert_all_rasters_to_dataframes',
    'add_h3_to_dataframe',
    'process_dataframes_with_h3',
]

