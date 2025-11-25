# Residual_Carbon - Biochar Suitability Mapping Tool

A tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and crop residue data.

## Project Overview

This tool analyzes soil properties (moisture, temperature, organic carbon, pH) to calculate biochar suitability scores across Mato Grosso state. The tool generates interactive maps from GeoTIFF data files and provides a web interface via Streamlit for both farmers and investors:

**Farmer Perspective:**
- **Biochar Suitability Map**: Color-coded suitability scores (0-10 scale) where higher scores indicate higher suitability (poor soil needs biochar)
- **Soil Organic Carbon (SOC) Map**: Displays SOC values (g/kg) aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers
- **Soil pH Map**: Displays pH values aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers, using a diverging color scheme
- **Soil Moisture Map**: Displays soil moisture values aggregated by H3 hexagons
- **Top 10 Recommendations**: Shows recommended biochar feedstocks based on soil conditions

**Investor Perspective:**
- **Crop Residue Map**: Municipality-level interactive map with data type selector (crop area, crop production, crop residue) showing total values per municipality

## Features

- **Automatic Data Download**: Required data files can be automatically downloaded from Google Drive on first run via Streamlit app
- **Targeted Spatial Analysis**: Works on the full Mato Grosso extent or user-specified circular AOIs with validation and graceful edge handling
- **Robust GeoTIFF Processing**: Clips, converts, and validates rasters before tabularisation, with an in-memory pandas pipeline
- **Performance Caching**: Intelligent caching system speeds up re-runs by caching clipped rasters and DataFrame conversions. Automatically detects changes and invalidates cache when source files are updated
- **H3 Hexagonal Grid**: Adds hex indexes for efficient aggregation using vectorized operations. Boundary geometry is generated after merge and aggregation to optimize memory usage
- **Biochar Suitability Scoring**: Calculates biochar suitability scores (0-10 scale) based on soil quality metrics. Uses weighted scoring for moisture, organic carbon (averages b0 and b10 depth layers), pH (averages b0 and b10 depth layers), and temperature properties
- **Biochar Recommendations**: Provides recommended biochar feedstocks based on soil challenges (implemented but not fully optimized)
- **Smart Dataset Filtering**: Automatically filters to only scoring-required datasets during processing
- **Interactive Maps**: Generates PyDeck-based HTML visualizations for suitability, SOC, pH, moisture, and crop residue data
- **Streamlit Web Interface**: User-friendly web interface with separate tabs for farmer and investor perspectives
- **Auditable Workflow**: Each stage can be run independently, and helper utilities exist to verify intermediate results

## Installation

### Prerequisites

- Python 3.9 or higher
- GeoTIFF data files (can be downloaded automatically or manually placed in `data/` directory - flat structure)
- Git (optional, for cloning repository)

### Step 1: Clone or Navigate to Project

```bash
cd Residual_Carbon
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

> **Note:** Raster libraries ship native binaries. On Windows we recommend installing them with Conda first.

```bash
# Linux / macOS (single step)
pip install -r requirements.txt

# Windows (two step)
conda install -c conda-forge geopandas rasterio shapely fiona pyproj gdal
pip install -r requirements.txt
```

### Step 4: Prepare Data Files

**Automatic Download from Google Drive (Recommended):**

All required data files are hosted in a shared Google Drive folder and can be downloaded automatically:

```bash
# Download all required data files from Google Drive
python scripts/download_assets.py
```

This script will download:
- 5 shapefile components for Brazilian municipality boundaries
- 1 crop production CSV file
- 6 GeoTIFF files for soil properties (SOC, pH, moisture, temperature)

**Required files for scoring:**
- Soil moisture: `soil_moisture_res_250_sm_surface.tif`
- Soil Organic Carbon: `SOC_res_250_b0.tif`, `SOC_res_250_b10.tif`
- Soil pH: `soil_pH_res_250_b0.tif`, `soil_pH_res_250_b10.tif`
- Soil temperature: `soil_temp_res_250_soil_temp_layer1.tif`

**Manual Data Placement (Alternative):**

If you prefer to place files manually, ensure the following structure:

```bash
data/
├── raw/
│   ├── SOC_res_250_b0.tif
│   ├── SOC_res_250_b10.tif
│   ├── soil_moisture_res_250_sm_surface.tif
│   ├── soil_pH_res_250_b0.tif
│   ├── soil_pH_res_250_b10.tif
│   └── soil_temp_res_250_soil_temp_layer1.tif
├── BR_Municipios_2024.shp (and .dbf, .shx, .prj, .cpg)  # Flat structure: all files in data/
│   ├── BR_Municipios_2024.shp
│   ├── BR_Municipios_2024.dbf
│   ├── BR_Municipios_2024.shx
│   ├── BR_Municipios_2024.prj
│   └── BR_Municipios_2024.cpg
└── crop_data/
    └── Updated_municipality_crop_production_data.csv
