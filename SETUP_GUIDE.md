# Setup Guide - Residual_Carbon

## Quick Setup Checklist

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (including raster libraries)
- [ ] GeoTIFF data files manually placed in `data/raw/` directory
- [ ] (Optional) Configuration file updated (`configs/config.yaml`) for custom settings

## Detailed Setup Instructions

### 1. Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 2. Install Dependencies

**Windows (Recommended two-step):**
```bash
conda install -c conda-forge geopandas rasterio shapely fiona pyproj gdal
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
pip install -r requirements.txt
```

**Note**: The tool requires `pyarrow>=10.0.0` for efficient DataFrame caching (Parquet file support). This is automatically installed via `requirements.txt`, but if you encounter Parquet-related errors, ensure it's installed: `pip install pyarrow>=10.0.0`.

### 3. Prepare Data Files

**Manual Data Placement:**

1. **Obtain GeoTIFF data files** from any source (Google Earth Engine, other providers, or existing datasets).

2. **Place files in `data/raw/` directory:**
   ```bash
   data/raw/
   ├── SOC_res_250_b0.tif
   ├── SOC_res_250_b10.tif
   ├── soil_moisture_res_250_sm_surface.tif
   ├── soil_pH_res_250_b0.tif
   ├── soil_pH_res_250_b10.tif
   └── soil_temp_res_250_soil_temp_layer1.tif
   ```

3. **Required files for biochar suitability scoring:**
   - `soil_moisture_res_250_sm_surface.tif` - Soil moisture
   - `SOC_res_250_b0.tif` - Soil Organic Carbon (surface)
   - `SOC_res_250_b10.tif` - Soil Organic Carbon (10cm depth)
   - `soil_pH_res_250_b0.tif` - Soil pH (surface)
   - `soil_pH_res_250_b10.tif` - Soil pH (10cm depth)
   - `soil_temp_res_250_soil_temp_layer1.tif` - Soil temperature

4. **File naming:** The tool recognizes files by keywords in their names (e.g., "moisture", "SOC", "ph", "temp"). Files should be GeoTIFF format (.tif or .tiff extension).

**Note:** Data acquisition is done manually outside the codebase. You can obtain data from any source as long as files are in GeoTIFF format and placed in `data/raw/`.

### 4. (Optional) Configuration

Configuration is optional - the tool works with sensible defaults. If you want to customize settings:

1. Copy the example configuration:
   ```bash
   cp configs/config.example.yaml configs/config.yaml
   ```

2. Edit `configs/config.yaml` to customize:
   - Data directories (default: `data/raw`, `data/processed`)
   - Output directories (default: `output/html`)
   - H3 resolution (default: 7)
   - Processing options

### 5. Verify Installation

```bash
# Test critical imports
python -c "import h3, rasterio, shapely, geopandas; print('Core imports OK')"

# Verify data files are present
python -c "from pathlib import Path; files = list(Path('data/raw').glob('*.tif')); print(f'Found {len(files)} GeoTIFF files')"
```

### 6. (Optional) Add Project to PYTHONPATH

If you run scripts from terminals outside PyCharm, add the project root to `PYTHONPATH` so imports work everywhere:

1. Open **System Properties** → **Environment Variables**.
2. Under **User variables**, create or edit `PYTHONPATH` and set it to the absolute path of this project, for example:
   ```
   C:\path\to\Residual_Carbon
   ```
   (Replace `C:\path\to` with the real location on your machine.)
3. Close all shells and reopen them so the change takes effect.
4. You can achieve the same result from PowerShell:
   ```powershell
   $projectRoot = "C:\path\to\Residual_Carbon"
   [Environment]::SetEnvironmentVariable("PYTHONPATH", $projectRoot, "User")
   ```
5. On macOS/Linux, add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):
   ```bash
   export PYTHONPATH="/path/to/Residual_Carbon"
   ```

### 6. (Optional) Configuration

Configuration is optional - the tool works with sensible defaults. If you want to customize settings, edit `configs/config.yaml`:

- **Data Directories**: Default `data/raw` and `data/processed`
- **Output Directories**: Default `output/html`
- **H3 Resolution**: Default 7 for clipped areas (higher = finer hexagons). Full state uses resolution 5 for suitability map and resolution 9 for SOC map automatically.
- **Persist Snapshots**: Set `processing.persist_snapshots` to `true` to keep intermediate CSV tables for debugging
- **Cache Cleanup**: Set `processing.cleanup_old_cache` to `false` to disable automatic cleanup of old coordinate-specific caches (default: `true`)
- **Dataset Filtering**: Only scoring-required datasets are processed (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature). Other datasets (land_cover, soil_type) are automatically excluded from processing.
- **Depth Layers**: For SOC and pH, both b0 (surface) and b10 (10cm depth) layers are used and averaged in the scoring calculation. Deeper layers (b30, b60) are not processed as they are not used in scoring.

