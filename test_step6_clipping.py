"""Test Step 6: Radius Clipping functionality with existing GeoTIFF files."""

from pathlib import Path
from src.utils.geospatial import create_circle_buffer
from src.data.raster_clip import clip_all_rasters_to_circle, verify_clipping_success

# Center of Mato Grosso (from bounds: min_lat=-18.0, max_lat=-7.0, min_lon=-65.0, max_lon=-50.0)
center_lat = -12.5
center_lon = -57.5
radius_km = 100.0

# Get project root
project_root = Path(__file__).parent
raw_dir = project_root / "data" / "raw"
processed_dir = project_root / "data" / "processed"

# Ensure directories exist
raw_dir.mkdir(parents=True, exist_ok=True)
processed_dir.mkdir(parents=True, exist_ok=True)

print("""============================================================
Testing Step 6: Radius Clipping
============================================================

Test Configuration:
  Center: ({}, {})
  Radius: {} km
  Input directory: {}
  Output directory: {}
""".format(center_lat, center_lon, radius_km, raw_dir, processed_dir))

# Check if input files exist
tif_files = list(raw_dir.glob("*.tif"))
if not tif_files:
    print("ERROR: No GeoTIFF files found in {}".format(raw_dir))
    exit(1)

print("Found {} GeoTIFF file(s) in {}".format(len(tif_files), raw_dir))
for tif_file in tif_files:
    print("  - {}".format(tif_file.name))

# Create circle buffer
print("""
------------------------------------------------------------
Creating circle buffer...
------------------------------------------------------------""")
try:
    circle = create_circle_buffer(lat=center_lat, lon=center_lon, radius_km=radius_km)
    print("Circle buffer created successfully")
    print("  Bounds: {}".format(circle.bounds))
except Exception as e:
    print("ERROR: Failed to create circle buffer: {}".format(e))
    exit(1)

# Clip all rasters
print("""
------------------------------------------------------------
Clipping GeoTIFF files...
------------------------------------------------------------""")
try:
    clipped_files = clip_all_rasters_to_circle(
        input_dir=raw_dir,
        output_dir=processed_dir,
        circle_geometry=circle
    )
    
    if not clipped_files:
        print("ERROR: No files were clipped")
        exit(1)
    
    # Verify clipping success
    print("""
------------------------------------------------------------
Verifying clipped files...
------------------------------------------------------------""")
    if verify_clipping_success(clipped_files):
        print("SUCCESS: All clipped files are valid")
        print("""
Clipped files:""")
        for clipped_file in clipped_files:
            file_size = clipped_file.stat().st_size / (1024 * 1024)  # MB
            print("  - {} ({:.2f} MB)".format(clipped_file.name, file_size))
    else:
        print("WARNING: Some clipped files may be invalid")
        exit(1)
    
except Exception as e:
    print("ERROR: Failed to clip rasters: {}".format(e))
    import traceback
    traceback.print_exc()
    exit(1)

print("""
============================================================
Step 6 Test: PASSED
============================================================
Successfully clipped {} file(s) to {}km radius circle
centered at ({}, {})
Files saved to: {}
============================================================
""".format(len(clipped_files), radius_km, center_lat, center_lon, processed_dir))