```

**Note:** The Streamlit app will automatically download missing files on first run. See `STREAMLIT_DEPLOYMENT.md` for more details.

## Configuration

**No configuration is required for core functionality** - the tool works with sensible defaults.

The `config.yaml` file is **only needed** if you want to use the optional GEE export scripts to export data from Google Earth Engine. For normal usage with manually placed data files, no configuration is needed.

**Default Settings (work out of the box):**
- Data directories: `data/` (flat structure for all input files), `data/processed/` (for outputs)
- Output directories: `output/html`
- H3 resolution: 7 for clipped areas, 9 for full state
- Processing: Caching enabled, snapshots disabled

**If you need to export data from GEE:**

1. Copy the template configuration:
   ```bash
   cp configs/config.template.yaml configs/config.yaml
   ```

2. Edit `configs/config.yaml` and fill in your GEE/Drive values:
   ```yaml
   gee:
     project_name: "your-gee-project-id"
     export_folder: "your-google-drive-folder-id"
   ```

3. See `src/data_acquisition/README_TEMPLATE.md` for detailed instructions.

**Note**: 
- Only scoring-required datasets are processed (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature). Other datasets (land_cover, soil_type) are automatically excluded from processing to optimize performance.
- The core pipeline processes local GeoTIFF files and doesn't require any configuration.

## Usage

### Running the Streamlit Web Interface (Recommended)

```bash
streamlit run streamlit_app.py
```

The web interface provides:
- Interactive area selection (latitude, longitude, radius)
- Two main perspectives: Farmer and Investor
- Automatic data download if files are missing
- Visualizations of all maps and results
- CSV download functionality

### Running Command Line Analysis

```bash
# Full-state run (interactive prompt will confirm coordinates)
python src/main.py

# Targeted analysis with explicit radius (default is 100 km)
python src/main.py --lat -15.5 --lon -56.0 --radius 100

# Using default radius (100 km)
python src/main.py --lat -15.5 --lon -56.0

# Explore all CLI switches
python src/main.py --help
```

Key processing flags:

- `--lat / --lon / --radius` — Skip prompts and inject AOI coordinates directly. Default radius is 100 km.
- `--h3-resolution` — Choose aggregation granularity for clipped areas (higher = more hexes, default 7). Full state uses resolution 9 automatically.
- `--config` — Point the pipeline at an alternate configuration document.

## Project Structure

```
Residual_Carbon/
├── scripts/              # Helper CLI utilities (run_analysis, download_assets)
├── src/
│   ├── analyzers/        # Analysis modules (suitability scoring, biochar recommendations)
│   ├── data_acquisition/ # Data retrieval utilities (optional GEE exports)
│   ├── data_processors/  # Data processing (raster clipping, H3 conversion)
│   ├── map_generators/   # Map generation (suitability, SOC, pH, moisture, investor maps)
│   └── utils/            # Utility functions (cache, config, geospatial)
├── configs/              # Configuration files
├── data/
│   ├── raw/              # GeoTIFF files and Excel data files
│   ├── boundaries/       # Shapefile boundaries
│   ├── crop_data/        # Crop production data CSVs
│   ├── pyrolysis/        # Pyrolysis/biochar feedstock data
│   └── processed/        # Processed outputs
│       └── cache/        # Cache directory (clipped rasters, DataFrames, H3 indexes)
├── output/
│   └── html/             # HTML map files
├── streamlit_app.py      # Streamlit web application
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

### Utility Scripts

All helper/automation scripts live under `scripts/`:

- `scripts/run_analysis.py` – wrapper script to invoke `src/main.py`
- `scripts/download_assets.py` – downloads required data files from Google Drive
- `scripts/retry_exports.py` – optional script for GEE exports (not required for local use)
- `scripts/check_export_status.py` – optional script for checking GEE export status (not required for local use)

