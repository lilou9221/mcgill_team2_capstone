# Residual_Carbon - Biochar Suitability Mapping Tool

A tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and biochar outputs.

## Project Overview

This tool analyzes soil properties (moisture, type, temperature, organic carbon, pH, and land cover) from Google Earth Engine to calculate suitability scores for biochar application across Mato Grosso state. The tool generates interactive maps with color-coded suitability scores (0-10 scale) where green indicates high suitability and red indicates low suitability.

## Features

- **Automated Data Retrieval**: Launches parameterized Google Earth Engine exports with per-layer summaries and optional auto-start. Downloads from Google Drive are automatic once configured.
- **Targeted Spatial Analysis**: Works on the full Mato Grosso extent or user-specified circular AOIs with validation and graceful edge handling.
- **Robust GeoTIFF Processing**: Clips, converts, and validates rasters before tabularisation, with an in-memory pandas pipeline and optional snapshots.
- **Performance Caching**: Intelligent caching system speeds up re-runs by caching clipped rasters and DataFrame conversions. Automatically detects changes and invalidates cache when source files are updated.
- **H3 Hexagonal Grid**: Adds hex indexes for efficient aggregation. Boundary geometry is generated after merge and aggregation to optimize memory usage (prevents memory crashes with large datasets).
- **Suitability Scoring**: Applies configurable thresholds (0–10 scale) with per-property diagnostics prior to final rollups.
- **Interactive Maps**: Generates PyDeck-based HTML visualisations and auto-opens them (configurable).
- **Auditable Workflow**: Each stage can be run independently, and helper utilities exist to verify intermediate results.

## Installation

### Prerequisites

- Python 3.9 or higher
- Google Earth Engine account
- Google Cloud Project with Drive API enabled
- Git (optional)

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

> ⚠️ Raster libraries ship native binaries. On Windows we recommend installing them with Conda first.

```bash
# Linux / macOS (single step)
pip install -r requirements.txt

# Windows (two step)
conda install -c conda-forge geopandas rasterio shapely fiona pyproj gdal
pip install -r requirements.txt
```

### Step 4: Google Earth Engine Setup

1. **Authenticate with Google Earth Engine:**
   ```bash
   python -c "import ee; ee.Authenticate()"
   ```

2. **Set your GEE project name** in `configs/config.yaml`:
   ```yaml
   gee:
     project_name: "your-project-name"
   ```

### Step 5: Google Drive API Setup (Required for Automatic Downloads)

The tool automatically downloads exported GeoTIFF files from Google Drive once configured. Set up the Google Drive API to enable automatic downloads:

1. **Enable Google Drive API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)

2. **Download credentials:**
   - Download `client_secrets.json` from Google Cloud Console
   - Place it in `configs/client_secrets.json`

3. **First-time authentication:**
   - The first time you run the acquisition tool, it will open a browser for OAuth authentication
   - A `credentials.json` file will be created automatically in `configs/`
   - Once configured, all exported files will be automatically downloaded to `data/raw/`

## Configuration

Edit `configs/config.yaml` to customize:

- Google Earth Engine project name
- Export resolution (default: 1000m)
- H3 resolution (default: 6)
- Output directories
- Suitability scoring parameters
- Optional snapshot persistence for intermediate DataFrames

## Usage

### 1. Acquire GeoTIFFs from Google Earth Engine

Run the acquisition script to create Drive export tasks. It prompts for how many datasets to export, shows a detailed summary (dataset, depth band, filename, resolution, folder), reminds you which files will be generated, and then asks whether to start the tasks.

```bash
python src/data/acquisition/gee_loader.py
```

- Use `--layers soil_pH,soil_organic_carbon` to target specific datasets.
- Add `--start-tasks` to skip the confirmation prompt and immediately launch the Drive exports.
- OpenLandMap layers (`soil_pH`, `soil_organic_carbon`, `soil_type`) are exported one GeoTIFF per depth band (`b0`, `b10`, `b30`, `b60`).

**Automatic Downloads**: Once Google Drive API is configured (Step 5), exported files are automatically downloaded from Google Drive to `data/raw/` as soon as the GEE export tasks complete. No manual download step is required. The GeoTIFFs will appear in `data/raw/` automatically.

### 2. Process and Map

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
- `--h3-resolution` — Choose aggregation granularity (higher = more hexes, default 7).
- `--config` — Point the pipeline at an alternate configuration document.

## Project Structure

```
Residual_Carbon/
├── src/
│   ├── data/           # Data retrieval and processing
│   ├── analysis/       # Suitability scoring
│   ├── visualization/  # Map generation
│   └── utils/          # Utility functions (includes cache utilities)
├── configs/            # Configuration files
├── data/
│   ├── raw/            # GeoTIFF files from GEE
│   └── processed/      # Processed outputs and optional snapshots
│       └── cache/      # Cache directory (clipped rasters, DataFrames)
│           ├── clipped_rasters/    # Cached clipped GeoTIFF files
│           └── raster_to_dataframe/ # Cached DataFrame Parquet files
├── output/
│   ├── maps/           # Generated maps
│   └── html/           # HTML map files
├── logs/               # Application logs
├── requirements.txt    # Python dependencies
├── config.yaml         # Main configuration
└── README.md           # This file
```

## Processing Pipeline

The core pipeline lives in `src/main.py` and wires high-level helpers from each submodule:

