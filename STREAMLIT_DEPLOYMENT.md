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
data/BR_Municipios_2024.{shp, dbf, shx, prj, cpg}  # Flat structure: all files in data/
data/Updated_municipality_crop_production_data.csv
data/SOC_res_250_b0.tif
data/SOC_res_250_b10.tif
data/soil_moisture_res_250_sm_surface.tif
data/soil_pH_res_250_b0.tif
data/soil_pH_res_250_b10.tif
data/soil_temp_res_250_soil_temp_layer1.tif
```

The Drive folder may have a flat structure with all files in one folder. The download script handles both flat and nested folder structures by searching for files by name.

## Streamlit Cloud Deployment Workflow

1. **Connect the repository:** `https://github.com/lilou9221/mcgill_team2_capstone` (lowercase repository name)
2. **Set main module:** `streamlit_app.py`
3. **Set branch:** `main`
4. **Deploy:** The app will automatically download required files on first run. Allow 5-10 minutes for the initial download (~400 MB total)
5. **Subsequent restarts:** Files are cached in the container, so downloads only occur if files are missing or deleted

### Performance Optimizations

The Streamlit app includes several performance optimizations:
- **File existence checks are cached** (TTL: 1 hour) to avoid repeated filesystem queries
- **CSV and HTML file reading is cached** (TTL: 1 hour) to reduce I/O on reruns
- **Session state tracking** prevents redundant download checks
- **Download status message** automatically clears when download completes

## Local Development Workflow

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lilou9221/mcgill_team2_capstone.git
   cd mcgill_team2_capstone
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download data files (first time only):**
   ```bash
   python scripts/download_assets.py
   ```
   
   Or let the Streamlit app download them automatically on first run.

4. **Launch the Streamlit app:**
   ```bash
   streamlit run streamlit_app.py
   ```

## Troubleshooting

### Download Fails

- **Verify Drive folder permissions:** The folder must be set to "Anyone with the link can view"
- **Check `gdown` installation:** Ensure `gdown` is installed (`pip install gdown`)
- **Check network connectivity:** Ensure the deployment environment has internet access
- **Review error messages:** The download script provides detailed error messages showing which files are missing

### Files Still Missing After Download

- The download script searches for files by name, so ensure files in Google Drive match expected filenames exactly
- Check that all 12 required files are present in the Drive folder:
  - 5 shapefile components (BR_Municipios_2024.*)
  - 1 CSV file (Updated_municipality_crop_production_data.csv)
  - 6 GeoTIFF files (SOC, pH, moisture, temperature)

### Performance Issues

- The app uses caching to reduce redundant operations
- First run may be slow due to data download
- Subsequent runs are faster due to cached file checks and data reads

### Common Issues

**Deprecation Warnings:**
- The app uses the new Streamlit `width` parameter instead of deprecated `use_container_width`
- All deprecation warnings have been resolved

**Port Already in Use:**
- If port 8501 is in use, run: `streamlit run streamlit_app.py --server.port 8502`
