# Residual_Carbon - Biochar Suitability Mapping Tool

A tool for mapping biochar application suitability in Mato Grosso, Brazil, based on soil properties and biochar outputs.

## Project Overview

This tool analyzes soil properties (moisture, type, temperature, organic carbon, pH, and land cover) from Google Earth Engine to calculate suitability scores for biochar application across Mato Grosso state. The tool generates interactive maps with color-coded suitability scores (0-10 scale) where green indicates high suitability and red indicates low suitability.

## Features

- **Automated Data Retrieval**: Retrieves soil property datasets from Google Earth Engine
- **Spatial Analysis**: Supports analysis of entire Mato Grosso state or user-specified 100km radius circles with intelligent edge handling when the circle falls near state boundaries
- **GeoTIFF Processing**: Exports data to GeoTIFF format with automated download from Google Drive
- **H3 Hexagonal Grid**: Converts spatial data to H3 hexagonal grid for efficient spatial indexing
- **Suitability Scoring**: Calculates suitability scores (0-10) based on soil property thresholds
- **Interactive Maps**: Generates color-coded HTML maps with automatic browser opening
- **Automated Workflow**: End-to-end pipeline from data retrieval to visualization

## Installation

### Prerequisites

- Python 3.9 or higher
- Google Earth Engine account
- Google Cloud Project with Drive API enabled
- Git (optional)

### Step 1: Clone or Navigate to Project

```bash
cd Residual_Carbon
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

**Option A: Using pip (Linux/Mac)**

```bash
pip install -r requirements.txt
```

**Option B: Using Conda (Recommended for Windows)**

```bash
# Install geospatial packages via Conda
conda install -c conda-forge geopandas rasterio shapely fiona pyproj gdal

# Then install remaining packages via pip
pip install -r requirements.txt
```

### Step 4: Google Earth Engine Setup

1. **Authenticate with Google Earth Engine:**
   ```bash
   python -c "import ee; ee.Authenticate()"
   ```

2. **Set your GEE project name** in `configs/config.yaml`:
   ```yaml
   gee:
     project_name: "your-project-name"
   ```

### Step 5: Google Drive API Setup (for Automated Download)

1. **Enable Google Drive API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)

2. **Download credentials:**
   - Download `client_secrets.json` from Google Cloud Console
   - Place it in `configs/client_secrets.json`

3. **First-time authentication:**
   - The first time you run the tool, it will open a browser for OAuth authentication
   - A `credentials.json` file will be created automatically in `configs/`

## Configuration

Edit `configs/config.yaml` to customize:

- Google Earth Engine project name
- Export resolution (default: 1000m)
- H3 resolution (default: 6)
- Output directories
- Suitability scoring parameters

## Usage

### 1. Acquire GeoTIFFs from Google Earth Engine

Run the acquisition script to create Drive export tasks. It prompts for how many datasets to export, shows a detailed summary (dataset, depth band, filename, resolution, folder), reminds you which files will be generated, and then asks whether to start the tasks.

```bash
python src/data/acquisition/gee_loader.py
```

- Use `--layers soil_pH,soil_organic_carbon` to target specific datasets.
- Add `--start-tasks` to skip the confirmation prompt and immediately launch the Drive exports.
- OpenLandMap layers (`soil_pH`, `soil_organic_carbon`, `soil_type`) are exported one GeoTIFF per depth band (`b0`, `b10`, `b30`, `b60`).

After the Drive tasks complete (and downloads finish, if you use the automated downloader), the GeoTIFFs will be in `data/raw/`.

### 2. Process and Map (Full State Analysis)

```bash
python src/main.py
```
Running without `--lat`/`--lon` launches an interactive prompt that lets you decide whether to keep the full state or supply coordinates on the fly.

### With User Coordinates (100km Radius)

```bash
python src/main.py --lat -15.5 --lon -56.0 --radius 100
```

### CLI Options

```bash
python src/main.py --help
```
Key options:

- `--lat / --lon / --radius`: Provide coordinates programmatically (skips prompts)
- `--h3-resolution`: Control the aggregation resolution (default 7)
- `--config`: Point to an alternate configuration file

## Project Structure

```
Residual_Carbon/
├── src/
│   ├── data/           # Data retrieval and processing
│   ├── analysis/       # Suitability scoring
│   ├── visualization/  # Map generation
│   └── utils/          # Utility functions
├── configs/            # Configuration files
├── data/
│   ├── raw/            # GeoTIFF files from GEE
│   └── processed/      # Processed CSV and H3 data
├── output/
│   ├── maps/           # Generated maps
│   └── html/           # HTML map files
├── logs/               # Application logs
├── requirements.txt    # Python dependencies
├── config.yaml         # Main configuration
└── README.md           # This file
```

## Workflow

1. **Data Retrieval**: Retrieve soil property datasets from Google Earth Engine
2. **Task Review**: Confirm export summary and start Drive tasks from the CLI
3. **Download**: Automatically download GeoTIFF files from Google Drive
4. **User Input**: Optionally specify coordinates for a 100km radius analysis (prompted if not supplied)
5. **Radius Clipping**: Clip GeoTIFFs to user-specified circles (if provided); verification tolerates partial coverage when circles touch the border
6. **CSV Conversion**: Convert clipped rasters to CSV format
7. **H3 Indexing**: Convert coordinates to H3 hexagonal grid
8. **Scoring**: Calculate suitability scores (0-10) by aggregating and averaging within H3 hexagons
9. **Visualization**: Generate interactive HTML map using PyDeck with Capstone-inspired styling
10. **Auto-Open**: Automatically open the final map in the default browser

## Data Sources

- **Soil Moisture**: NASA SMAP (NASA/SMAP/SPL4SMGP/008)
- **Soil Type**: OpenLandMap (OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02)
- **Soil Temperature**: NASA SMAP (NASA/SMAP/SPL4SMGP/008)
- **Soil Organic Carbon**: OpenLandMap (OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02)
- **Soil pH**: OpenLandMap (OpenLandMap/SOL/SOL_PH-H2O_USDA-4C1A2A_M/v02)
- **Land Cover**: ESA WorldCover (ESA/WorldCover/v100)

## Output

The tool generates:

- **GeoTIFF files**: Raw raster data in `data/raw/`
- **CSV files**: Processed point data in `data/processed/`
- **HTML map**: Interactive suitability map in `output/html/`
- **Logs**: Application logs in `logs/`

## Troubleshooting

### Google Earth Engine Authentication Issues

```bash
# Re-authenticate
python -c "import ee; ee.Authenticate()"
```

### Google Drive API Issues

- Ensure `client_secrets.json` is in `configs/` directory
- Check that Google Drive API is enabled in Google Cloud Console
- Delete `configs/credentials.json` and re-authenticate if needed

### GeoTIFF Export Issues

- Check export task status in Google Earth Engine Code Editor
- Verify you have sufficient Google Drive storage
- Ensure export folder name matches in `config.yaml`

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Contact

[Add contact information here]

