"""
Soil Quality and Biochar Suitability Calculator

Evaluates soil quality and determines biochar suitability based on:
- Soil Moisture (%)
- Soil Organic Carbon (%)
- Soil pH
- Soil Temperature (°C)
"""

from typing import Dict, Tuple
import numpy as np


def get_biochar_suitability_color(score: float) -> Tuple[str, str]:
    """
    Get color hex code and suitability grade based on biochar suitability score.
    
    Parameters
    ----------
    score : float
        Biochar suitability score (0-100)
    
    Returns
    -------
    Tuple[str, str]
        (color_hex, suitability_grade)
        - color_hex: Hex color code (e.g., "#d32f2f")
        - suitability_grade: "High Suitability", "Moderate Suitability", 
          "Low Suitability", or "Not Suitable"
    """
    if score >= 76:
        return "#d32f2f", "High Suitability"
    elif score >= 51:
        return "#f57c00", "Moderate Suitability"
    elif score >= 26:
        return "#fbc02d", "Low Suitability"
    else:
        return "#388e3c", "Not Suitable"


def get_recommendation(grade: str) -> str:
    """
    Get recommendation text based on suitability grade.
    
    Parameters
    ----------
    grade : str
        Suitability grade
    
    Returns
    -------
    str
        Recommendation text
    """
    recommendations = {
        "High Suitability": "Very suitable – biochar highly recommended",
        "Moderate Suitability": "Suitable – biochar recommended",
        "Low Suitability": "Marginal – biochar may help",
        "Not Suitable": "Healthy soil – biochar not needed"
    }
    return recommendations.get(grade, "Unknown suitability")


def rate_soil_moisture(moisture: float) -> Tuple[int, str]:
    """
    Rate soil moisture on a 4-level scale.
    
    Parameters
    ----------
    moisture : float
        Soil moisture percentage (0-100)
    
    Returns
    -------
    Tuple[int, str]
        (score, rating)
        - score: 0 (Very Poor), 1 (Poor), 2 (Moderate), 3 (Good)
        - rating: "Very Poor", "Poor", "Moderate", or "Good"
    """
    if moisture < 20 or moisture > 80:
        return 0, "Very Poor"
    elif 20 <= moisture < 30 or 70 < moisture <= 80:
        return 1, "Poor"
    elif 30 <= moisture < 50 or 60 < moisture <= 70:
        return 2, "Moderate"
    else:  # 50 <= moisture <= 60
        return 3, "Good"


def rate_soil_organic_carbon(soc: float) -> Tuple[int, str]:
    """
    Rate soil organic carbon on a 4-level scale.
    
    Parameters
    ----------
    soc : float
        Soil organic carbon percentage
    
    Returns
    -------
    Tuple[int, str]
        (score, rating)
        - score: 0 (Very Poor), 1 (Poor), 2 (Moderate), 3 (Good)
        - rating: "Very Poor", "Poor", "Moderate", or "Good"
    """
    if soc < 1:
        return 0, "Very Poor"
    elif 1 <= soc < 2:
        return 1, "Poor"
    elif 2 <= soc < 4:
        return 2, "Moderate"
    else:  # soc >= 4
        return 3, "Good"


def rate_soil_ph(ph: float) -> Tuple[int, str]:
    """
    Rate soil pH on a 4-level scale.
    
    Parameters
    ----------
    ph : float
        Soil pH value
    
    Returns
    -------
    Tuple[int, str]
        (score, rating)
        - score: 0 (Very Poor), 1 (Poor), 2 (Moderate), 3 (Good)
        - rating: "Very Poor", "Poor", "Moderate", or "Good"
    """
    if ph < 3.0 or ph > 9.0:
        return 0, "Very Poor"
    elif 3.0 <= ph < 4.5 or 8.0 < ph <= 9.0:
        return 1, "Poor"
    elif 4.5 <= ph < 6.0 or 7.0 < ph <= 8.0:
        return 2, "Moderate"
    else:  # 6.0 <= ph <= 7.0
        return 3, "Good"


def rate_soil_temperature(temp: float) -> Tuple[int, str]:
    """
    Rate soil temperature on a 4-level scale.
    
    Parameters
    ----------
    temp : float
        Soil temperature in °C
    
    Returns
    -------
    Tuple[int, str]
        (score, rating)
        - score: 0 (Very Poor), 1 (Poor), 2 (Moderate), 3 (Good)
        - rating: "Very Poor", "Poor", "Moderate", or "Good"
    """
    if temp < 0 or temp > 35:
        return 0, "Very Poor"
    elif 0 <= temp < 10 or 30 < temp <= 35:
        return 1, "Poor"
    elif 10 <= temp < 15 or 25 < temp <= 30:
        return 2, "Moderate"
    else:  # 15 <= temp <= 25
        return 3, "Good"


def validate_inputs(moisture: float, soc: float, ph: float, temp: float) -> None:
    """
    Validate input values.
    
    Parameters
    ----------
    moisture : float
        Soil moisture percentage (0-100)
    soc : float
        Soil organic carbon percentage (should be >= 0)
    ph : float
        Soil pH value (typically 0-14)
    temp : float
        Soil temperature in °C
    
    Raises
    ------
    ValueError
        If any input is invalid
    """
    if moisture < 0 or moisture > 100:
        raise ValueError(f"Moisture must be between 0 and 100, got {moisture}")
    
    if soc < 0:
        raise ValueError(f"Soil organic carbon must be >= 0, got {soc}")
    
    if ph < 0 or ph > 14:
        raise ValueError(f"pH must be between 0 and 14, got {ph}")
    
    if np.isnan(moisture) or np.isnan(soc) or np.isnan(ph) or np.isnan(temp):
        raise ValueError("Input values cannot be NaN")


