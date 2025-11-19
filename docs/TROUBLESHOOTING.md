# Troubleshooting Guide

This guide helps you resolve common issues when using the Residual_Carbon biochar suitability mapping tool.

## Table of Contents

1. [Common Errors](#common-errors)
2. [Data Issues](#data-issues)
3. [Configuration Issues](#configuration-issues)
4. [Performance Issues](#performance-issues)
5. [Visualization Issues](#visualization-issues)

## Common Errors

### PermissionError: [Errno 13] Permission denied

**Problem**: Cannot write snapshot CSVs or the final suitability export during H3 conversion or scoring.

**Solution**:
- Close any programs that might have the CSV files open (Excel, text editors, etc.)
- Check file permissions on the `data/processed/` directory
- Run the script with appropriate permissions
- When automation fails mid-run, delete any partially written `.tmp` files (prefixed with `.`) so the converter can retry

### TypeError: Could not convert string to numeric

**Problem**: Non-numeric columns (like color codes) are being included in aggregation.

**Solution**:
- This has been fixed in the latest version - the code now filters to only numeric columns
- If you still see this error, check your CSV snapshots for unexpected string columns
- Ensure persisted tables only contain numeric data for soil properties

### ModuleNotFoundError

**Problem**: Missing Python packages.

**Solution**:
```bash
pip install -e .
```

Or install specific packages:
```bash
pip install earthengine-api rasterio pandas h3 pydeck shapely pyyaml pyarrow
```

**Note**: The main pipeline uses PyDeck exclusively for map generation, working directly with CSV data.

**Note**: `pyarrow>=10.0.0` is required for DataFrame caching (Parquet file support). This is automatically installed via `requirements.txt`, but if you encounter Parquet-related errors, ensure it's installed: `pip install pyarrow>=10.0.0`.

### Config file not found

**Problem**: Configuration file cannot be loaded.

**Solution**:
- Ensure `configs/config.yaml` exists
- Run the script from the project root directory
- Use `--config` flag to specify a custom config path
- If running inside PyCharm, set the working directory to the project root (`$PROJECT_DIR$`)

## Data Issues

### No GeoTIFF files found

**Problem**: `data/raw/` directory is empty or files are missing.

**Solution**:
1. Run the acquisition tool: `python src/data/acquisition/gee_loader.py`
2. When prompted, choose how many datasets to export (0 = all), review the task summary, and start the Drive tasks
3. Wait for the exports to complete in Google Earth Engine
4. **Automatic downloads**: Once Google Drive API is configured (see SETUP_GUIDE.md Step 4), files are automatically downloaded from Google Drive to `data/raw/` as export tasks complete. No manual step required.
5. If downloads are not working automatically, re-run the acquisition tool once exports complete; it will automatically download any newly available rasters to `data/raw/`
6. SMAP rasters should appear with `_res_250_...` filenames (e.g., `soil_moisture_res_250_sm_surface.tif`). The pipeline automatically filters out any old `_res_3000_...` files when 250m versions exist, so you can safely keep both in `data/raw/` - only the 250m versions will be used.
7. **Dataset filtering**: Only scoring-required datasets are imported for processing. Files like `land_cover_res_250_Map.tif` and `soil_type_res_250_b0.tif` will be in `data/raw/` (exported to Google Drive) but are automatically excluded from processing. This is expected behavior - only scoring-required files (soil_moisture, SOC b0/b10, pH b0/b10, soil_temperature) are processed.
8. **Depth layers**: For SOC and pH, ensure both `*_b0.tif` and `*_b10.tif` files are present. The system averages both layers for more accurate scoring. Deeper layers (b30, b60) are not needed.

### Final merged data CSV is empty

**Problem**: The exported `merged_soil_data.csv` (or optional snapshots) contains no data.

**Solution**:
- Check that GeoTIFF files are valid and not corrupted
- Verify the clipping area intersects with the data
- Check for NoData values in the GeoTIFF files
- If your circle sits on the edge of the dataset (common near state boundaries), expect large nodata regions; this is fine as long as some valid pixels remain
- When working purely in memory, inspect the DataFrames returned from the conversion step before writing snapshots

### Biochar suitability scores are all zero or NaN

**Problem**: All biochar suitability scores are 0.0 or NaN.

**Solution**:
- Verify the in-memory tables contain the required soil property columns (moisture, SOC, pH, temperature)
- Check that property values are within expected ranges
- Ensure SOC and pH values are present (these are required for biochar suitability calculation)
  - **Note**: The system uses both b0 (surface) and b10 (10cm depth) layers for SOC and pH, averaging them when both are available
  - If only one layer is available, it will use that layer
- Check that moisture and temperature have valid values or will use default values (50% moisture, 20°C temperature)
- Inspect the biochar suitability score columns to see which properties might be causing issues
- Verify that b0 and b10 files are present in `data/raw/` for SOC and pH datasets

## Configuration Issues

### Invalid H3 resolution

**Problem**: H3 resolution is outside valid range (0-15).

**Solution**:
- Use `--h3-resolution` flag with a value between 0 and 15
- Default is 7 (recommended for most use cases)
- Higher values = finer hexagons (more detail, larger files)

### Coordinates outside Mato Grosso

**Problem**: Input coordinates are outside the state bounds.

**Solution**:
- Use coordinates within Mato Grosso bounds:
  - Latitude: -7.0 to -18.0
  - Longitude: -50.0 to -62.0
- Or omit coordinates to use the full state
- If you are unsure, run `python src/main.py` without flags; the CLI will prompt you and display the valid ranges before accepting coordinates

### Circle partially outside dataset

**Problem**: You selected coordinates near the edge of the available rasters, so the clipped output contains many NaNs.

**Solution**:
- This is expected. The verification helpers (`verify_clipping_success`, `verify_clipped_data_integrity`) already ignore nodata pixels outside the circle and only check that remaining pixels stay inside the radius.
- As long as the pipeline reports success, you can proceed; hexagons with insufficient data are skipped automatically during scoring.
- To double-check, call `verify_clipped_data_integrity` manually with the circle geometry and compare the console warnings.

## Performance Issues

### Slow processing

**Problem**: Steps take a long time to complete.

**Solution**:
- **Cache is enabled by default**: The tool automatically caches clipped rasters and DataFrame conversions. First run creates cache, subsequent runs use cache for faster processing.
- Use `--skip-steps` to skip already completed steps (if implemented)
- Reduce H3 resolution for faster processing
- Process smaller areas (use coordinates with smaller radius)
- Check if cache is being used: Look for "Using cached..." messages in the output

### Memory issues or crashes

**Problem**: Application crashes or runs out of memory, especially with large datasets (100km+ radius).

**Solution**:
- **Memory optimization is built-in**: The pipeline automatically optimizes memory usage by deferring H3 boundary generation until after merge and aggregation. This reduces memory usage by ~99% for large datasets.
- **How it works**: Boundaries are not generated during H3 indexing or merging. They are only generated after data is aggregated by hexagon (e.g., 5,817 hexagons instead of 521,217 points).
- **If you still experience memory issues**:
  - Process smaller areas (reduce radius)
  - Reduce H3 resolution (coarser hexagons = fewer hexagons)
  - Ensure you're using the latest version with memory optimizations
  - Check available system memory (recommended: 4GB+ free RAM for 100km radius)

### Cache not working

**Problem**: Cache is not being used or cache errors occur.

**Solution**:
- **Cache is enabled by default**: Caching works automatically and requires no configuration
- **First run**: Cache is created during normal processing (this is expected)
- **Subsequent runs**: Cache is automatically used if valid (same inputs and parameters)
- **Cache validation**: Cache automatically invalidates when source files change (checks modification times)
- **Automatic cleanup**: Old coordinate-specific caches are automatically cleaned up on each run
  - Protected caches: Full state cache (no coordinates), protected coordinates (-13, -56, 100km), and current coordinates (same lat/lon/radius as current run)
  - If you see "Cleaned up X old coordinate-specific cache(s)" message, this is normal behavior
  - Only old coordinate-specific caches (clipped_rasters) that don't match the above are removed
  - Can be disabled by setting `processing.cleanup_old_cache: false` in config
- **Clear cache**: If you suspect cache issues, delete `data/processed/cache/` directory to force regeneration:
  ```bash
  # Windows
  rmdir /s /q data\processed\cache
  
  # Linux/Mac
  rm -rf data/processed/cache
  ```
- **Parquet errors**: Ensure `pyarrow>=10.0.0` is installed: `pip install pyarrow>=10.0.0`
- **Check cache directory**: Verify `data/processed/cache/` exists and contains cache subdirectories
- **Cache size**: Cache typically uses 10-100 MB depending on area size and number of datasets

### Large map files (>100MB)

**Problem**: HTML map files are too large.

**Solution**:
- The code automatically switches to PyDeck for large files
- Reduce H3 resolution to create smaller hexagons
- Process smaller areas
- Use lower resolution GeoTIFF files

## Visualization Issues

### Map not opening in browser

**Problem**: Auto-open fails or map doesn't display correctly.

**Solution**:
- Manually open the HTML file: `output/html/biochar_suitability_map.html`, `output/html/suitability_map.html`, or `output/html/soc_map.html`
- Check browser console for JavaScript errors
- Try a different browser
- Disable auto-open in config and open manually
- Confirm that the HTML file is under 100 MB; larger files can take a while to open on slower machines
- Both suitability and SOC maps should auto-open after pipeline completion if `auto_open_html: true` in config

### Map shows no data

**Problem**: Map is empty or shows only background.

**Solution**:
- Check that `merged_soil_data.csv` exists and has data
- Verify the file has `lon`, `lat`, and required property columns (moisture, SOC, pH, temperature)
- Check that biochar suitability scores are in valid range (0-100 in main map, 0-10 in Streamlit CSV)
- Review the data in `data/processed/merged_soil_data.csv` or `data/processed/suitability_scores.csv`
- Ensure the H3 resolution you selected matches what the visualisation expects (defaults to 7)
- For Streamlit: Verify that `suitability_scores.csv` exists with `suitability_score` column (0-10 scale)

**Note**: 
- **Suitability Map**: When using H3 hexagons, clicking or hovering over a hexagon displays a tooltip with the biochar suitability score, suitability grade, H3 index, location coordinates, and point count.
- **SOC Map**: Tooltip displays SOC value (g/kg), H3 index, location coordinates, and point count.
- **pH Map**: Tooltip displays pH value, H3 index, location coordinates, and point count.

### Streamlit: Results not displayed

**Problem**: Analysis completes successfully but maps and results are not shown in Streamlit.

**Solution**:
- Verify that `data/processed/suitability_scores.csv` exists and contains the `suitability_score` column
- Check that `output/html/suitability_map.html` exists (this is the Streamlit-compatible suitability map file)
- Ensure scores are in 0-10 range (the CSV file should have scores scaled from 0-100 to 0-10)
- Check the Streamlit console/logs for any file path errors
- Verify the config paths match: `config["data"]["processed"]` and `config["output"]["html"]`
- The program automatically generates all map files during analysis - if they're missing, re-run the analysis
- **SOC Map**: The SOC map is pre-generated during analysis. If it fails to display:
  - Verify that `data/processed/merged_soil_data.csv` exists and contains SOC columns (`SOC_res_250_b0 (g/kg)` and `SOC_res_250_b10 (g/kg)`)
  - Check that `output/html/soc_map_streamlit.html` exists
  - Check Streamlit error messages in the tab
  - Ensure the analysis completed successfully before opening the SOC tab
- **pH Map**: The pH map is pre-generated during analysis. If it fails to display:
  - Verify that `data/processed/merged_soil_data.csv` exists and contains pH columns (`soil_pH_res_250_b0` and `soil_pH_res_250_b10`)
  - Check that `output/html/ph_map_streamlit.html` exists
  - Check Streamlit error messages in the tab
  - Ensure the analysis completed successfully before opening the pH tab

### pH Map colors too dark or too red

**Problem**: pH map shows colors that are too dark red for acidic soils, making it hard to distinguish from neutral/alkaline areas.

**Solution**:
- This issue was fixed by updating the color scheme in `src/visualization/ph_map.py`
- The pH map now uses lighter, more yellow-tinted colors for acidic soils:
  - Acidic soils (<5.5): Light orange-yellow (255, 140-200, 0) instead of dark red
  - Neutral (~7): Yellow (255, 255, 0)
  - Alkaline (>7.5): Blue (173-49, 216-54, 230-149)
- If you're seeing old dark red colors, ensure you have the latest version of the code
- The color scheme uses a diverging scale that transitions smoothly from acidic (light orange-yellow) through neutral (yellow) to alkaline (blue)
- Regenerate the pH map by re-running the analysis to see the updated colors

### PYTHONPATH / import issues outside PyCharm

**Problem**: Running scripts from PowerShell or Command Prompt raises `ModuleNotFoundError: No module named 'src...'`.

**Solution**:
- Add the project root to your user-level `PYTHONPATH` environment variable via System Properties → Environment Variables.
- Alternatively, in PowerShell run:
  ```powershell
  [Environment]::SetEnvironmentVariable(
      "PYTHONPATH",
      "C:\Users\lilou\PycharmProjects\PythonProject\Residual_Carbon",
      "User"
  )
  ```
- Restart the shell so the new variable is picked up.

### Map generation issues

**Problem**: Maps fail to generate or show incorrect data.

**Solution**:
- **All maps are generated during analysis**: The pipeline automatically generates suitability, SOC, and pH maps during the analysis step. They are not generated on-demand in Streamlit.
- **Check map files exist**: Verify that map HTML files exist in `output/html/`:
  - `suitability_map.html` and `biochar_suitability_map.html` (suitability map)
  - `soc_map.html` and `soc_map_streamlit.html` (SOC map)
  - `ph_map.html` and `ph_map_streamlit.html` (pH map)
- **Missing pH or SOC maps**: If pH or SOC maps are missing:
  - Ensure the analysis completed successfully (check for errors in the console)
  - Verify that `data/processed/merged_soil_data.csv` contains the required columns:
    - For SOC: `SOC_res_250_b0 (g/kg)` and `SOC_res_250_b10 (g/kg)`
    - For pH: `soil_pH_res_250_b0` and `soil_pH_res_250_b10`
  - Check that both b0 and b10 layers are present in `data/raw/` for SOC and pH datasets
  - Re-run the analysis if maps are missing
- **Map colors incorrect**: If map colors don't match expectations:
  - For pH map: Ensure you have the latest version with updated color scheme (lighter, more yellow-tinted for acidic soils)
  - Regenerate maps by re-running the analysis
- **Streamlit map display issues**: If maps don't display in Streamlit:
  - Check that Streamlit-compatible versions exist (`*_streamlit.html` files)
  - Verify file paths in config match actual file locations
  - Check Streamlit console for JavaScript errors
  - Try refreshing the Streamlit page

## Getting Help

If you encounter issues not covered here:

1. Check the log file: `logs/residual_carbon.log` (if logging is enabled)
2. Run with `--verbose` flag for detailed output
3. Check the progress file: `.progress.json` to see which steps completed
4. Review error messages and stack traces for specific error details
5. Use the verification helpers to isolate whether the issue lies in clipping, table conversion, or scoring
6. Verify that all required map files are generated during analysis (suitability, SOC, and pH maps)

