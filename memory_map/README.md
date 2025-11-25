# Developer Reference: Data Flow Memory Map

This folder contains architecture documentation for developers working on the Biochar Suitability Mapper.

## Quick Reference

The application has **4 core features**:

| Feature | Data Source | Output |
|---------|-------------|--------|
| **Farmer Maps** | GeoTIFF soil data (data/*.tif) | suitability_map.html, soc_map.html, ph_map.html, moisture_map.html |
| **Investor Map** | BR_Municipios_2024_simplified.shp + Crop CSV | investor_crop_area_map.html |
| **Biochar Yield Calculator** | residue_ratios.csv + harvest data | In-app calculation |
| **Biochar Recommendations** | pyrolysis/*.csv + soil scores | In-app recommendations |

## Files

| File | Description |
|------|-------------|
| `memory_map.py` | Python script to generate the data flow diagram |
| `data_flow_memory_map.png` | Visual flowchart of the processing pipeline |

## Regenerate Diagram

```bash
cd memory_map
python memory_map.py
```

Requires: `pip install matplotlib`

## Pipeline Overview

```
GeoTIFF Files (data/*.tif)
    │
    ▼
clip_all_rasters_to_circle (raster_clip.py)
    │
    ▼
convert_all_rasters_to_dataframes (raster_to_csv.py)
    │
    ▼
process_dataframes_with_h3 (h3_converter.py)
    │
    ▼
merge_and_aggregate_soil_data (suitability.py)
    │
    ├──► merged_soil_data.csv
    │         │
    │         ├──► create_soc_map ──► soc_map.html
    │         ├──► create_ph_map ──► ph_map.html
    │         └──► create_moisture_map ──► moisture_map.html
    │
    ▼
calculate_biochar_suitability_scores (biochar_suitability.py)
    │
    ▼
suitability_scores.csv
    │
    ▼
create_biochar_suitability_map ──► suitability_map.html
```

**Investor Map (separate pipeline):**

```
Municipality Shapefile + Crop CSV
    │
    ▼
prepare_investor_crop_area_geodata (municipality_waste_map.py)
    │
    ▼
create_municipality_waste_deck ──► investor_crop_area_map.html
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `src/main.py` | Main pipeline orchestration |
| `src/analyzers/biochar_suitability.py` | Suitability score calculation |
| `src/analyzers/biochar_recommender.py` | Feedstock recommendations |
| `src/analyzers/biomass_calculator.py` | Residue ratio loading |
| `src/data_processors/raster_clip.py` | GeoTIFF clipping |
| `src/data_processors/h3_converter.py` | H3 hexagonal indexing |
| `src/map_generators/*.py` | Map generation |
| `src/utils/cache.py` | Caching system |
| `streamlit_app.py` | Web interface |

## Diagram Legend

| Box Color | Meaning |
|-----------|---------|
| Light Blue | Files/Data |
| Light Orange | Processes/Functions |
| Light Green | Final Map Outputs |
| Arrows | Data flow direction |
