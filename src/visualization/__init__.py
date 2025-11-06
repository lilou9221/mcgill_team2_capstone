"""
Visualization Module

Creates interactive maps with suitability scores.
"""

from src.visualization.map_generator import create_suitability_map
from src.visualization.color_scheme import get_color_for_score, get_color_rgb, get_color_scheme_info

__all__ = [
    'create_suitability_map',
    'get_color_for_score',
    'get_color_rgb',
    'get_color_scheme_info'
]
