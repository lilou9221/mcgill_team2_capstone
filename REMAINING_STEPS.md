# Remaining Steps - Residual_Carbon Project

This document outlines all remaining steps after STEP 4 (Export to GeoTIFF Format).

## Completed Steps

- **STEP 1**: Project Structure Setup [COMPLETED]
- **STEP 2**: Google Earth Engine Data Retrieval [COMPLETED]
- **STEP 3**: Clipping to Mato Grosso State [COMPLETED]
- **STEP 4**: Export to GeoTIFF Format [COMPLETED]
- **STEP 5**: User Interface - Coordinate Input [COMPLETED]
- **STEP 6**: Radius Clipping (100km circles) [COMPLETED]
- **STEP 7**: Convert Maps to CSV (within circles) [COMPLETED]
- **STEP 8**: H3 Index Conversion [COMPLETED]

---

## STEP 5: User Interface - Coordinate Input

**Goal**: Create interface for user to specify area of interest

**Status**: Completed

**Tasks**:
- Enhance CLI to accept coordinate input (already partially implemented in main.py)
- Validate coordinate inputs (latitude: -90 to 90, longitude: -180 to 180)
- Validate that coordinates are within Mato Grosso bounds
- Store user preferences (coordinates and radius)
- Add option to skip coordinate input (use full state)

**Files to Create/Modify**:
- `src/utils/coordinate_validator.py` - Validate coordinates
- `src/main.py` - Enhance CLI argument parsing
- `src/data/user_input.py` - Handle user input processing

**Key Functions**:
```python
def validate_coordinates(lat: float, lon: float) -> bool
def is_within_mato_grosso(lat: float, lon: float) -> bool
def get_user_area_of_interest(lat: Optional[float], lon: Optional[float], radius_km: float) -> AreaOfInterest
```

---

## STEP 6: Radius Clipping (100km circles)

**Goal**: Clip GeoTIFFs to user-specified circles

**Status**: Completed

**Tasks**:
- If coordinates provided:
  - Create 100km radius buffer around point
  - Convert to Shapely geometry
  - Clip all GeoTIFF files to this circle using rasterio
  - Save clipped versions to `data/processed/`
- If no coordinates:
  - Use full state data (already in `data/raw/`)
- Handle coordinate transformations (WGS84 to projected CRS if needed)
- Verify clipping success

**Files to Create/Modify**:
- `src/data/raster_clip.py` - Implement circle clipping for GeoTIFFs
- `src/utils/geospatial.py` - Helper functions for geometry operations

**Key Functions**:
```python
def create_circle_buffer(lat: float, lon: float, radius_km: float) -> Geometry
def clip_raster_to_circle(tif_path: Path, circle_geometry: Geometry, output_path: Path) -> Path
def clip_all_rasters_to_circle(input_dir: Path, output_dir: Path, circle_geometry: Geometry) -> List[Path]
```

**Dependencies**:
- rasterio (already in requirements.txt)
- shapely (already in requirements.txt)
- geopandas (already in requirements.txt)

---

## STEP 7: Convert Maps to CSV (within circles)

**Goal**: Convert clipped GeoTIFFs to CSV format

**Status**: Completed

**Tasks**:
- Extract pixel values from clipped rasters
- Create CSV with columns: lon, lat, value for each soil property
- Handle nodata values (skip or convert to NaN)
- Merge spatial coordinates across all datasets
- Save individual CSV files per dataset OR one merged CSV
- Validate CSV output

**Files to Create/Modify**:
- `src/data/raster_to_csv.py` - Convert raster to CSV (can reuse from biochar-brazil)
- `src/data/csv_merger.py` - Merge multiple CSV files by coordinates

**Key Functions**:
```python
def raster_to_csv(tif_path: Path, output_csv: Path, band: int = 1) -> pd.DataFrame
def merge_csv_files_by_coordinates(csv_files: List[Path], output_csv: Path) -> pd.DataFrame
def handle_nodata_values(df: pd.DataFrame, nodata_handling: str) -> pd.DataFrame
```

**Output Format**:
- CSV files in `data/processed/` with columns: `lon`, `lat`, `soil_moisture`, `soil_type`, `soil_temperature`, `soil_organic_carbon`, `soil_pH`, `land_cover`

---

## STEP 8: H3 Index Conversion

**Goal**: Convert coordinates to H3 hexagonal grid

**Status**: Completed