## Troubleshooting

### Issue: "No GeoTIFF files found"

**Solution:**
1. Ensure GeoTIFF files are manually placed in `data/raw/` directory
2. Check that files have `.tif` or `.tiff` extension
3. Verify required files are present:
   - `soil_moisture_res_250_sm_surface.tif`
   - `SOC_res_250_b0.tif`
   - `SOC_res_250_b10.tif`
   - `soil_pH_res_250_b0.tif`
   - `soil_pH_res_250_b10.tif`
   - `soil_temp_res_250_soil_temp_layer1.tif`
4. Files are recognized by keywords in their names (e.g., "moisture", "SOC", "ph", "temp")

### Issue: Cache not working or Parquet errors

**Solution:**
1. **Parquet support**: Ensure `pyarrow>=10.0.0` is installed: `pip install pyarrow>=10.0.0`
2. **Cache directory**: The cache is automatically created in `data/processed/cache/` during first run
3. **Clear cache**: If you suspect cache issues, delete `data/processed/cache/` directory:
   ```bash
   # Windows
   rmdir /s /q data\processed\cache
   
   # Linux/Mac
   rm -rf data/processed/cache
   ```
4. **Cache validation**: Cache automatically invalidates when source files change (checks modification times)
5. **First run**: Cache is created during normal processing (this is expected - subsequent runs will use cache)
6. **Check cache usage**: Look for "Using cached..." messages in the output to confirm cache is being used

## Performance Optimization (Caching)

The tool includes an intelligent caching system that significantly speeds up re-runs:

### How Caching Works

- **First run**: Cache is created during normal processing (clipped rasters and DataFrame conversions)
- **Subsequent runs**: Cache is automatically used if valid (same inputs and parameters)
- **Cache validation**: Automatically checks source file modification times to detect changes
- **Automatic invalidation**: Cache is invalidated if source files change or parameters differ
- **Transparent**: Caching is enabled by default and requires no configuration

### Cache Types

1. **Clipped Raster Cache** (`data/processed/cache/clipped_rasters/`)
   - Caches clipped GeoTIFF files based on coordinates, radius, and source file metadata
   - **Time savings**: ~90% (skips expensive clipping operations)

2. **DataFrame Cache** (`data/processed/cache/raster_to_dataframe/`)
   - Caches converted DataFrames as Parquet files (faster than CSV)
   - Based on source files, conversion parameters (band, nodata handling, pattern)
   - **Time savings**: ~70% (skips expensive raster reading and DataFrame conversion)

3. **H3 Indexes Cache** (`data/processed/cache/h3_indexes/`)
   - Caches H3-indexed DataFrames as Parquet files
   - Based on input DataFrames and H3 resolution
   - **Time savings**: ~50% (skips H3 index generation for large datasets)
   - **Performance**: Uses vectorized operations (5-10x faster than previous implementation)

### Cache Management

- **Location**: `data/processed/cache/`
- **Size**: Typically 10-100 MB depending on area size and number of datasets
- **Automatic cleanup**: Old coordinate-specific caches are automatically cleaned up on each run
  - Preserved caches: Full state cache (no coordinates), protected coordinates (-13, -56, 100km), and current coordinates (same lat/lon/radius as current run)
  - Only old coordinate-specific caches (clipped_rasters) that don't match the above are removed
  - A message is displayed showing how many old caches were cleaned up
  - Can be disabled by setting `processing.cleanup_old_cache: false` in config
- **Manual clearing**: Delete `data/processed/cache/` directory to force regeneration of all caches
- **Git ignore**: Cache files are excluded from Git (see `.gitignore`)

### Benefits

- **Faster re-runs**: Re-running the same analysis is much faster
- **Development speed**: Faster iteration when testing different parameters
- **Resource efficiency**: Reduces CPU and I/O usage for repeated operations
- **Automatic**: No manual configuration required, works out of the box

## Performance & Memory Optimization

The pipeline includes several built-in optimizations to handle large datasets efficiently:

### Vectorized H3 Indexing

