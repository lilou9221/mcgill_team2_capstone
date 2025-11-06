"""
Color Scheme Module

Defines color mapping for suitability scores.
"""

from typing import Tuple, Optional
import numpy as np


def get_color_for_score(score: float, color_scheme: str = "default") -> str:
    """
    Get color for a suitability score.
    
    Color scheme:
    - Green (8-10): Most suitable
    - Yellow (5-7): Moderately suitable
    - Red (0-4): Least suitable
    
    Parameters
    ----------
    score : float
        Suitability score (0-10)
    color_scheme : str, optional
        Color scheme name (default: "default")
    
    Returns
    -------
    str
        Hex color code (e.g., "#00FF00")
    """
    if np.isnan(score):
        return "#808080"  # Gray for NaN
    
    score = float(score)
    
    if score >= 8.0:
        # Green: Most suitable (8-10)
        # Interpolate from light green (8) to dark green (10)
        ratio = (score - 8.0) / 2.0  # 0 to 1
        # Light green (#90EE90) to dark green (#006400)
        r = int(144 - (144 - 0) * ratio)
        g = int(238 - (238 - 100) * ratio)
        b = int(144 - (144 - 0) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"
    
    elif score >= 5.0:
        # Yellow: Moderately suitable (5-7)
        # Interpolate from red-yellow (5) to yellow-green (7)
        ratio = (score - 5.0) / 2.0  # 0 to 1
        # Red-yellow (#FFD700) to yellow-green (#ADFF2F)
        r = int(255 - (255 - 173) * ratio)
        g = int(215 + (255 - 215) * ratio)
        b = int(0 + (47 - 0) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"
    
    else:
        # Red: Least suitable (0-4)
        # Interpolate from dark red (0) to light red (4)
        ratio = score / 4.0  # 0 to 1
        # Dark red (#8B0000) to light red (#FF6B6B)
        r = int(139 + (255 - 139) * ratio)
        g = int(0 + (107 - 0) * ratio)
        b = int(0 + (107 - 0) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"


def get_color_rgb(score: float) -> Tuple[int, int, int]:
    """
    Get RGB color tuple for a suitability score.
    
    Parameters
    ----------
    score : float
        Suitability score (0-10)
    
    Returns
    -------
    Tuple[int, int, int]
        RGB color tuple (0-255)
    """
    hex_color = get_color_for_score(score)
    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_color_scheme_info() -> dict:
    """
    Get information about the color scheme.
    
    Returns
    -------
    dict
        Color scheme information
    """
    return {
        "ranges": [
            {"min": 8.0, "max": 10.0, "color": "#006400", "label": "Most Suitable (8-10)"},
            {"min": 5.0, "max": 7.99, "color": "#FFD700", "label": "Moderately Suitable (5-7)"},
            {"min": 0.0, "max": 4.99, "color": "#8B0000", "label": "Least Suitable (0-4)"},
        ],
        "description": "Green = most suitable, Yellow = moderately suitable, Red = least suitable"
    }