**Tasks**:
- Install and configure H3 library (already in requirements.txt)
- Convert lat/lon to H3 indexes using configurable resolution (default: 6)
- Generate H3 polygons (hexagon boundaries) for visualization
- Aggregate data by H3 hexagons if multiple points per hexagon
- Store H3 index and polygon data in CSV
- Create GeoJSON for H3 polygons (optional, for visualization)

**Files to Create/Modify**:
- `src/data/h3_converter.py` - H3 index conversion and polygon generation
- `src/data/preprocessing.py` - H3 preprocessing and aggregation

**Key Functions**:
```python
def add_h3_index(df: pd.DataFrame, resolution: int = 6) -> pd.DataFrame
def get_h3_polygon(h3_index: str) -> List[List[float]]
def aggregate_by_h3_hexagon(df: pd.DataFrame, aggregation_method: str = 'mean') -> pd.DataFrame
```

**Output Format**:
- Enhanced CSV with columns: `lon`, `lat`, `h3_index`, `h3_boundary_geojson`, plus all soil properties

---

## STEP 9: Biochar Thresholds Database

**Goal**: Create/load database with soil property thresholds

**Status**: Not Started

**Tasks**:
- Design database structure for thresholds (YAML or JSON)
- Define optimal ranges for soil properties with thresholds:
  - Soil moisture (optimal range)
  - Soil temperature (optimal range)
  - Soil organic carbon (optimal range)
  - Soil pH (optimal range)
- Note: Land cover and soil type are useful but will be handled later (not included in initial thresholds)
- Create scoring system (0-10 scale) with thresholds
- Load biochar outputs database (feedstock properties) - if available
- Create configuration file for thresholds
- Allow user to customize thresholds

**Files to Create/Modify**:
- `configs/thresholds.yaml` - Threshold definitions
- `src/analysis/thresholds.py` - Load and manage thresholds
- `data/external/biochar_outputs.csv` - Biochar properties database (if provided)

**Threshold Structure Example**:
```yaml
soil_moisture:
  optimal_min: 0.2
  optimal_max: 0.4
  acceptable_min: 0.1
  acceptable_max: 0.5
  scoring:
    high: [0.2, 0.4]  # Score 8-10
    medium: [0.1, 0.2] or [0.4, 0.5]  # Score 5-7
    low: [0.0, 0.1] or [0.5, 1.0]  # Score 0-4

soil_temperature:
  optimal_min: 20.0
  optimal_max: 30.0
  # ... similar structure

soil_organic_carbon:
  optimal_min: 2.0
  optimal_max: 5.0
  # ... similar structure

soil_pH:
  optimal_min: 6.0
  optimal_max: 7.5
  # ... similar structure

# Note: land_cover and soil_type will be handled later
```

---

## STEP 10: Suitability Score Calculator

**Goal**: Calculate suitability scores based on thresholds

**Status**: Not Started

**Tasks**:
- Implement scoring algorithm:
  - Compare soil properties to thresholds (moisture, temperature, organic carbon, pH only)
  - Calculate individual scores for each property (0-10 scale)
  - Weight and combine scores (weighted average or other method)
  - Generate final suitability score (0-10)
- Note: Land cover and soil type are available in data but not used in scoring initially
- Handle multiple soil layers (if applicable)
- Incorporate biochar output data (if available)
- Handle missing data (NaN values)
- Validate scores are within 0-10 range

**Files to Create/Modify**:
- `src/analysis/suitability.py` - Main suitability scoring algorithm
- `src/analysis/scoring.py` - Individual property scoring functions
- `src/analysis/weighting.py` - Score weighting and combination

**Key Functions**:
```python
def calculate_property_score(value: float, thresholds: Dict) -> float
def calculate_suitability_score(df: pd.DataFrame, thresholds: Dict, weights: Dict) -> pd.DataFrame
def apply_biochar_considerations(df: pd.DataFrame, biochar_data: pd.DataFrame) -> pd.DataFrame
```

**Scoring Method**:
- For each property: calculate score based on distance from optimal range
- Weighted combination: weighted average of all property scores
- Final score: 0-10 scale where 10 = most suitable

**Output Format**:
- CSV with columns: `lon`, `lat`, `h3_index`, `suitability_score`, plus all individual property scores

---

## STEP 11: Visualization - Color-Coded Map

**Goal**: Create interactive map with suitability scores

**Status**: Not Started

**Tasks**:
- Generate color scheme:
  - Green = most suitable (score 8-10)
  - Yellow = moderately suitable (score 5-7)
  - Red = least suitable (score 0-4)
