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

### **STEP 9: Biochar Thresholds Database**
**Goal**: Create/load database with soil property thresholds
- Design database structure for thresholds
- Define optimal ranges for each soil property
- Create scoring system (0-10 scale)
- Load biochar outputs database (feedstock properties)
- Create configuration file for thresholds

---

### **STEP 10: Suitability Score Calculator**
**Goal**: Calculate suitability scores based on thresholds
- Implement scoring algorithm:
  - Compare soil properties to thresholds
  - Calculate individual scores for each property
  - Weight and combine scores
  - Generate final suitability score (0-10)
- Handle multiple soil layers
- Incorporate biochar output data

---

### **STEP 11: Visualization - Color-Coded Map**
**Goal**: Create interactive map with suitability scores
- Generate color scheme:
  - Green = most suitable (score 8-10)
  - Yellow = moderately suitable (score 5-7)
  - Red = least suitable (score 0-4)
- Create interactive HTML map (using Folium/Leaflet or PyDeck)
- Display H3 hexagons colored by suitability score
- Add legend and grade scale (0-10)
- Include tooltips with score details

---

### **STEP 12: HTML Output and Auto-Open**
**Goal**: Generate HTML file and open it automatically
- Save map as HTML file
- Automatically open HTML in default browser
- Add styling and interactivity
- Include metadata (date, input parameters, etc.)

---

### **STEP 13: Main Pipeline Integration**
**Goal**: Connect all components into a single workflow
- Create main.py that orchestrates all steps
- Add error handling and logging
- Create CLI interface
- Add progress indicators
- Test end-to-end workflow

---

### **STEP 14: Testing and Documentation**
**Goal**: Ensure tool works correctly and is documented
- Test with different coordinate inputs
- Test with no coordinates (full state)
- Validate suitability scores
- Create user documentation
- Add code comments and docstrings

---

## Next Steps
We'll implement each step one at a time. Start with **STEP 1: Project Structure Setup**?

