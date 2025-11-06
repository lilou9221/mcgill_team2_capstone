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

**Problem**: Cannot write to CSV files during H3 conversion or suitability scoring.

**Solution**:
- Close any programs that might have the CSV files open (Excel, text editors, etc.)
- Check file permissions on the `data/processed/` directory
- Run the script with appropriate permissions

### TypeError: Could not convert string to numeric

**Problem**: Non-numeric columns (like color codes) are being included in aggregation.

**Solution**:
- This has been fixed in the latest version - the code now filters to only numeric columns
- If you still see this error, check your CSV files for unexpected string columns
- Ensure CSV files only contain numeric data for soil properties

### ModuleNotFoundError

**Problem**: Missing Python packages.

**Solution**:
```bash
pip install -e .
```

Or install specific packages:
```bash
pip install earthengine-api rasterio pandas h3 folium pydeck shapely pyyaml
```

### Config file not found

**Problem**: Configuration file cannot be loaded.

**Solution**:
- Ensure `configs/config.yaml` exists
- Run the script from the project root directory
- Use `--config` flag to specify a custom config path

## Data Issues

### No GeoTIFF files found

**Problem**: `data/raw/` directory is empty or files are missing.

**Solution**:
1. Run the data loader first: `python src/data_loader.py`
2. Export data from Google Earth Engine to Google Drive
3. Manually download GeoTIFF files to `data/raw/`

### CSV files are empty

**Problem**: Converted CSV files have no data.

**Solution**:
- Check that GeoTIFF files are valid and not corrupted
- Verify the clipping area intersects with the data
- Check for NoData values in the GeoTIFF files

### Suitability scores are all zero

**Problem**: All suitability scores are 0.0.

**Solution**:
- Check that thresholds file exists: `configs/thresholds.yaml`
- Verify CSV files contain the required soil property columns
- Check that property values are within expected ranges
- Review threshold values in `configs/thresholds.yaml`

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

## Performance Issues

### Slow processing

**Problem**: Steps take a long time to complete.

**Solution**:
- Use `--skip-steps` to skip already completed steps
- Use `--resume` to continue from last successful step
- Reduce H3 resolution for faster processing
- Process smaller areas (use coordinates with smaller radius)

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
- Manually open the HTML file: `output/html/suitability_map.html`
- Check browser console for JavaScript errors
- Try a different browser
- Disable auto-open in config and open manually

### Map shows no data

**Problem**: Map is empty or shows only background.

**Solution**:
- Check that `suitability_scores.csv` exists and has data
- Verify the file has `lon`, `lat`, and `suitability_score` columns
- Check that scores are in valid range (0-10)
- Review the data in `data/processed/suitability_scores.csv`

## Getting Help

If you encounter issues not covered here:

1. Check the log file: `logs/residual_carbon.log` (if logging is enabled)
2. Run with `--verbose` flag for detailed output
3. Check the progress file: `.progress.json` to see which steps completed
4. Review error messages and stack traces for specific error details

