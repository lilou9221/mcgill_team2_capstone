# Data Acquisition Template - Google Earth Engine Export

**NOTE:** This is a **template/reference guide only**. Data acquisition is done manually outside the codebase.

GeoTIFF files should be manually placed in `data/` directory (flat structure). The core pipeline does not require these scripts.

## Purpose

This directory contains **optional utility scripts** that can be used to export data from Google Earth Engine if you need to obtain new data. These scripts are **not required** for the core pipeline to function.

## How to Use (If Needed)

**IMPORTANT:** These scripts are **non-functional templates** until you provide your credentials.

If you want to export new data from Google Earth Engine:

### Step 1: Set Up Configuration (REQUIRED)

1. Copy `configs/config.template.yaml` to `configs/config.yaml`
2. **Fill in your actual credentials** (replace placeholders):
   ```yaml
   gee:
     project_name: "your-actual-gee-project-id"  # Replace YOUR_GEE_PROJECT_ID
     export_folder: "your-actual-google-drive-folder-id"  # Replace YOUR_GOOGLE_DRIVE_FOLDER_ID
   ```
   
   **Without these credentials, the scripts will fail with clear error messages.**

### Step 2: Authenticate with Google Earth Engine

```bash
python -c "import ee; ee.Authenticate()"
```

### Step 3: Run Export Script

```bash
python src/data_acquisition/data_loader.py
```

This will:
- Load datasets from Google Earth Engine
- Create export tasks to Google Drive
- You can then manually download the exported GeoTIFF files
- Place the downloaded files in `data/` directory (flat structure)

### Step 4: Manual Data Placement

After exports complete:
1. Download GeoTIFF files from Google Drive
2. Manually place them in `data/` directory (flat structure)
3. Run the main pipeline: `python src/main.py`

## Files in This Directory

- `gee_loader.py` - Google Earth Engine data loader template (requires `earthengine-api` and credentials)
- `smap_downscaling.py` - SMAP dataset downscaling utilities
- `data_loader.py` - Main export script template
- `README_TEMPLATE.md` - This file (usage instructions)

## Required Configuration Files

To make these scripts functional, you need:

1. **`configs/config.yaml`** - Copy from `configs/config.template.yaml` and fill in:
   - `gee.project_name` - Your GEE project ID (replace `YOUR_GEE_PROJECT_ID`)
   - `gee.export_folder` - Your Google Drive folder ID (replace `YOUR_GOOGLE_DRIVE_FOLDER_ID`)

2. **`configs/settings.yaml`** (optional, for Google Drive API) - Copy from `configs/settings.yaml.template` and fill in:
   - `client_id` - Google OAuth client ID (replace `YOUR_CLIENT_ID_HERE`)
   - `client_secret` - Google OAuth client secret (replace `YOUR_CLIENT_SECRET_HERE`)

**Without these files and credentials, the scripts will NOT function and will show clear error messages.**

## Important Notes

- **These scripts are templates** - They are non-functional until you provide credentials
- **Core pipeline is independent** - The main application works with manually placed GeoTIFF files
- **No cloud services required for core** - Only needed if you want to export new data from GEE
- **Data acquisition is manual** - Export scripts are optional utilities, not part of the core workflow

## Alternative Data Sources

You can obtain GeoTIFF files from any source:
- Google Earth Engine (using these scripts)
- Other providers
- Existing datasets
- Manual downloads

As long as files are in GeoTIFF format and placed in `data/`, the pipeline will process them.

