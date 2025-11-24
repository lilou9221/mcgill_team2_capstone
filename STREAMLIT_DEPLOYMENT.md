# Streamlit Cloud Deployment Notes

## External Data Source

All heavy datasets (GeoTIFFs, boundary shapefiles, crop production CSV) are hosted in a shared Google Drive folder to avoid Git LFS bandwidth limitations:

- **Folder ID:** `1FvG4FM__Eam2pXggHdo5piV7gg2bljjt`
- **Folder URL:** https://drive.google.com/drive/folders/1FvG4FM__Eam2pXggHdo5piV7gg2bljjt

The folder must be set to **"Anyone with the link can view"** for the download to work.

Keeping data in Drive removes the Git LFS bandwidth/storage bottleneck and allows Streamlit Cloud to download assets on-demand during deployment.

## Download Script

The repository includes `scripts/download_assets.py`, which uses `gdown` to download the Drive folder and copy required files into the local `data/` directory.

### Automatic Download

**The Streamlit app automatically runs the download script on first launch** if any required files are missing. The download message will appear and disappear automatically when complete.

### Manual Download

You can also run the download script manually:

```bash
# Ensure gdown is installed
pip install -r requirements.txt

# Download all required files
python scripts/download_assets.py

# Force re-download and overwrite existing files
python scripts/download_assets.py --force
```

### How It Works

1. The script downloads the entire Google Drive folder to a temporary directory
2. Searches for required files by name (handles flat or nested folder structures)
3. Copies files to the correct locations in `data/` directory
4. Creates necessary subdirectories automatically
5. Provides detailed error messages if files are missing

## Required files pulled from Drive

```
data/boundaries/BR_Municipios_2024/BR_Municipios_2024.{shp, dbf, shx, prj, cpg}
data/crop_data/Updated_municipality_crop_production_data.csv
data/raw/SOC_res_250_b0.tif
data/raw/SOC_res_250_b10.tif
data/raw/soil_moisture_res_250_sm_surface.tif
data/raw/soil_pH_res_250_b0.tif
data/raw/soil_pH_res_250_b10.tif
data/raw/soil_temp_res_250_soil_temp_layer1.tif
```

The Drive folder mirrors the repository layout (`data/...`), so the script can copy files directly into place.

## Streamlit Cloud deployment workflow

1. **Connect the repo:** `https://github.com/lilou9221/mcgill_team2_capstone`.
2. **Set credentials/environment variables** (if any) in Streamlit Cloud.
3. **Deploy:** the app will call `scripts/download_assets.py` automatically on first run. Allow a few minutes for the initial download (~400 MB).
4. **Subsequent restarts** reuse the cached data directory, so downloads run only when files are missing.

## Local development workflow

1. Clone the repo.
2. Run `python scripts/download_assets.py` once to fetch the datasets.
3. Launch the Streamlit app as usual.

> If the download fails, verify that the Drive folder link is public (“Anyone with the link can view”) and that `gdown` is installed.