def calculate_soil_quality_for_biochar(
    moisture: float,
    soc: float,
    ph: float,
    temp: float
) -> Dict:
    """
    Calculate soil quality and biochar suitability based on four soil properties.
    
    This function evaluates soil quality and determines biochar suitability.
    Biochar is most beneficial in poor soils, so lower soil quality = higher suitability.
    
    Parameters
    ----------
    moisture : float
        Soil moisture percentage (0-100)
    soc : float
        Soil organic carbon percentage
    ph : float
        Soil pH value
    temp : float
        Soil temperature in °C
    
    Returns
    -------
    Dict
        Dictionary containing:
        - property_ratings: dict of {property: rating_string}
        - property_scores: dict of {property: score (0-3)}
        - weighted_scores: dict of {property: weighted_score}
        - total_weighted_score: float
        - maximum_possible_score: float (7.2)
        - soil_quality_index: float (0-100)
        - biochar_suitability_score: float (0-100)
        - suitability_grade: str (High/Moderate/Low/Not Suitable)
        - color_hex: str (e.g., "#d32f2f")
        - recommendation: str (recommendation text)
    
    Raises
    ------
    ValueError
        If input values are invalid
    """
    # Validate inputs
    validate_inputs(moisture, soc, ph, temp)
    
    # Define weights
    weights = {
        'moisture': 0.5,
        'soc': 1.0,
        'ph': 0.7,
        'temperature': 0.2
    }
    
    # Rate each property
    moisture_score, moisture_rating = rate_soil_moisture(moisture)
    soc_score, soc_rating = rate_soil_organic_carbon(soc)
    ph_score, ph_rating = rate_soil_ph(ph)
    temp_score, temp_rating = rate_soil_temperature(temp)
    
    # Calculate weighted scores
    weighted_scores = {
        'moisture': moisture_score * weights['moisture'],
        'soc': soc_score * weights['soc'],
        'ph': ph_score * weights['ph'],
        'temperature': temp_score * weights['temperature']
    }
    
    # Calculate total weighted score
    total_weighted_score = sum(weighted_scores.values())
    
    # Maximum possible score = 3 × (0.5 + 1.0 + 0.7 + 0.2) = 7.2
    maximum_possible_score = 3.0 * sum(weights.values())
    
    # Calculate soil quality index (0-100)
    soil_quality_index = (total_weighted_score / maximum_possible_score) * 100.0
    
    # Biochar suitability score = 100 - soil_quality_index
    # (Lower quality = Higher suitability for biochar)
    biochar_suitability_score = 100.0 - soil_quality_index
    
    # Get suitability grade and color
    color_hex, suitability_grade = get_biochar_suitability_color(biochar_suitability_score)
    recommendation = get_recommendation(suitability_grade)
    
    # Return comprehensive result dictionary
    return {
        'property_ratings': {
            'moisture': moisture_rating,
            'soc': soc_rating,
            'ph': ph_rating,
            'temperature': temp_rating
        },
        'property_scores': {
            'moisture': moisture_score,
            'soc': soc_score,
            'ph': ph_score,
            'temperature': temp_score
        },
        'weighted_scores': weighted_scores,
        'total_weighted_score': total_weighted_score,
        'maximum_possible_score': maximum_possible_score,
        'soil_quality_index': round(soil_quality_index, 2),
        'biochar_suitability_score': round(biochar_suitability_score, 2),
        'suitability_grade': suitability_grade,
        'color_hex': color_hex,
        'recommendation': recommendation
    }


if __name__ == "__main__":
    # Test with sample data
    print("Testing calculate_soil_quality_for_biochar...")
    print("=" * 60)
    
    # Test case from user
    result = calculate_soil_quality_for_biochar(moisture=15, soc=0.8, ph=5.0, temp=32)
    
    print("\nInput values:")
    print(f"  Moisture: 15%")
    print(f"  SOC: 0.8%")
    print(f"  pH: 5.0")
    print(f"  Temperature: 32°C")
    
    print("\nProperty Ratings:")
    for prop, rating in result['property_ratings'].items():
        score = result['property_scores'][prop]
        weighted = result['weighted_scores'][prop]
        print(f"  {prop.capitalize()}: {rating} (score: {score}, weighted: {weighted:.2f})")
    
    print("\nCalculated Values:")
    print(f"  Total Weighted Score: {result['total_weighted_score']:.2f}")
    print(f"  Maximum Possible Score: {result['maximum_possible_score']:.2f}")
    print(f"  Soil Quality Index: {result['soil_quality_index']}")
    print(f"  Biochar Suitability Score: {result['biochar_suitability_score']}")
    
    print("\nBiochar Suitability:")
    print(f"  Grade: {result['suitability_grade']}")
    print(f"  Color: {result['color_hex']}")
    print(f"  Recommendation: {result['recommendation']}")
    
    # Additional test cases
    print("\n" + "=" * 60)
    print("\nAdditional Test Cases:")
    
    test_cases = [
        {"moisture": 55, "soc": 5.0, "ph": 6.5, "temp": 20, "desc": "Good soil"},
        {"moisture": 25, "soc": 1.5, "ph": 5.5, "temp": 12, "desc": "Moderate soil"},
        {"moisture": 10, "soc": 0.5, "ph": 4.0, "temp": 5, "desc": "Poor soil"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        desc = case.pop("desc")
        result = calculate_soil_quality_for_biochar(**case)
        print(f"\n{i}. {desc}:")
        print(f"   Input: moisture={case['moisture']}%, soc={case['soc']}%, pH={case['ph']}, temp={case['temp']}°C")
        print(f"   Biochar Suitability: {result['biochar_suitability_score']:.1f} ({result['suitability_grade']})")
        print(f"   {result['recommendation']}")

