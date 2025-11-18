# Setup Guide - Residual_Carbon

## Quick Setup Checklist

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (including raster libraries)
- [ ] Google Earth Engine authenticated
- [ ] Google Drive API credentials configured
- [ ] Configuration file updated (`configs/config.yaml`)
- [ ] Sample rasters exported to `data/raw/`

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

### 3. Google Earth Engine Setup

1. **Authenticate:**
   ```bash
   python -c "import ee; ee.Authenticate()"
   ```
   This will open a browser for authentication.

2. **Set project name in `configs/config.yaml`:**
   ```yaml
   gee:
     project_name: "your-project-name"
   ```

### 4. Google Drive API Setup (Required for Automatic Downloads)

The tool automatically downloads exported GeoTIFF files from Google Drive once configured. Set up the Google Drive API to enable automatic downloads:

#### Step 4.1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### Step 4.2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External (or Internal if using Google Workspace)
   - App name: "Residual_Carbon"
   - Scopes: Add `https://www.googleapis.com/auth/drive.readonly`
   - Save and continue
4. Application type: **Desktop application**
5. Name: "Residual_Carbon Desktop Client"
6. Click "Create"
7. Download the JSON file (it will be named something like `client_secret_xxxxx.json`)

#### Step 4.3: Configure PyDrive

1. **Rename the downloaded file:**
   ```bash
   # Rename the downloaded JSON file to:
   configs/client_secrets.json
   ```

2. **First-time authentication:**
   - When you first run the acquisition tool, it will automatically:
     - Open a browser for OAuth authentication
     - Create `configs/credentials.json` (stores your access token)
     - Create `configs/settings.yaml` (PyDrive configuration)
   - You only need to do this once
   - Once configured, all exported files will be automatically downloaded to `data/raw/` as GEE export tasks complete

#### Alternative: Manual PyDrive Setup

If you prefer to set up PyDrive manually:

1. Copy `configs/settings.yaml.template` to `configs/settings.yaml`
2. Extract `client_id` and `client_secret` from your `client_secrets.json`
3. Update `configs/settings.yaml` with your credentials

### 5. Verify Installation

```bash
# Test critical imports
python -c "import ee, h3, rasterio, shapely; print('Core imports OK')"

# Confirm Google Earth Engine access
python -c "import ee; ee.Initialize(); print('GEE initialized successfully!')"
```

> Tip: you can run `python src/data/acquisition/gee_loader.py` and answer "n" when prompted to leave tasks pending while reviewing the export summary.

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

### 7. Configuration

Edit `configs/config.yaml` to customize:

- **GEE Project Name**: Your Google Earth Engine project name
- **Export Resolution**: Default 1000m (affects processing time and file size)
- **H3 Resolution**: Default 7 for clipped areas (higher = finer hexagons). Full state uses resolution 5 automatically.
- **Export Folder**: Must match in both `gee.export_folder` and `drive.download_folder`
- **Persist Snapshots**: Set `processing.persist_snapshots` to `true` to keep intermediate CSV tables for debugging
- **SMAP Resampling**: Soil moisture and soil temperature are always bicubic-resampled from ~3000 m to 250 m inside `load_datasets()`. There is intentionally no optional ML/Random-Forest toggle anymore—every run uses the bicubic outputs.

## Troubleshooting

### Issue: "No module named 'pydrive2'"

**Solution:**
```bash
pip install pydrive2
```

### Issue: Google Earth Engine Authentication Error

**Solution:**
```bash
# Re-authenticate
python -c "import ee; ee.Authenticate()"
```

### Issue: Google Drive API Authentication Error

**Solution:**
1. Delete `configs/credentials.json` if it exists
2. Ensure `configs/client_secrets.json` is present
3. Run the tool again - it will re-authenticate

### Issue: "Drive API not enabled"

**Solution:**
1. Go to Google Cloud Console
2. Enable Google Drive API (see Step 4.1 above)

### Issue: GeoTIFF files not downloading automatically

**Solution:**
1. Check that export tasks completed in Google Earth Engine Code Editor
2. Verify folder name matches in `config.yaml` (`gee.export_folder` and `drive.download_folder`)
3. Check Google Drive for the exported files
4. Verify Drive API credentials are correct (`client_secrets.json` and `credentials.json`)
5. Ensure Google Drive API is enabled in Google Cloud Console
6. Downloads happen automatically once configured - rerun `python src/data/acquisition/gee_loader.py`; the script will automatically download any completed Drive exports to `data/raw/`

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

### Cache Management

- **Location**: `data/processed/cache/`
- **Size**: Typically 10-100 MB depending on area size and number of datasets
- **Automatic cleanup**: When new coordinates are provided, old coordinate-specific caches are automatically cleaned up
  - Preserved caches: Full state cache and protected coordinates (-13, -56, 100km)
  - Only coordinate-specific caches (clipped_rasters) are cleaned up
  - A message is displayed showing how many old caches were cleaned up
- **Manual clearing**: Delete `data/processed/cache/` directory to force regeneration of all caches
- **Git ignore**: Cache files are excluded from Git (see `.gitignore`)

### Benefits

- **Faster re-runs**: Re-running the same analysis is much faster
- **Development speed**: Faster iteration when testing different parameters
- **Resource efficiency**: Reduces CPU and I/O usage for repeated operations
- **Automatic**: No manual configuration required, works out of the box

## Memory Optimization

The pipeline includes built-in memory optimizations to handle large datasets efficiently:

### H3 Boundary Generation Optimization

- **Problem**: Generating hexagon boundary geometry for all data points (e.g., 500,000+ points) can cause memory crashes, especially with large areas (100km+ radius).
- **Solution**: Boundaries are **not** generated during H3 indexing or merging. They are only generated after data is merged and aggregated by hexagon.
- **Memory savings**: ~99% reduction in boundary data:
  - **Before**: Generate boundaries for all points (e.g., 521,217 points)
  - **After**: Only generate boundaries for aggregated hexagons (e.g., 5,817 hexagons)
- **Result**: Prevents memory crashes when processing large areas
- **Automatic**: This optimization is built-in and requires no configuration

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
   - `output/html/biochar_suitability_map.html` - Main interactive map
   - `output/html/suitability_map.html` - Streamlit-compatible map (copy of main map)
   
   For Streamlit integration, both `suitability_scores.csv` and `suitability_map.html` are automatically generated.

6. **Check project status:**
   - Review `README.md` for project overview and features
   - Check logs in `logs/residual_carbon.log` for processing status

## Support

For issues or questions:
- Review `README.md` for general information and usage
- Check `docs/TROUBLESHOOTING.md` for common issues and solutions
- Check logs in `logs/residual_carbon.log`

