# Streamlit Cloud Deployment Guide

## Data Storage Strategy

Most data files are stored directly in the GitHub repository. Only the largest file (`soil_moisture_res_250_sm_surface.tif`, 59MB) is hosted on Cloudflare R2 to stay within GitHub's 100MB file limit.

### Files in GitHub Repository

| File | Size |
|------|------|
| `BR_Municipios_2024_simplified.*` (shapefile) | 11MB total |
| `brazil_crop_harvest_area_2017-2024.csv` | 25MB |
| `soil_temp_res_250_soil_temp_layer1.tif` | 40MB |
| `SOC_res_250_b0.tif`, `SOC_res_250_b10.tif` | 3MB each |
| `soil_pH_res_250_b0.tif`, `soil_pH_res_250_b10.tif` | 5MB each |
| `Updated_municipality_crop_production_data.csv` | 1.6MB |
| `residue_ratios.csv` | 179B |

### Files on Cloudflare R2

| File | Size | R2 URL |
|------|------|--------|
| `soil_moisture_res_250_sm_surface.tif` | 59MB | `https://pub-d86172a936014bdc9e794890543c5f66.r2.dev/` |

The R2 bucket has public read access enabled with no bandwidth limits.

## Automatic Download

**The Streamlit app automatically downloads the soil moisture file from R2 on first launch** if it's missing. The download uses:

- 10-minute timeout for large files
- 1MB chunk streaming to avoid memory issues
- Size verification to detect incomplete downloads
- Cached download status to prevent redundant downloads

## Manual Download

You can also download manually:

```bash
# Ensure requests is installed
pip install -r requirements.txt

# Download from Cloudflare R2 (default)
python scripts/download_assets.py

# Force re-download
python scripts/download_assets.py --force
```

## Streamlit Cloud Deployment

1. **Connect the repository:** `https://github.com/lilou9221/mcgill_team2_capstone`
2. **Set main module:** `streamlit_app.py`
3. **Set branch:** `main`
4. **Deploy:** The app downloads the soil moisture file automatically on first run (~2-5 minutes)

### Performance Optimizations

- **File checks cached** (TTL: 1 hour) to avoid repeated filesystem queries
- **Data loading cached** (TTL: 1 hour) to reduce I/O
- **Shapefile simplified** to 5MB (from 287MB) for faster loading
- **Session state tracking** prevents redundant operations

## Local Development

```bash
# Clone repository
git clone https://github.com/lilou9221/mcgill_team2_capstone.git
cd mcgill_team2_capstone

# Install dependencies
pip install -r requirements.txt

# Download soil moisture file (only file not in repo)
python scripts/download_assets.py

# Run app
streamlit run streamlit_app.py
```

## Troubleshooting

### Download Fails

- **Check network**: Ensure internet access
- **Check R2 status**: https://www.cloudflarestatus.com/
- **Review errors**: The download script shows detailed error messages

### Port Already in Use

```bash
streamlit run streamlit_app.py --server.port 8502
```

### Files Missing After Clone

All files except soil moisture are in the Git repository. If files are missing:

1. Ensure Git LFS is not filtering files: `git lfs uninstall`
2. Re-clone the repository
3. Run `python scripts/download_assets.py` for soil moisture
