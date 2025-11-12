# Residual_Carbon - Biochar Suitability Mapping Tool

A tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and biochar outputs.

## Project Overview

This tool analyzes soil properties (moisture, type, temperature, organic carbon, pH, and land cover) from Google Earth Engine to calculate suitability scores for biochar application across Mato Grosso state. The tool generates interactive maps with color-coded suitability scores (0-10 scale) where green indicates high suitability and red indicates low suitability.

## Features

- **Automated Data Retrieval**: Launches parameterized Google Earth Engine exports with per-layer summaries and optional auto-start.
- **Targeted Spatial Analysis**: Works on the full Mato Grosso extent or user-specified circular AOIs with validation and graceful edge handling.
- **Robust GeoTIFF Processing**: Clips, converts, and validates rasters before tabularisation, with an in-memory pandas pipeline and optional snapshots.
- **H3 Hexagonal Grid**: Adds hex indexes and boundary geometry for efficient aggregation and map rendering.
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

### Step 5: Google Drive API Setup (for Automated Download)

1. **Enable Google Drive API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)

2. **Download credentials:**
   - Download `client_secrets.json` from Google Cloud Console
   - Place it in `configs/client_secrets.json`

3. **First-time authentication:**
   - The first time you run the tool, it will open a browser for OAuth authentication
   - A `credentials.json` file will be created automatically in `configs/`

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

After the Drive tasks complete (and downloads finish, if you use the automated downloader), the GeoTIFFs will be in `data/raw/`.

### 2. Process and Map

```bash
# Full-state run (interactive prompt will confirm coordinates)
python src/main.py

# Targeted 100 km analysis
python src/main.py --lat -15.5 --lon -56.0 --radius 100

# Explore all CLI switches
python src/main.py --help
```

Key processing flags:

- `--lat / --lon / --radius` — Skip prompts and inject AOI coordinates directly.
- `--h3-resolution` — Choose aggregation granularity (higher = more hexes, default 7).
- `--config` — Point the pipeline at an alternate configuration document.

## Project Structure

```
Residual_Carbon/
├── src/
│   ├── data/           # Data retrieval and processing
│   ├── analysis/       # Suitability scoring
│   ├── visualization/  # Map generation
│   └── utils/          # Utility functions
├── configs/            # Configuration files
├── data/
│   ├── raw/            # GeoTIFF files from GEE
│   └── processed/      # Processed outputs and optional snapshots
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
3. **Optional clipping** (`clip_all_rasters_to_circle`) — trims rasters to the requested buffer and reports size deltas.
4. **Raster ➜ Table** (`convert_all_rasters_to_dataframes`) — flattens rasters into pandas DataFrames with coordinates, nodata handling, and unit inference.
5. **Hex indexing** (`process_dataframes_with_h3`) — injects `h3_index` plus polygon boundaries at the requested resolution.
6. **Suitability scoring** (`process_csv_files_with_suitability_scores`) — merges property tables, aggregates by hex, and applies thresholds.
7. **Visualisation** (`create_suitability_map`) — renders an interactive PyDeck map and saves it under `output/html/`.

Verification helpers such as `verify_clipping_success`, `verify_clipped_data_integrity`, and `calculate_property_score` can be run independently when you need to inspect intermediate outputs.

## Workflow Summary

1. **Data Retrieval**: Launch Drive exports from Google Earth Engine.
2. **Task Review**: Inspect task summaries and start jobs with confidence.
3. **Download**: Allow the automated Drive downloader (optional) to populate `data/raw/`.
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

## Output

The tool generates:

- **GeoTIFF files**: Raw raster data in `data/raw/`
- **CSV snapshots**: Optional debug exports and final `suitability_scores.csv` in `data/processed/`
- **HTML map**: Interactive suitability map in `output/html/`
- **Logs**: Application logs in `logs/`

## Troubleshooting Highlights

- **Re-authenticate GEE**: `python -c "import ee; ee.Authenticate()"`.
- **Drive API hiccups**: confirm `configs/client_secrets.json` exists, delete `configs/credentials.json`, and re-run the acquisition tool.
- **Missing rasters**: rerun `src/data/acquisition/gee_loader.py` and wait for Drive downloads to complete.
- **Empty CSV outputs**: make sure the clipping circle overlaps the raster (edge circles often produce sparse data—use the verification helpers to confirm coverage).

## Contributing & Support

This project is actively developed for internal research. If you have improvements or encounter issues:

- Open an issue or pull request with a clear description of the change.
- Attach sample rasters/CSVs when reporting pipeline bugs so we can reproduce them.
- Reach out to the project maintainers via the repository issue tracker for further assistance.

