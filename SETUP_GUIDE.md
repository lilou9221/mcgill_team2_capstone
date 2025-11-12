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

### 4. Google Drive API Setup (for Automated Download)

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
   - When you first run the tool, it will automatically:
     - Open a browser for OAuth authentication
     - Create `configs/credentials.json` (stores your access token)
     - Create `configs/settings.yaml` (PyDrive configuration)
   - You only need to do this once

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
- **H3 Resolution**: Default 6 (higher = finer hexagons)
- **Export Folder**: Must match in both `gee.export_folder` and `drive.download_folder`
- **Persist Snapshots**: Set `processing.persist_snapshots` to `true` to keep intermediate CSV tables for debugging

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

### Issue: GeoTIFF files not downloading

**Solution:**
1. Check that export tasks completed in Google Earth Engine Code Editor
2. Verify folder name matches in `config.yaml` (`gee.export_folder` and `drive.download_folder`)
3. Check Google Drive for the exported files
4. Verify Drive API credentials are correct
5. Rerun `python src/data/acquisition/gee_loader.py`; once the script detects completed Drive exports it will download them to `data/raw/`

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

5. **Check the project plan:**
   - See `PROJECT_PLAN.md` for module-by-module status

## Support

For issues or questions:
- Check `PROJECT_PLAN.md` for implementation status
- Review `README.md` for general information
- Check logs in `logs/residual_carbon.log`

