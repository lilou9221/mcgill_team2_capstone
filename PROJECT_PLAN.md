# Biochar Suitability Mapping Tool - Step-by-Step Plan

## Project Overview
Tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and biochar outputs.

## Data Inputs
- **Soil Properties** (from Google Earth Engine):
  - Soil moisture
  - Soil type
  - Soil temperature
  - Soil organic carbon (SOC)
  - Soil pH
  - Land cover
- **Biochar Outputs**: Feedstock-specific properties (database to be provided)

## Geographic Focus
- Primary region: Mato Grosso state, Brazil
- User can specify coordinates for 100km radius analysis
- If no coordinates provided, analyze entire state

---

## Step-by-Step Implementation Plan

### **STEP 1: Project Structure Setup**
**Goal**: Create the folder structure and basic configuration files
- Create directory structure (src, data, configs, output, etc.)
- Create requirements.txt with dependencies
- Create config.yaml for settings
- Create README.md with project description
- Initialize git repository

---

### **STEP 2: Google Earth Engine Data Retrieval Module**
**Goal**: Retrieve soil property datasets from GEE
- Create GEE authentication and initialization
- Define functions to retrieve each soil property:
  - Soil moisture (NASA/SMAP)
  - Soil type (OpenLandMap)
  - Soil temperature (NASA/SMAP)
  - Soil organic carbon (OpenLandMap)
  - Soil pH (OpenLandMap)
  - Land cover (ESA WorldCover)
- Handle ImageCollections vs Images
- Standardize projections to EPSG:4326
- Cross examin the projections

---

### **STEP 3: Clipping to Mato Grosso State**
**Goal**: Clip all retrieved datasets to Mato Grosso boundaries
- Load Mato Grosso administrative boundaries from GEE
- Clip all soil property images to state boundaries
- Verify clipping success

---

### **STEP 4: Export to GeoTIFF Format** **COMPLETED** - **Option B Selected: Automated Download**
**Goal**: Export clipped datasets to GeoTIFF files with automated download
- Create export tasks for each dataset using `ee.batch.Export.image.toDrive()` [DONE]
- **Note**: GEE exports to Google Drive (not directly to local machine) [DONE]
- **Selected Approach**: Automate download from Drive using `pydrive2` [DONE]
- Monitor export progress and task status [DONE]
- Automatically download files from Drive to local `data/raw/` directory when complete [DONE]
- Organize files by dataset name [DONE]
- Export OpenLandMap layers (soil pH, SOC, soil type) as separate depth-band GeoTIFFs (`b0`, `b10`, `b30`, `b60`) [DONE]
- During acquisition, prompt user for how many datasets to export and show a detailed task summary before starting jobs [DONE]
- **Setup Required**: Google Drive API credentials (OAuth2) - See SETUP_GUIDE.md

---

### **STEP 5: User Interface - Coordinate Input**
**Goal**: Create interface for user to specify area of interest
- Create CLI or simple GUI for coordinate input
- Options:
  - No input: Use entire Mato Grosso state
  - With coordinates: Create 100km radius circle
- Validate coordinate inputs
- Store user preferences

---

### **STEP 6: Radius Clipping (100km circles)**
**Goal**: Clip GeoTIFFs to user-specified circles
- If coordinates provided:
  - Create 100km radius buffer around point
  - Clip all GeoTIFF files to this circle
  - Save clipped versions
- If no coordinates:
  - Use full state data
- Handle coordinate transformations

---

### **STEP 7: Convert Maps to CSV (within circles)**
**Goal**: Convert clipped GeoTIFFs to CSV format
- Extract pixel values from clipped rasters
- Create CSV with columns: lon, lat, value for each soil property
- Handle nodata values
- Merge spatial coordinates across all datasets

---

### **STEP 8: H3 Index Conversion**
**Goal**: Convert coordinates to H3 hexagonal grid
- Install and configure H3 library
- Convert lat/lon to H3 indexes
- Generate H3 polygons (hexagon boundaries)
- Aggregate data by H3 hexagons if needed
- Store H3 index and polygon data in CSV

---

### **STEP 9: Biochar Thresholds Database** — **Completed**
Threshold definitions live in `configs/thresholds.yaml` and are loaded through `src/analysis/thresholds.py`. The current scoring pipeline uses calibrated ranges for soil moisture, soil temperature, soil organic carbon, and soil pH, and the YAML file remains editable for rapid tuning.

---

### **STEP 10: Suitability Score Calculator** — **Completed**
`src/analysis/suitability.py` groups raster-derived values by H3 hexagon, averages the soil variables within each hex, and applies the 0–10 scoring logic. Per-variable diagnostic columns are retained, NaNs are respected, and poorly covered hexes are filtered out.

---

### **STEP 11: Visualization - Color-Coded Map** — **Completed**
PyDeck is now the default renderer, matching the Capstone color scheme and tooltip format. Large datasets fall back gracefully, and generated maps are written to `output/html/` in a human-editable structure.

---

### **STEP 12: HTML Output and Auto-Open** — **Completed**
`src/utils/browser.py` centralizes HTML launching, and `main.py` saves output maps under `output/html/` before opening them automatically (configurable via `visualization.auto_open_html`).

---

### **STEP 13: Main Pipeline Integration** — **Completed**
`src/main.py` stitches together acquisition validation, optional clipping, CSV conversion, H3 aggregation, scoring, and mapping. CLI flags expose coordinates, radius, H3 resolution, and config overrides, and interactive prompts guide users who run without coordinates.

---

### **STEP 14: Testing and Documentation** — **Completed**
Manual runs cover both full-state and edge-case coordinate scenarios. `raster_clip.py` verifiers accept partial coverage (common when circles touch state boundaries) while still enforcing radius limits, and all documentation files now reflect the latest workflow.

---

## Next Steps
Core workflow is complete. Future enhancements could include automated tests, feedstock-specific weighting, and additional visualization controls.

