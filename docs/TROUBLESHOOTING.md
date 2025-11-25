# Troubleshooting Guide

## Common Issues

### Missing Data Files

**Problem**: App shows "Missing required data files" error.

**Solution**: Most data files are included in the GitHub repository. Only `soil_moisture_res_250_sm_surface.tif` (59MB) is downloaded from Cloudflare R2. If download fails:

1. Check your internet connection
2. Try clicking "Reset Cache & Restart" in the sidebar
3. Manually run: `python scripts/download_assets.py`

### Coordinates Outside Mato Grosso

**Problem**: Analysis fails with coordinate validation error.

**Solution**: Use coordinates within Mato Grosso bounds:
- Latitude: -7.0 to -18.0
- Longitude: -50.0 to -62.0

### Empty Results or All NaN Scores

**Problem**: Analysis completes but results are empty or all NaN.

**Solution**:
1. Verify coordinates overlap with data coverage
2. Check that SOC and pH values exist (required for scoring)
3. Edge coordinates may have sparse data - try a more central location

### Cache Issues

**Problem**: Stale results or cache errors.

**Solution**: Clear the cache:
```bash
rm -rf data/processed/cache/
```
Or click "Reset Cache & Restart" in the Streamlit sidebar.

### Memory Issues

**Problem**: Crashes when processing large areas (100km+ radius).

**Solution**:
- Reduce radius to 50km or less
- Lower H3 resolution (e.g., 6 instead of 7)
- Ensure at least 4GB free RAM

### Maps Not Displaying

**Problem**: Maps show empty or don't load in Streamlit.

**Solution**:
1. Verify analysis completed successfully
2. Check that HTML files exist in `output/html/`
3. Try a different browser
4. Re-run the analysis

### Investor Map Not Available

**Problem**: Investor tab shows "data not available".

**Solution**: Check for required files in `data/`:
- `BR_Municipios_2024_simplified.shp` (and .dbf, .shx, .prj, .cpg)
- `Updated_municipality_crop_production_data.csv`

These files are included in the GitHub repository.

### Import Errors

**Problem**: `ModuleNotFoundError` when running scripts.

**Solution**:
```bash
# Install dependencies
pip install -r requirements.txt

# Or run from project root
cd /path/to/project
python src/main.py
```

### Parquet/Cache Errors

**Problem**: Errors related to Parquet files or pyarrow.

**Solution**:
```bash
pip install pyarrow>=10.0.0
```

### Cloudflare R2 Download Timeout

**Problem**: Soil moisture file download times out.

**Solution**:
1. The file is 59MB - allow up to 10 minutes on slow connections
2. Check Cloudflare R2 status at https://www.cloudflarestatus.com/
3. Manually download from R2 URL if needed

## Getting Help

1. Check log files in `logs/` directory
2. Review error messages for specific file/line information
3. Clear cache and retry: `rm -rf data/processed/cache/`
