# Streamlit Cloud Deployment Notes

## Git LFS Requirements

This repository uses Git LFS for large files including:
- Municipality boundaries (`data/boundaries/BR_Municipios_2024/*.shp`, `*.dbf`, `*.shx`, etc.) - Extracted shapefile files
- GeoTIFF files (`data/raw/*.tif`)
- Other large data files

**Important**: Streamlit Cloud requires Git LFS to be available during deployment to download these files.

If you encounter errors like:
```
error: external filter 'git-lfs filter-process' failed
fatal: data/boundaries/BR_Municipios_2024.zip: smudge filter lfs failed
```

This indicates that Git LFS is not installed or configured on Streamlit Cloud.

**Note**: The zip file has been removed from the repository to reduce LFS bandwidth usage. The app uses the extracted shapefile directory (`data/boundaries/BR_Municipios_2024/`) directly.

## Solution

Streamlit Cloud should automatically handle Git LFS, but if it doesn't:

1. Ensure all LFS files are properly pushed:
   ```bash
   git lfs push --all origin
   ```

2. Verify LFS files are tracked:
   ```bash
   git lfs ls-files
   ```

3. If the issue persists, contact Streamlit support or check Streamlit Cloud documentation for Git LFS configuration.

## Files Tracked by LFS

- `data/boundaries/BR_Municipios_2024/*.shp`, `*.dbf`, `*.shx`, `*.prj`, `*.cpg` - Required for investor map (extracted shapefile files)
- `data/raw/*.tif` - GeoTIFF raster files
- Large CSV files (except `data/pyrolysis/pyrolysis_data.csv` and `pyrolysis_data_fallback.csv` which are small)