Call them with `python scripts/<script_name>.py [...]` from the project root.

## Processing Pipeline

The core pipeline lives in `src/main.py` and wires high-level helpers from each submodule:

1. **Data validation** (`ensure_rasters_acquired`) — confirms GeoTIFFs exist in `data/` before doing any expensive work. Files should be manually placed in this directory or downloaded automatically.
2. **AOI selection** (`get_user_area_of_interest`) — validates coordinates, radius, and provides a full-state fallback.
3. **Optional clipping** (`clip_all_rasters_to_circle`) — trims rasters to the requested buffer and reports size deltas. **Cached** to speed up re-runs (see Caching System section).
4. **Raster ➜ Table** (`convert_all_rasters_to_dataframes`) — flattens rasters into pandas DataFrames with coordinates, nodata handling, and unit inference. **Cached** as Parquet files for fast loading (see Caching System section).
5. **Hex indexing** (`process_dataframes_with_h3`) — injects `h3_index` at the requested resolution using vectorized operations. Boundary geometry is excluded during indexing and merging to optimize memory usage. **Cached** to speed up re-runs (see Caching System section).
6. **Data merging and aggregation** (`merge_and_aggregate_soil_data`) — merges property tables (without boundaries), aggregates by hex, and generates boundaries for aggregated hexagons only.
7. **Biochar suitability scoring** (`calculate_biochar_suitability_scores`) — calculates biochar suitability scores (0-10 scale) based on soil quality metrics. For SOC and pH, averages both b0 (surface) and b10 (10cm depth) layers to provide a more representative soil profile assessment. Uses weighted scoring for moisture, organic carbon, pH, and temperature properties.
8. **Biochar recommendations** (optional) — adds recommended feedstock types based on soil challenges using pyrolysis data
9. **Visualisation** — renders interactive PyDeck maps directly from CSV data:
   - **Biochar Suitability Map** (`create_biochar_suitability_map`) — saves `biochar_suitability_map.html` and `suitability_map.html` (Streamlit-compatible copy)
   - **Soil Organic Carbon Map** (`create_soc_map`) — saves `soc_map.html` and `soc_map_streamlit.html` showing SOC values aggregated by H3 hexagons
   - **Soil pH Map** (`create_ph_map`) — saves `ph_map.html` and `ph_map_streamlit.html` showing pH values aggregated by H3 hexagons with diverging color scheme
   - **Soil Moisture Map** (`create_moisture_map`) — saves `moisture_map.html` and `moisture_map_streamlit.html` showing soil moisture values aggregated by H3 hexagons
   - **Investor Crop Area Map** (`build_investor_waste_deck_html`) — saves `investor_crop_area_map.html` with interactive data type selector
   - All maps are saved under `output/html/` and auto-open in browser (configurable)

Verification helpers such as `verify_clipping_success` and `verify_clipped_data_integrity` can be run independently when you need to inspect intermediate outputs.

## Workflow Summary

1. **Data Preparation**: GeoTIFF data files can be downloaded automatically via Streamlit app or manually placed in `data/` directory (flat structure).
2. **Processing**: Run `python src/main.py` with or without coordinates to process the local data files, or use the Streamlit web interface.
3. **Score & Map**: Review the returned DataFrame (optionally written to `data/processed/merged_soil_data.csv`), suitability scores CSV (`data/processed/suitability_scores.csv`), and interactive maps:
   - `output/html/biochar_suitability_map.html` — Biochar suitability map
   - `output/html/suitability_map.html` — Streamlit-compatible copy of suitability map
   - `output/html/soc_map.html` — Soil Organic Carbon map
   - `output/html/soc_map_streamlit.html` — Streamlit-compatible copy of SOC map
   - `output/html/ph_map.html` — Soil pH map
   - `output/html/ph_map_streamlit.html` — Streamlit-compatible copy of pH map
   - `output/html/moisture_map.html` — Soil Moisture map
   - `output/html/moisture_map_streamlit.html` — Streamlit-compatible copy of moisture map
   - `output/html/investor_crop_area_map.html` — Investor crop area map with data type selector
4. **Validate (optional)**: Run the helper verification functions if you need to sanity-check inputs or radius coverage.

## Data Sources

