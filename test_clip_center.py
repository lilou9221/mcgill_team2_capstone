"""Test script to clip a GeoTIFF to a circle centered at Mato Grosso center."""

from pathlib import Path
from src.utils.geospatial import create_circle_buffer
from src.data.raster_clip import clip_raster_to_circle

# Mato Grosso bounds (from coordinate_validator.py)
# min_lat: -18.0, max_lat: -7.0 -> center: (-18.0 + -7.0) / 2 = -12.5
# min_lon: -65.0, max_lon: -50.0 -> center: (-65.0 + -50.0) / 2 = -57.5
center_lat = -12.5
center_lon = -57.5
radius_km = 100.0  # 100km radius for testing

# Get project root
project_root = Path(__file__).parent
raw_dir = project_root / "data" / "raw"
processed_dir = project_root / "data" / "processed"

# Ensure processed directory exists
processed_dir.mkdir(parents=True, exist_ok=True)

# Find a GeoTIFF file to clip (use the first one found)
tif_files = list(raw_dir.glob("*.tif"))
if not tif_files:
    print("No GeoTIFF files found in data/raw/")
    exit(1)

# Use the first file
input_file = tif_files[0]
output_file = processed_dir / f"test_clip_{input_file.stem}.tif"

print(f"""Creating test clip:
  Input: {input_file.name}
  Center: ({center_lat}, {center_lon})
  Radius: {radius_km} km
  Output: {output_file.name}""")

# Create circle buffer
print("\nCreating circle buffer...")
circle = create_circle_buffer(lat=center_lat, lon=center_lon, radius_km=radius_km)
print(f"Circle buffer created: {circle.bounds}")

# Clip the raster
print(f"\nClipping {input_file.name}...")
try:
    clipped_path = clip_raster_to_circle(
        tif_path=input_file,
        circle_geometry=circle,
        output_path=output_file
    )
    print(f"""Successfully created test clip:
  Output file: {clipped_path}
  File size: {clipped_path.stat().st_size / (1024 * 1024):.2f} MB""")
except Exception as e:
    print(f"Error clipping raster: {type(e).__name__}: {e}")
    exit(1)

print("\nTest clip completed successfully!")
print(f"File saved to: {output_file}")

