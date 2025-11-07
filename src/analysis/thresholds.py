# Biochar Suitability Thresholds
# Derived from FAO Soil Diagnostic Guidelines (A0541E) and project analysis

soil_moisture:
  # Water availability for crops and microbial life
  optimal_min: 0.2            # Udic regime (>90 moist days/year)
  optimal_max: 0.4
  acceptable_min: 0.1
  acceptable_max: 0.6
  unit: "m3/m3"
  notes: "Below 0.1 indicates aridic stress; above 0.6 may lead to waterlogging."

soil_organic_carbon:
  # Soil fertility, structure, and biodiversity indicator
  optimal_min: 3.0            # % (approx. dark grey Munsell 4)
  optimal_max: 9.0
  acceptable_min: 1.0
  acceptable_max: 12.0
  unit: "%"
  notes: "Values >12% (black Munsell 2–2.5) indicate highly fertile organic soils."

soil_pH:
  # Nutrient availability and microbial activity
  optimal_min: 5.5
  optimal_max: 7.5
  acceptable_min: 4.2
  acceptable_max: 8.5
  unit: "pH"
  notes: "Acidic below 4.2 (Dystric); alkaline above 8.5 may limit micronutrients."

soil_temperature:
  # Root growth and biotic activity
  optimal_min: 278.15         # Kelvin (5°C)
  optimal_max: 308.15         # Kelvin (35°C)
  acceptable_min: 273.15      # 0°C
  acceptable_max: 313.15      # 40°C
  unit: "K"
  notes: "Below 278K limits germination; above 313K stresses microbial communities."

electrical_conductivity:
  # Salinity indicator (ECSE 25°C)
  optimal_min: 0.0
  optimal_max: 0.75
  acceptable_min: 0.0
  acceptable_max: 4.0
  unit: "dS/m"
  notes: "Values >4 dS/m cause salinity stress; >15 extremely saline."

soil_texture:
  # Particle size distribution and aeration
  optimal_classes: ["loam", "silt loam", "sandy loam"]
  acceptable_classes: ["sandy clay loam", "clay loam", "silt clay loam"]
  notes: "Extreme sands or clays have poor water retention or drainage."

bulk_density:
  # Soil compaction and porosity
  optimal_max: 1.4             # g/cm3 (loam/clay)
  acceptable_max: 1.6          # g/cm3 (sandy)
  unit: "g/cm3"
  notes: "Higher densities reduce root penetration and infiltration."

redox_potential:
  # Aeration and nutrient redox balance
  optimal_min: 20
  acceptable_min: 13
  unit: "rH"
  notes: "rH < 13 indicates anaerobic conditions, possible sulfide formation."

land_cover:
  # Surface vegetation or land use suitability
  optimal_classes: ["cropland", "grassland", "forest"]
  acceptable_classes: ["shrubland", "mosaic"]
  unsuitable_classes: ["urban", "bare", "water"]
  notes: "Land cover impacts carbon sequestration potential and biochar application."

surface_indicators:
  # Qualitative visual indicators (for field surveys)
  avoid_conditions: ["crusting", "massive structure", "wide deep cracks"]
  preferred_conditions: ["granular structure", "visible pores"]
  notes: "Crusting or massive structure indicates compaction and poor infiltration."