- Create interactive HTML map using Folium or PyDeck
- Display H3 hexagons colored by suitability score
- Add legend and grade scale (0-10)
- Include tooltips with score details (hover over hexagons)
- Add base map layers (satellite, terrain)
- Add control for zoom and pan

**Files to Create/Modify**:
- `src/visualization/map_generator.py` - Main map generation
- `src/visualization/color_scheme.py` - Color mapping functions
- `src/visualization/folium_map.py` - Folium implementation (or PyDeck)

**Key Functions**:
```python
def get_color_for_score(score: float) -> str
def create_suitability_map(df: pd.DataFrame, output_path: Path) -> str
def add_hexagon_layer(map_obj, df: pd.DataFrame) -> None
def add_legend(map_obj, color_scheme: Dict) -> None
```

**Output Format**:
- Interactive HTML file in `output/html/suitability_map.html`

---

## STEP 12: HTML Output and Auto-Open

**Goal**: Generate HTML file and open it automatically

**Status**: Not Started

**Tasks**:
- Save map as HTML file
- Automatically open HTML in default browser using `webbrowser` module
- Add styling and interactivity (already in Folium/PyDeck)
- Include metadata (date, input parameters, etc.)
- Add footer with project information
- Handle browser opening errors gracefully

**Files to Create/Modify**:
- `src/visualization/map_generator.py` - Enhance with auto-open functionality
- `src/utils/browser.py` - Browser opening utilities

**Key Functions**:
```python
def save_and_open_html(html_content: str, output_path: Path) -> None
def open_html_in_browser(file_path: Path) -> None
def add_metadata_to_html(html_content: str, metadata: Dict) -> str
```

**Metadata to Include**:
- Generation date/time
- Analysis area (coordinates or "Full State")
- Radius (if applicable)
- Number of datasets processed
- H3 resolution used
- Thresholds version

---

## STEP 13: Main Pipeline Integration

**Goal**: Connect all components into a single workflow

**Status**: Partially Complete (STEPS 1-4 integrated)

**Tasks**:
- Create main.py that orchestrates all steps (already started)
- Add error handling and logging throughout
- Create unified CLI interface (already started)
- Add progress indicators for long-running operations
- Add option to skip completed steps (resume functionality)
- Test end-to-end workflow
- Add configuration for skipping steps
- Add verbose/debug mode

**Files to Create/Modify**:
- `src/main.py` - Enhance with all steps
- `src/utils/logging.py` - Logging configuration
- `src/utils/progress.py` - Progress indicators

**Key Features**:
- Pipeline resume capability (skip already-completed steps)
- Error recovery (continue from last successful step)
- Progress reporting
- Configuration validation

---

## STEP 14: Testing and Documentation

**Goal**: Ensure tool works correctly and is documented

**Status**: Not Started

**Tasks**:
- Test with different coordinate inputs
- Test with no coordinates (full state)
- Validate suitability scores (check they're in 0-10 range)
- Test edge cases (coordinates outside Mato Grosso, invalid inputs)
- Create user documentation
- Add code comments and docstrings throughout
- Create example workflows
- Add troubleshooting guide

**Files to Create/Modify**:
- `tests/test_suitability.py` - Unit tests
- `tests/test_geospatial.py` - Geospatial tests
- `docs/USER_GUIDE.md` - User documentation
- `docs/API_REFERENCE.md` - API documentation
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide

**Test Cases**:
1. Full state analysis (no coordinates)
2. 100km radius with coordinates
3. Invalid coordinates (outside bounds)
4. Missing data handling
5. Empty exports
6. Large dataset performance

---

## Implementation Order Recommendation

1. **STEP 5** - User Interface (quick, builds on existing CLI)
2. **STEP 6** - Radius Clipping (needed for coordinate-based analysis)
3. **STEP 7** - Convert to CSV (needed for all downstream steps)
4. **STEP 8** - H3 Index Conversion (needed for visualization)
5. **STEP 9** - Thresholds Database (needed for scoring)
6. **STEP 10** - Suitability Calculator (core functionality)
7. **STEP 11** - Visualization (uses scores from STEP 10)
8. **STEP 12** - Auto-Open (simple addition to STEP 11)
9. **STEP 13** - Pipeline Integration (integrates all steps)
10. **STEP 14** - Testing and Documentation (final polish)

---

## Notes

- Steps can be implemented incrementally and tested independently
- Each step should have clear inputs and outputs
- Error handling should be added at each step
- Configuration should be centralized in `configs/config.yaml`
- Logging should be added throughout for debugging