- **Performance improvement**: Uses vectorized list comprehensions instead of row-by-row `.apply()` calls
- **Speed**: 5-10x faster for large datasets (100k+ rows)
- **Memory**: Lower memory overhead compared to `.apply()` operations
- **Automatic**: Built-in optimization, no configuration required

### H3 Boundary Generation Optimization

- **Problem**: Generating hexagon boundary geometry for all data points (e.g., 500,000+ points) can cause memory crashes, especially with large areas (100km+ radius).
- **Solution**: Boundaries are **not** generated during H3 indexing or merging. They are only generated after data is merged and aggregated by hexagon.
- **Memory savings**: ~99% reduction in boundary data:
  - **Before**: Generate boundaries for all points (e.g., 521,217 points)
  - **After**: Only generate boundaries for aggregated hexagons (e.g., 5,817 hexagons)
- **Result**: Prevents memory crashes when processing large areas
- **Automatic**: This optimization is built-in and requires no configuration

### Smart Dataset Filtering

- **Automatic filtering**: Only scoring-required datasets are imported for processing
- **Scoring-required**: soil_moisture, SOC (b0 and b10), pH (b0 and b10), soil_temperature
- **Excluded**: land_cover, soil_type (available in Google Drive but not imported)
- **Benefits**: Reduces memory usage, processing time, and cache size
- **Note**: All datasets are still exported to Google Drive, but only scoring-required files are processed

### When to Use

- **Small areas** (< 25km radius): Works smoothly with or without optimization
- **Medium areas** (25-50km radius): Optimization helps prevent memory issues
- **Large areas** (50-100km+ radius): **Essential** - prevents memory crashes

### Technical Details

The pipeline follows this optimized flow:
1. H3 indexing: Only generates `h3_index` (no boundaries)
2. Merging: Datasets merged without boundary columns
3. Aggregation: Data aggregated by hexagon
4. Boundary generation: Boundaries generated only for aggregated hexagons
5. Visualization: Map created with boundaries for visualization

## Next Steps

Once setup is complete, you can:

1. **Create GeoTIFF export tasks (interactive prompt):**
   ```bash
   python src/data/acquisition/gee_loader.py
   ```
   - Choose how many datasets to export when prompted (0 = all)
   - Review the task summary (dataset, depth band, filename, resolution, folder)
   - Start the Drive exports by responding `y` when asked, or rerun with `--start-tasks` to skip the prompt

2. **Test the processing workflow:**
   ```bash
   python src/main.py
   ```
   - The script will confirm that GeoTIFFs exist and then ask whether you want to supply coordinates if you didn’t pass `--lat/--lon`.

3. **Run with specific coordinates:**
   ```bash
   python src/main.py --lat -15.5 --lon -56.0 --radius 100
   ```
   Note: If `--radius` is not specified, the default radius is 100 km.

4. **Inspect intermediate outputs (optional):**
   ```bash
   python - <<'PY'
   from pathlib import Path
   from src.data.processing.raster_clip import verify_clipping_success
   from src.utils.geospatial import create_circle_buffer

   circle = create_circle_buffer(-15.5, -56.0, 100)
   clipped = list(Path("data/processed").glob("*.tif"))
   print("Verified:", verify_clipping_success(clipped, circle))
   PY
   ```

5. **Check expected outputs:**
   After running the analysis, you should see:
   - `data/processed/merged_soil_data.csv` - Merged and aggregated soil data
   - `data/processed/suitability_scores.csv` - Biochar suitability scores (0-10 scale) for Streamlit
   - `output/html/biochar_suitability_map.html` - Main interactive biochar suitability map
   - `output/html/suitability_map.html` - Streamlit-compatible copy of suitability map
   - `output/html/soc_map.html` - Interactive Soil Organic Carbon map
   - `output/html/soc_map_streamlit.html` - Streamlit-compatible copy of SOC map
   - `output/html/ph_map.html` - Interactive Soil pH map
   - `output/html/ph_map_streamlit.html` - Streamlit-compatible copy of pH map
   
   For Streamlit integration:
   - `suitability_scores.csv` and all map files are automatically generated during analysis
   - Streamlit interface includes three tabs: "Biochar Suitability", "Soil Organic Carbon", and "Soil pH"
   - All maps are pre-generated during analysis and ready to display in Streamlit

6. **Check project status:**
   - Review `README.md` for project overview and features
   - Check logs in `logs/residual_carbon.log` for processing status

## Support

For issues or questions:
- Review `README.md` for general information and usage
- Check `docs/TROUBLESHOOTING.md` for common issues and solutions
- Check logs in `logs/residual_carbon.log`

