# Data Acquisition Template - Google Earth Engine Export

**NOTE:** This is a **template/reference guide only**. Data acquisition is done manually outside the codebase.

GeoTIFF files should be manually placed in `data/raw/` directory. The core pipeline does not require these scripts.

## Purpose

This directory contains **optional utility scripts** that can be used to export data from Google Earth Engine if you need to obtain new data. These scripts are **not required** for the core pipeline to function.

## How to Use (If Needed)

If you want to export new data from Google Earth Engine:

### Step 1: Set Up Configuration

1. Copy `configs/config.example.yaml` to `configs/config.yaml`
2. Fill in your Google Earth Engine project ID:
   ```yaml
   gee:
     project_name: "your-gee-project-id"
     export_folder: "your-google-drive-folder-id"
   ```

### Step 2: Authenticate with Google Earth Engine

```bash
python -c "import ee; ee.Authenticate()"
```

### Step 3: Run Export Script

```bash
python src/data_loader.py
```

This will:
- Load datasets from Google Earth Engine
- Create export tasks to Google Drive
- You can then manually download the exported GeoTIFF files
- Place the downloaded files in `data/raw/` directory

### Step 4: Manual Data Placement

After exports complete:
1. Download GeoTIFF files from Google Drive
2. Manually place them in `data/raw/` directory
3. Run the main pipeline: `python src/main.py`

## Files in This Directory

- `gee_loader.py` - Google Earth Engine data loader (requires `earthengine-api`)
- `smap_downscaling.py` - SMAP dataset downscaling utilities
- `data_loader.py` (in parent `src/` directory) - Main export script

## Important Notes

- **These scripts are optional** - The core pipeline works with manually placed GeoTIFF files
- **No cloud services required** - The main application processes local files only
- **Data acquisition is manual** - Export scripts are utilities, not part of the core workflow
- **Configuration is optional** - Only needed if you want to use these export utilities

## Alternative Data Sources

You can obtain GeoTIFF files from any source:
- Google Earth Engine (using these scripts)
- Other providers
- Existing datasets
- Manual downloads

As long as files are in GeoTIFF format and placed in `data/raw/`, the pipeline will process them.