1. **Acquisition check** (`ensure_rasters_acquired`) — confirms GeoTIFFs exist in `data/raw/` before doing any expensive work.
2. **AOI selection** (`get_user_area_of_interest`) — validates coordinates, radius, and provides a full-state fallback.
3. **Optional clipping** (`clip_all_rasters_to_circle`) — trims rasters to the requested buffer and reports size deltas. **Cached** to speed up re-runs (see Caching System section).
4. **Raster ➜ Table** (`convert_all_rasters_to_dataframes`) — flattens rasters into pandas DataFrames with coordinates, nodata handling, and unit inference. **Cached** as Parquet files for fast loading (see Caching System section).
5. **Hex indexing** (`process_dataframes_with_h3`) — injects `h3_index` at the requested resolution. Boundary geometry is excluded during indexing and merging to optimize memory usage.
6. **Suitability scoring** (`process_csv_files_with_suitability_scores`) — merges property tables (without boundaries), aggregates by hex, generates boundaries for aggregated hexagons only, and applies thresholds.
7. **Visualisation** (`create_suitability_map`) — renders an interactive PyDeck map and saves it under `output/html/`.

Verification helpers such as `verify_clipping_success`, `verify_clipped_data_integrity`, and `calculate_property_score` can be run independently when you need to inspect intermediate outputs.

## Workflow Summary

1. **Data Retrieval**: Launch Drive exports from Google Earth Engine using `gee_loader.py`.
2. **Task Review**: Inspect task summaries and start jobs with confidence.
3. **Automatic Download**: Files are automatically downloaded from Google Drive to `data/raw/` as export tasks complete (requires Google Drive API setup from Step 5).
4. **Processing**: Run `python src/main.py` with or without coordinates.
5. **Score & Map**: Review the returned DataFrame (optionally written to `data/processed/suitability_scores.csv`) and `output/html/suitability_map.html`.
6. **Validate (optional)**: Run the helper verification functions if you need to sanity-check inputs or radius coverage.

## Data Sources

- **Soil Moisture**: NASA SMAP (NASA/SMAP/SPL4SMGP/008)
- **Soil Type**: OpenLandMap (OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02)
- **Soil Temperature**: NASA SMAP (NASA/SMAP/SPL4SMGP/008)
- **Soil Organic Carbon**: OpenLandMap (OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02)
- **Soil pH**: OpenLandMap (OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02)
- **Land Cover**: ESA WorldCover (ESA/WorldCover/v100)

## Caching System

The tool includes an intelligent caching system that significantly speeds up re-runs:

### Cache Types

1. **Clipped Raster Cache** (`data/processed/cache/clipped_rasters/`)
   - Caches clipped GeoTIFF files based on coordinates, radius, and source file metadata
   - Automatically invalidates when source files change (checks modification times)
   - **Time savings**: ~90% (skips expensive clipping operations)

2. **DataFrame Cache** (`data/processed/cache/raster_to_dataframe/`)
   - Caches converted DataFrames as Parquet files (faster than CSV)
   - Based on source files, conversion parameters (band, nodata handling, pattern)
   - Automatically invalidates when source files change
   - **Time savings**: ~70% (skips expensive raster reading and DataFrame conversion)

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
- To clear cache: Delete the `data/processed/cache/` directory or specific cache subdirectories
- Cache size: Typically 10-100 MB depending on area size and number of datasets

### Benefits

- **Faster re-runs**: Re-running the same analysis is much faster
- **Development speed**: Faster iteration when testing different parameters
- **Resource efficiency**: Reduces CPU and I/O usage for repeated operations
- **Automatic**: No manual configuration required, works out of the box

## Memory Optimization

The pipeline includes memory optimizations to handle large datasets efficiently:

- **H3 Boundary Generation**: Hexagon boundary geometry is **not** generated during H3 indexing or merging. Boundaries are only generated after data is merged and aggregated by hexagon. This reduces memory usage by ~99% for large datasets:
  - **Before optimization**: Would generate boundaries for all points (e.g., 521,217 points)
  - **After optimization**: Only generates boundaries for aggregated hexagons (e.g., 5,817 hexagons)
  - **Result**: Prevents memory crashes when processing large areas (100km+ radius)

- **Automatic**: This optimization is built-in and requires no configuration. The pipeline automatically handles boundary generation at the optimal stage.

## Output

The tool generates:

- **GeoTIFF files**: Raw raster data in `data/raw/`
- **CSV snapshots**: Optional debug exports and final `suitability_scores.csv` in `data/processed/`
- **Cache files**: Cached clipped rasters and DataFrames in `data/processed/cache/`
- **HTML map**: Interactive suitability map in `output/html/`
- **Logs**: Application logs in `logs/`

## Troubleshooting Highlights

- **Re-authenticate GEE**: `python -c "import ee; ee.Authenticate()"`.
- **Drive API hiccups**: confirm `configs/client_secrets.json` exists, delete `configs/credentials.json`, and re-run the acquisition tool.
- **Automatic downloads not working**: Ensure Google Drive API is enabled and `client_secrets.json` is properly configured. Downloads happen automatically once GEE export tasks complete.
- **Missing rasters**: rerun `src/data/acquisition/gee_loader.py` and wait for automatic downloads to complete, or manually download from Google Drive if automatic download is not configured.
- **Empty CSV outputs**: make sure the clipping circle overlaps the raster (edge circles often produce sparse data—use the verification helpers to confirm coverage).
- **Cache issues**: If you suspect cache problems, delete `data/processed/cache/` directory to force regeneration. Cache automatically invalidates when source files change, but manual deletion can help troubleshoot.
- **Parquet file errors**: Ensure `pyarrow>=10.0.0` is installed (`pip install pyarrow`). Parquet files are used for efficient DataFrame caching.

## Contributing & Support

This project is actively developed for internal research. If you have improvements or encounter issues:

- Open an issue or pull request with a clear description of the change.
- Attach sample rasters/CSVs when reporting pipeline bugs so we can reproduce them.
- Reach out to the project maintainers via the repository issue tracker for further assistance.

