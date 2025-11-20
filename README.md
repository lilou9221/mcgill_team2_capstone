# Residual_Carbon - Biochar Suitability Mapping Tool

A tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and biochar outputs.

## Project Overview

This tool analyzes soil properties (moisture, temperature, organic carbon, pH) to calculate biochar suitability scores across Mato Grosso state. The tool generates interactive maps from manually provided GeoTIFF data files:
- **Biochar Suitability Map**: Color-coded suitability scores (0-100 scale) where green indicates high suitability (poor soil needs biochar) and red indicates low suitability (healthy soil doesn't need biochar)
- **Soil Organic Carbon (SOC) Map**: Displays SOC values (g/kg) aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers
- **Soil pH Map**: Displays pH values aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers, using a diverging color scheme (light orange-yellow for acidic, yellow for neutral, blue for alkaline)

## Features

- **Automated Data Retrieval**: Launches parameterized Google Earth Engine exports with per-layer summaries and optional auto-start. Downloads from Google Drive are automatic once configured.
- **Targeted Spatial Analysis**: Works on the full Mato Grosso extent or user-specified circular AOIs with validation and graceful edge handling.
- **Robust GeoTIFF Processing**: Clips, converts, and validates rasters before tabularisation, with an in-memory pandas pipeline and optional snapshots.
- **SMAP Bicubic Downscaling**: Soil moisture and soil temperature rasters (native ~3 km) are automatically resampled to 250 m using bicubic interpolation so they align with the rest of the stack.
- **Performance Caching**: Intelligent caching system speeds up re-runs by caching clipped rasters and DataFrame conversions. Automatically detects changes and invalidates cache when source files are updated.
- **H3 Hexagonal Grid**: Adds hex indexes for efficient aggregation using vectorized operations (5-10x faster than previous implementation). Boundary geometry is generated after merge and aggregation to optimize memory usage (prevents memory crashes with large datasets).
- **Biochar Suitability Scoring**: Calculates biochar suitability scores (0-100 scale) based on soil quality metrics. Uses weighted scoring for moisture, organic carbon (averages b0 and b10 depth layers), pH (averages b0 and b10 depth layers), and temperature properties. Lower soil quality = higher biochar suitability.
- **Smart Dataset Filtering**: Automatically filters to only scoring-required datasets during processing. All datasets are exported to Google Drive, but only scoring-required files (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature) are imported for processing, reducing memory usage and processing time.
- **Interactive Maps**: Generates three PyDeck-based HTML visualisations:
  - **Biochar Suitability Map**: Interactive map with color-coded suitability scores (0-100 scale), suitability grades, H3 hexagon indexes, location coordinates, and point counts
  - **Soil Organic Carbon (SOC) Map**: Interactive map showing SOC values (g/kg) aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers
  - **Soil pH Map**: Interactive map showing pH values aggregated by H3 hexagons, calculated as the average of b0 and b10 depth layers, with a diverging color scheme (light orange-yellow for acidic soils <5.5, yellow for neutral ~7, blue for alkaline soils >7.5)
  - All maps are generated directly from CSV data using PyDeck and auto-open in browser (configurable)
- **Auditable Workflow**: Each stage can be run independently, and helper utilities exist to verify intermediate results.

## Installation

### Prerequisites

- Python 3.9 or higher
- GeoTIFF data files (manually placed in `data/raw/` directory)
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

> ⚠️ Raster libraries ship native binaries. On Windows we recommend installing them with Conda first.

```bash
# Linux / macOS (single step)
pip install -r requirements.txt

# Windows (two step)
conda install -c conda-forge geopandas rasterio shapely fiona pyproj gdal
pip install -r requirements.txt
```

### Step 4: Prepare Data Files

**Manual Data Placement:**

1. Place your GeoTIFF data files in the `data/raw/` directory:
   ```bash
   data/raw/
   ├── SOC_res_250_b0.tif
   ├── SOC_res_250_b10.tif
   ├── soil_moisture_res_250_sm_surface.tif
   ├── soil_pH_res_250_b0.tif
   ├── soil_pH_res_250_b10.tif
   └── soil_temp_res_250_soil_temp_layer1.tif
   ```

2. **Required files for scoring:**
   - Soil moisture: `soil_moisture_res_250_sm_surface.tif`
   - Soil Organic Carbon: `SOC_res_250_b0.tif`, `SOC_res_250_b10.tif`
   - Soil pH: `soil_pH_res_250_b0.tif`, `soil_pH_res_250_b10.tif`
   - Soil temperature: `soil_temp_res_250_soil_temp_layer1.tif`

3. **Optional files:**
   - Land cover, soil type (not used in scoring but can be included)

**Note:** Data files can be obtained from any source (Google Earth Engine, other providers, or existing datasets). The tool processes whatever GeoTIFF files are placed in `data/raw/`.

### Step 5: Configuration (Optional - Only for Data Acquisition)

**No configuration is required for core functionality** - the tool works with sensible defaults.

The `config.yaml` file is **only needed** if you want to use the optional GEE export scripts to export data from Google Earth Engine. For normal usage with manually placed data files, you don't need any configuration.

**If you need to export data from GEE:**

1. Copy the example configuration:
   ```bash
   cp configs/config.example.yaml configs/config.yaml
   ```

2. Edit `configs/config.yaml` and fill in your GEE/Drive values:
   ```yaml
   gee:
     project_name: "your-gee-project-id"
     export_folder: "your-google-drive-folder-id"
   ```

3. See `src/data/acquisition/README_TEMPLATE.md` for detailed instructions.

**Note:** The core pipeline processes local GeoTIFF files and doesn't require any configuration.

## Configuration

**No configuration is required for core functionality** - the tool works with sensible defaults.

The `config.yaml` file is **only needed** if you want to use the optional GEE export scripts (see `src/data/acquisition/README_TEMPLATE.md`). For normal usage with manually placed data files, no configuration is needed.

**Default Settings (work out of the box):**
- Data directories: `data/raw`, `data/processed`
- Output directories: `output/html`
- H3 resolution: 7 for clipped areas, 9 for full state SOC map, 5 for full state suitability map
- Processing: Caching enabled, snapshots disabled

**Note**: 
- The pipeline automatically filters out old 3000m resolution SMAP files when 250m versions are available. Only the higher-resolution 250m files are used for processing.
- Only scoring-required datasets are processed (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature). Other datasets (land_cover, soil_type) are automatically excluded from processing to optimize performance.
- **Configuration is optional**: The tool works entirely with local data files and default settings. `config.yaml` is only needed for optional GEE export features.

## Usage

### 1. Prepare Data Files

**Manually place GeoTIFF files in `data/raw/` directory:**

The tool processes GeoTIFF files that you manually place in the `data/raw/` directory. Data acquisition is done outside the codebase - you can obtain data from any source (Google Earth Engine, other providers, or existing datasets).

**Required files for biochar suitability scoring:**
- `soil_moisture_res_250_sm_surface.tif`
- `SOC_res_250_b0.tif`
- `SOC_res_250_b10.tif`
- `soil_pH_res_250_b0.tif`
- `soil_pH_res_250_b10.tif`
- `soil_temp_res_250_soil_temp_layer1.tif`

**File naming:** The tool recognizes files by keywords in their names (e.g., "moisture", "SOC", "ph", "temp"). Files should be GeoTIFF format (.tif or .tiff extension).

**Note:** If you need to export data from Google Earth Engine, you can use the optional scripts in `src/data/acquisition/`. However, this is not required - you can use data from any source as long as it's in GeoTIFF format.

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
- `--h3-resolution` — Choose aggregation granularity for clipped areas (higher = more hexes, default 7). Full state uses resolution 5 for suitability map and resolution 9 for SOC map automatically.
- `--config` — Point the pipeline at an alternate configuration document.

## Project Structure

```
Residual_Carbon/
├── scripts/           # Helper CLI utilities (run_analysis, optional GEE export scripts)
├── src/
│   ├── data/           # Data retrieval and processing
│   ├── analysis/       # Suitability scoring
│   ├── visualization/  # Map generation
│   └── utils/          # Utility functions (includes cache utilities)
├── configs/            # Configuration files
├── data/
│   ├── raw/            # GeoTIFF files from GEE
│   └── processed/      # Processed outputs and optional snapshots
│       └── cache/      # Cache directory (clipped rasters, DataFrames, H3 indexes)
│           ├── clipped_rasters/    # Cached clipped GeoTIFF files
│           ├── raster_to_dataframe/ # Cached DataFrame Parquet files
│           └── h3_indexes/         # Cached H3-indexed DataFrame Parquet files
├── output/
│   ├── maps/           # Generated maps
│   └── html/           # HTML map files
├── logs/               # Application logs
├── requirements.txt    # Python dependencies
├── config.yaml         # Main configuration
└── README.md           # This file
```

### Utility Scripts

All helper/automation scripts now live under `scripts/` to keep the repository root tidy:

- `scripts/run_analysis.py` – wrapper script to invoke `src/main.py`.
- `scripts/retry_exports.py` – optional script for GEE exports (not required for local use).
- `scripts/check_export_status.py` – optional script for checking GEE export status (not required for local use).

Call them with `python scripts/<script_name>.py [...]` from the project root.

## Processing Pipeline

The core pipeline lives in `src/main.py` and wires high-level helpers from each submodule:

1. **Data validation** (`ensure_rasters_acquired`) — confirms GeoTIFFs exist in `data/raw/` before doing any expensive work. Files should be manually placed in this directory.
2. **AOI selection** (`get_user_area_of_interest`) — validates coordinates, radius, and provides a full-state fallback.
3. **Optional clipping** (`clip_all_rasters_to_circle`) — trims rasters to the requested buffer and reports size deltas. **Cached** to speed up re-runs (see Caching System section).
4. **Raster ➜ Table** (`convert_all_rasters_to_dataframes`) — flattens rasters into pandas DataFrames with coordinates, nodata handling, and unit inference. **Cached** as Parquet files for fast loading (see Caching System section).
5. **Hex indexing** (`process_dataframes_with_h3`) — injects `h3_index` at the requested resolution using vectorized operations (5-10x faster than previous implementation). Boundary geometry is excluded during indexing and merging to optimize memory usage. **Cached** to speed up re-runs (see Caching System section).
6. **Data merging and aggregation** (`merge_and_aggregate_soil_data`) — merges property tables (without boundaries), aggregates by hex, and generates boundaries for aggregated hexagons only.
7. **Biochar suitability scoring** (`calculate_biochar_suitability_scores`) — calculates biochar suitability scores based on soil quality metrics. For SOC and pH, averages both b0 (surface) and b10 (10cm depth) layers to provide a more representative soil profile assessment. Uses weighted scoring for moisture, organic carbon, pH, and temperature properties.
8. **Visualisation** — renders three interactive PyDeck maps directly from CSV data:
   - **Biochar Suitability Map** (`create_biochar_suitability_map`) — saves `biochar_suitability_map.html` and `suitability_map.html` (Streamlit-compatible copy)
   - **Soil Organic Carbon Map** (`create_soc_map`) — saves `soc_map.html` and `soc_map_streamlit.html` showing SOC values aggregated by H3 hexagons
   - **Soil pH Map** (`create_ph_map`) — saves `ph_map.html` and `ph_map_streamlit.html` showing pH values aggregated by H3 hexagons with diverging color scheme
   - All maps are saved under `output/html/` and auto-open in browser (configurable)

Verification helpers such as `verify_clipping_success` and `verify_clipped_data_integrity` can be run independently when you need to inspect intermediate outputs.

## Workflow Summary

1. **Data Preparation**: Manually place GeoTIFF data files in `data/raw/` directory (data acquisition is done outside the codebase).
2. **Processing**: Run `python src/main.py` with or without coordinates to process the local data files.
3. **Score & Map**: Review the returned DataFrame (optionally written to `data/processed/merged_soil_data.csv`), suitability scores CSV (`data/processed/suitability_scores.csv`), and interactive maps:
   - `output/html/biochar_suitability_map.html` — Biochar suitability map
   - `output/html/suitability_map.html` — Streamlit-compatible copy of suitability map
   - `output/html/soc_map.html` — Soil Organic Carbon map
   - `output/html/soc_map_streamlit.html` — Streamlit-compatible copy of SOC map
   - `output/html/ph_map.html` — Soil pH map
   - `output/html/ph_map_streamlit.html` — Streamlit-compatible copy of pH map
6. **Validate (optional)**: Run the helper verification functions if you need to sanity-check inputs or radius coverage.

## Data Sources

### Scoring-Required Datasets (Used in Biochar Suitability Calculation)
- **Soil Moisture**: NASA SMAP (NASA/SMAP/SPL4SMGP/008) - surface layer
- **Soil Temperature**: NASA SMAP (NASA/SMAP/SPL4SMGP/008) - layer 1
- **Soil Organic Carbon**: OpenLandMap (OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02) - **b0 (surface) and b10 (10cm) layers averaged**
- **Soil pH**: OpenLandMap (OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02) - **b0 (surface) and b10 (10cm) layers averaged**

### Optional Datasets (Exported but Not Used in Scoring)
- **Soil Type**: OpenLandMap (OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02) - Available in Google Drive but not imported for processing
- **Land Cover**: ESA WorldCover (ESA/WorldCover/v100) - Available in Google Drive but not imported for processing

**Note**: All datasets are exported to Google Drive, but only scoring-required datasets are imported and processed to optimize performance.

### SMAP Downscaling

- SMAP soil moisture/temperature arrive at ~3000 m native resolution.
- During `load_datasets()` the rasters are resampled to 250 m with bicubic interpolation (see `src/data/acquisition/smap_downscaling.py`).
- All exports and downstream processing use the bicubic-resampled outputs at 250 m resolution.

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

3. **H3 Indexes Cache** (`data/processed/cache/h3_indexes/`)
   - Caches H3-indexed DataFrames as Parquet files
   - Based on input DataFrames and H3 resolution
   - Automatically invalidates when input DataFrames change
   - **Time savings**: ~50% (skips H3 index generation for large datasets)
   - **Note**: Uses vectorized operations for faster indexing (5-10x faster than previous implementation)

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
- **Note**: Only scoring-required files are processed from the manually placed GeoTIFF files in `data/raw/`

### Automatic
All optimizations are built-in and require no configuration. The pipeline automatically handles these optimizations at the optimal stages.

## Output

The tool generates:

- **GeoTIFF files**: Raw raster data in `data/raw/`
- **CSV files**: 
  - `merged_soil_data.csv` - Merged and aggregated soil data in `data/processed/`
  - `suitability_scores.csv` - Biochar suitability scores with `suitability_score` column (0-10 scale) for Streamlit compatibility in `data/processed/`
- **Cache files**: Cached clipped rasters, DataFrames, and H3 indexes in `data/processed/cache/`
- **HTML maps**: Interactive maps in `output/html/`:
  - `biochar_suitability_map.html` - Main interactive biochar suitability map with scores (0-100 scale)
  - `suitability_map.html` - Streamlit-compatible copy of suitability map
  - `soc_map.html` - Main interactive Soil Organic Carbon map showing SOC values (g/kg) aggregated by H3 hexagons
  - `soc_map_streamlit.html` - Streamlit-compatible copy of SOC map
  - `ph_map.html` - Main interactive Soil pH map showing pH values aggregated by H3 hexagons
  - `ph_map_streamlit.html` - Streamlit-compatible copy of pH map
- **Logs**: Application logs in `logs/`

### Streamlit Integration

The tool generates files specifically for Streamlit web interface compatibility:
- `suitability_scores.csv` contains scores scaled to 0-10 (from internal 0-100 scale) with `suitability_score` column
- `suitability_map.html` is a copy of the main suitability map file for Streamlit to display
- `soc_map_streamlit.html` is a Streamlit-compatible copy of the SOC map (pre-generated during analysis)
- `ph_map_streamlit.html` is a Streamlit-compatible copy of the pH map (pre-generated during analysis)
- Streamlit interface includes three tabs:
  - **Biochar Suitability**: Displays the suitability map with metrics and results table
  - **Soil Organic Carbon**: Displays the SOC map showing organic carbon values aggregated by H3 hexagons
  - **Soil pH**: Displays the pH map showing pH values aggregated by H3 hexagons with diverging color scheme
- All files are automatically generated during the analysis pipeline

## Troubleshooting Highlights

- **Missing rasters**: Ensure GeoTIFF files are manually placed in `data/raw/` directory. Files should be GeoTIFF format and contain keywords like "moisture", "SOC", "ph", or "temp" in their names.
- **No data found**: Check that required files are present: `soil_moisture_res_250_sm_surface.tif`, `SOC_res_250_b0.tif`, `SOC_res_250_b10.tif`, `soil_pH_res_250_b0.tif`, `soil_pH_res_250_b10.tif`, `soil_temp_res_250_soil_temp_layer1.tif`
- **Empty CSV outputs**: make sure the clipping circle overlaps the raster (edge circles often produce sparse data—use the verification helpers to confirm coverage).
- **Cache issues**: If you suspect cache problems, delete `data/processed/cache/` directory to force regeneration. Cache automatically invalidates when source files change, but manual deletion can help troubleshoot.
- **Parquet file errors**: Ensure `pyarrow>=10.0.0` is installed (`pip install pyarrow`). Parquet files are used for efficient DataFrame caching.

## Contributing & Support

This project is actively developed for internal research. If you have improvements or encounter issues:

- Open an issue or pull request with a clear description of the change.
- Attach sample rasters/CSVs when reporting pipeline bugs so we can reproduce them.
- Reach out to the project maintainers via the repository issue tracker for further assistance.