### Scoring-Required Datasets (Used in Biochar Suitability Calculation)
- **Soil Moisture**: Resampled to 250m resolution - surface layer
- **Soil Temperature**: Resampled to 250m resolution - layer 1
- **Soil Organic Carbon**: 250m resolution - b0 (surface) and b10 (10cm) layers averaged
- **Soil pH**: 250m resolution - b0 (surface) and b10 (10cm) layers averaged

### Additional Data Sources
- **Municipality Boundaries**: Brazilian municipality boundaries shapefiles (2024)
- **Crop Production Data**: Municipality-level crop area, production, and residue data
- **Pyrolysis Data**: Biochar feedstock properties and soil challenge matching (for recommendations)

## Caching System

The tool includes an intelligent caching system that significantly speeds up re-runs:

### Cache Types

1. **Clipped Raster Cache** (`data/processed/cache/clipped_rasters/`)
   - Caches clipped GeoTIFF files based on coordinates, radius, and source file metadata
   - Automatically invalidates when source files change

2. **DataFrame Cache** (`data/processed/cache/raster_to_dataframe/`)
   - Caches converted DataFrames as Parquet files (faster than CSV)
   - Based on source files, conversion parameters (band, nodata handling, pattern)
   - Automatically invalidates when source files change

3. **H3 Indexes Cache** (`data/processed/cache/h3_indexes/`)
   - Caches H3-indexed DataFrames as Parquet files
   - Based on input DataFrames and H3 resolution
   - Automatically invalidates when input DataFrames change

### How It Works

- **First run**: Caches are created during normal processing
- **Subsequent runs**: Caches are automatically used if valid (same inputs and parameters)
- **Cache validation**: Checks source file modification times to detect changes
- **Automatic invalidation**: Cache is invalidated if source files change or parameters differ
- **Transparent**: Caching is enabled by default and works automatically

### Cache Management

- Cache files are stored in `data/processed/cache/`
- Cache directories are automatically created as needed
- Cache files are excluded from Git (see `.gitignore`)
- **Automatic cleanup**: Old coordinate-specific caches are automatically cleaned up on each run
  - Preserved caches: Full state cache (no coordinates), protected coordinates (-13, -56, 100km), and current coordinates (same lat/lon/radius as current run)
  - Only old coordinate-specific caches (clipped_rasters) that don't match the above are removed
- To manually clear cache: Delete the `data/processed/cache/` directory or specific cache subdirectories
- Cache size: Typically 10-100 MB depending on area size and number of datasets

### Benefits

- **Faster re-runs**: Re-running the same analysis is much faster
- **Development speed**: Faster iteration when testing different parameters
- **Resource efficiency**: Reduces CPU and I/O usage for repeated operations
- **Automatic**: No manual configuration required, works out of the box
- **Smart cleanup**: Automatically removes old coordinate-specific caches on each run, while preserving important caches (full state, protected coordinates -13/-56/100km, and current coordinates)

## Performance & Memory Optimization

The pipeline includes several optimizations to handle large datasets efficiently:

### Vectorized H3 Indexing
- **Vectorized operations**: Uses list comprehensions with zip() instead of row-by-row `.apply()` calls
- **Performance improvement**: 5-10x faster for large datasets (100k+ rows)
- **Memory efficiency**: Lower memory overhead compared to `.apply()` operations
- **Automatic**: Built-in optimization, no configuration required

### H3 Boundary Generation Optimization
- **Memory savings**: Hexagon boundary geometry is **not** generated during H3 indexing or merging. Boundaries are only generated after data is merged and aggregated by hexagon. This reduces memory usage by ~99% for large datasets:
  - **Before optimization**: Would generate boundaries for all points (e.g., 521,217 points)
  - **After optimization**: Only generates boundaries for aggregated hexagons (e.g., 5,817 hexagons)
  - **Result**: Prevents memory crashes when processing large areas (100km+ radius)

### Smart Dataset Filtering
- **Automatic filtering**: Only scoring-required datasets are processed
- **Scoring-required datasets**: soil_moisture, SOC (b0 and b10), pH (b0 and b10), soil_temperature
- **Excluded from processing**: land_cover, soil_type (can be included but not used in scoring)
- **Benefits**: Reduces memory usage, processing time, and cache size
- **Note**: Only scoring-required files are processed from the manually placed GeoTIFF files in `data/`

### Automatic
All optimizations are built-in and require no configuration. The pipeline automatically handles these optimizations at the optimal stages.

