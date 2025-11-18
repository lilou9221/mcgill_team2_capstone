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


def get_color_for_biochar_suitability(score: float) -> str:
    """
    Get color for a biochar suitability score (0-100, displayed as 0-10).
    
    Biochar suitability color scheme (inverted - green for high, red for low):
    - Green (76-100 / 7.6-10.0): High suitability - poor soil needs biochar
    - Yellow-Green (51-75 / 5.1-7.5): Moderate-high suitability
    - Yellow-Orange (26-50 / 2.6-5.0): Low-moderate suitability
    - Red (0-25 / 0-2.5): Not suitable - healthy soil doesn't need biochar
    
    Parameters
    ----------
    score : float
        Biochar suitability score (0-100, internally converted to 0-10 scale)
    
    Returns
    -------
    str
        Hex color code (e.g., "#388e3c")
    """
    if np.isnan(score):
        return "#808080"  # Gray for NaN
    
    score = float(score)
    
    if score >= 76:  # 7.6-10.0 on 0-10 scale
        # High Suitability - Green
        # Interpolate from medium green (76/7.6) to dark green (100/10.0)
        ratio = (score - 76) / 24.0  # 0 to 1
        # Medium green (#388e3c) to dark green (#2e7d32)
        r = int(56 - (56 - 46) * ratio)
        g = int(142 - (142 - 125) * ratio)
        b = int(60 - (60 - 50) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"
    
    elif score >= 51:  # 5.1-7.5 on 0-10 scale
        # Moderate-High Suitability - Yellow to Yellow-Green
        # Interpolate from yellow (51/5.1) to yellow-green (75/7.5)
        ratio = (score - 51) / 24.0  # 0 to 1
        # Yellow (#FFD700) to yellow-green (#ADFF2F)
        r = int(255 - (255 - 173) * ratio)
        g = int(215 + (255 - 215) * ratio)
        b = int(0 + (47 - 0) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"
    
    elif score >= 26:  # 2.6-5.0 on 0-10 scale
        # Low-Moderate Suitability - Orange to Yellow
        # Interpolate from orange (26/2.6) to yellow (50/5.0)
        ratio = (score - 26) / 24.0  # 0 to 1
        # Orange (#FF9800) to yellow (#FFD700)
        r = int(255)  # Keep red at max
        g = int(152 + (215 - 152) * ratio)  # Increase green
        b = int(0)  # Keep blue at 0
        return f"#{r:02X}{g:02X}{b:02X}"
    
    else:  # 0-25 / 0-2.5 on 0-10 scale
        # Not Suitable - Red
        # Interpolate from dark red (0) to light red (25/2.5)
        ratio = score / 25.0  # 0 to 1
        # Dark red (#8B0000) to light red (#FF6B6B)
        r = int(139 + (255 - 139) * ratio)
        g = int(0 + (107 - 0) * ratio)
        b = int(0 + (107 - 0) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"


def get_biochar_suitability_color_rgb(score: float) -> Tuple[int, int, int]:
    """
    Get RGB color tuple for a biochar suitability score.
    
    Parameters
    ----------
    score : float
        Biochar suitability score (0-100)
    
    Returns
    -------
    Tuple[int, int, int]
        RGB color tuple (0-255)
    """
    hex_color = get_color_for_biochar_suitability(score)
    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