## Output

The tool generates:

- **GeoTIFF files**: Raw raster data in `data/` (flat structure)
- **CSV files**: 
  - `merged_soil_data.csv` - Merged and aggregated soil data in `data/processed/`
  - `suitability_scores.csv` - Biochar suitability scores with `suitability_score` column (0-10 scale) in `data/processed/`
- **Cache files**: Cached clipped rasters, DataFrames, and H3 indexes in `data/processed/cache/`
- **HTML maps**: Interactive maps in `output/html/`:
  - `biochar_suitability_map.html` - Main interactive biochar suitability map with scores (0-10 scale)
  - `suitability_map.html` - Streamlit-compatible copy of suitability map
  - `soc_map.html` - Main interactive Soil Organic Carbon map showing SOC values (g/kg)
  - `soc_map_streamlit.html` - Streamlit-compatible copy of SOC map
  - `ph_map.html` - Main interactive Soil pH map showing pH values
  - `ph_map_streamlit.html` - Streamlit-compatible copy of pH map
  - `moisture_map.html` - Main interactive Soil Moisture map
  - `moisture_map_streamlit.html` - Streamlit-compatible copy of moisture map
  - `investor_crop_area_map.html` - Interactive municipality-level map with data type selector
- **Logs**: Application logs in `logs/`

### Streamlit Integration

The tool includes a Streamlit web interface (`streamlit_app.py`) with the following features:

**Automatic Data Download:**
- Downloads required data files from Google Drive on first run if missing
- Shows progress message during download (automatically clears when complete)
- Caches file existence checks to improve performance

**Performance Optimizations:**
- Cached file existence checks (TTL: 1 hour)
- Cached CSV and HTML file reading (TTL: 1 hour)
- Session state tracking to prevent redundant operations
- Efficient data loading with minimal reruns

**Generated Files:**
- `suitability_scores.csv` contains scores on a 0-10 scale with `suitability_score` column
- All Streamlit-compatible map files (`*_streamlit.html`) are pre-generated during analysis

**Streamlit Interface:**
- Two main perspectives:
  - **Farmer Perspective**: Five tabs showing soil health insights
    - Biochar Suitability: Displays suitability map with metrics (0-10 scale)
    - Soil Organic Carbon: Displays SOC map with values (g/kg)
    - Soil pH: Displays pH map with diverging color scheme
    - Soil Moisture: Displays moisture map
    - Top 10 Recommendations: Shows recommended biochar feedstocks (if available)
  - **Investor Perspective**: Interactive crop residue map
    - Radio button selector for crop area, production, or residue data
    - Municipality-level visualization with summary metrics
- Automatic loading of previous analysis results if available
- Interactive area selection for targeted analysis (latitude, longitude, radius)
- Download button for CSV results

**Deployment:**
- See `STREAMLIT_DEPLOYMENT.md` for detailed deployment instructions
- Compatible with Streamlit Cloud (handles Google Drive downloads automatically)
- All files are automatically generated during the analysis pipeline

## Troubleshooting Highlights

- **Missing rasters**: Ensure GeoTIFF files are in `data/` directory or use the automatic download feature. Files should be GeoTIFF format and contain keywords like "moisture", "SOC", "ph", or "temp" in their names.
- **No data found**: Check that required files are present: `soil_moisture_res_250_sm_surface.tif`, `SOC_res_250_b0.tif`, `SOC_res_250_b10.tif`, `soil_pH_res_250_b0.tif`, `soil_pH_res_250_b10.tif`, `soil_temp_res_250_soil_temp_layer1.tif`
- **Empty CSV outputs**: Make sure the clipping circle overlaps the raster (edge circles often produce sparse data—use the verification helpers to confirm coverage).
- **Cache issues**: If you suspect cache problems, delete `data/processed/cache/` directory to force regeneration. Cache automatically invalidates when source files change, but manual deletion can help troubleshoot.
- **Parquet file errors**: Ensure `pyarrow>=10.0.0` is installed (`pip install pyarrow`). Parquet files are used for efficient DataFrame caching.

## Contributing & Support

This project is actively developed for internal research. If you have improvements or encounter issues:

- Open an issue or pull request with a clear description of the change.
- Attach sample rasters/CSVs when reporting pipeline bugs so we can reproduce them.
- Reach out to the project maintainers via the repository issue tracker for further assistance.
