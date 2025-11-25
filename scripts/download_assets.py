#!/usr/bin/env python
"""
Download required GeoTIFF and shapefile assets from Google Drive.

The Google Drive folder is FLAT (all files in one folder).
This script finds files by filename and organizes them into the local directory structure.

Usage:
    python scripts/download_assets.py

Optional flags:
    --force    Re-download and overwrite existing files.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import gdown
except ImportError as exc:  # pragma: no cover - handled during runtime
    raise SystemExit(
        "gdown is required. Install dependencies via `pip install -r requirements.txt`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOOGLE_DRIVE_FOLDER_ID = "1FvG4FM__Eam2pXggHdo5piV7gg2bljjt"
GOOGLE_DRIVE_URL = f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"

REQUIRED_FILES = [
    # All files go directly into data/ to match flat Google Drive structure
    {"filename": "BR_Municipios_2024.shp", "target": "data/BR_Municipios_2024.shp"},
    {"filename": "BR_Municipios_2024.dbf", "target": "data/BR_Municipios_2024.dbf"},
    {"filename": "BR_Municipios_2024.shx", "target": "data/BR_Municipios_2024.shx"},
    {"filename": "BR_Municipios_2024.prj", "target": "data/BR_Municipios_2024.prj"},
    {"filename": "BR_Municipios_2024.cpg", "target": "data/BR_Municipios_2024.cpg"},
    {"filename": "Updated_municipality_crop_production_data.csv", "target": "data/Updated_municipality_crop_production_data.csv"},
    {"filename": "SOC_res_250_b0.tif", "target": "data/SOC_res_250_b0.tif"},
    {"filename": "SOC_res_250_b10.tif", "target": "data/SOC_res_250_b10.tif"},
    {"filename": "soil_moisture_res_250_sm_surface.tif", "target": "data/soil_moisture_res_250_sm_surface.tif"},
    {"filename": "soil_pH_res_250_b0.tif", "target": "data/soil_pH_res_250_b0.tif"},
    {"filename": "soil_pH_res_250_b10.tif", "target": "data/soil_pH_res_250_b10.tif"},
    {"filename": "soil_temp_res_250_soil_temp_layer1.tif", "target": "data/soil_temp_res_250_soil_temp_layer1.tif"},
    {"filename": "residue_ratios.csv", "target": "data/residue_ratios.csv"},
    {"filename": "brazil_crop_harvest_area_2017-2024.csv", "target": "data/brazil_crop_harvest_area_2017-2024.csv"},
]


def _download_drive_folder(tmp_dir: Path) -> Path:
    """Download the shared Drive folder into a temp directory and return its root."""
    output_dir = tmp_dir / "drive_download"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        gdown.download_folder(
            id=GOOGLE_DRIVE_FOLDER_ID,
            output=str(output_dir),
            quiet=False,
            use_cookies=False,
            remaining_ok=True,
        )
    except Exception as e:
        error_msg = str(e).lower()
        print(f"[ERROR] Failed to download folder: {e}", file=sys.stderr, flush=True)
        
        # Detect common Google Drive blocking/rate limiting issues
        if any(keyword in error_msg for keyword in ["403", "forbidden", "rate limit", "quota", "blocked", "access denied"]):
            print("\n[WARNING] Google Drive access may be blocked or rate-limited.", file=sys.stderr, flush=True)
            print("[WARNING] This is common on Streamlit Cloud due to network restrictions.", file=sys.stderr, flush=True)
            print("[WARNING] Consider using alternative hosting or manual file placement.", file=sys.stderr, flush=True)
        
        raise
    
    # gdown may create a subdirectory with the folder name, or put files directly in output_dir
    # Check for subdirectories first
    subdirs = [p for p in output_dir.iterdir() if p.is_dir()]
    if len(subdirs) == 1:
        folder_root = subdirs[0]
        print(f"[INFO] Files downloaded to subdirectory: {folder_root}")
        return folder_root
    
    # If no subdir, files might be directly in output_dir
    files = [p for p in output_dir.iterdir() if p.is_file()]
    if files:
        print(f"[INFO] Files downloaded directly to: {output_dir} ({len(files)} files found)")
        return output_dir
    
    # Last resort: search recursively for any files
    all_files = list(output_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]
    if files_only:
        print(f"[INFO] Found {len(files_only)} files recursively in {output_dir}")
        return output_dir
    
    raise FileNotFoundError(f"No files found in downloaded folder: {output_dir}")


def _locate_source_file(source_root: Path, filename: str) -> Path | None:
    """Find a file in the flat Google Drive folder by filename (case-insensitive search).
    
    The Google Drive folder is flat (all files in one folder), so we search by filename only.
    """
    # Try exact match first
    matches = list(source_root.rglob(filename))
    if not matches:
        # Try case-insensitive match
        filename_lower = filename.lower()
        for file_path in source_root.rglob("*"):
            if file_path.is_file() and file_path.name.lower() == filename_lower:
                matches.append(file_path)
    
    if not matches:
        return None
    
    # Prefer the shallowest match (in case of duplicates)
    return sorted(matches, key=lambda p: len(p.parts))[0]


def _copy_required_assets(source_root: Path, force: bool) -> tuple[list[Path], list[Path]]:
    """Copy required assets from flat Google Drive folder to flat local data/ directory.
    
    Both source (Google Drive) and destination (local) are flat - all files in data/.
    Maps each filename from the flat Drive folder to data/.
    Only data/processed/ is kept separate for pipeline outputs.
    
    Returns:
        Tuple of (copied_files, missing_files)
    """
    missing_sources = []
    copied_files = []
    
    print(f"[INFO] Searching for files in: {source_root}")
    all_items = list(source_root.rglob("*"))
    files_only = [f for f in all_items if f.is_file()]
    print(f"[INFO] Found {len(files_only)} files in downloaded folder")
    
    # List all available files for debugging
    if files_only:
        print(f"[DEBUG] Available files: {', '.join(f.name for f in files_only[:10])}")
        if len(files_only) > 10:
            print(f"[DEBUG] ... and {len(files_only) - 10} more files")
    
    for file_spec in REQUIRED_FILES:
        rel_target = Path(file_spec["target"])
        dest = PROJECT_ROOT / rel_target
        src = _locate_source_file(source_root, file_spec["filename"])

        if src is None:
            print(f"[ERROR] File not found in Drive: {file_spec['filename']}", file=sys.stderr)
            print(f"[DEBUG] Searched in: {source_root}", file=sys.stderr)
            missing_sources.append(rel_target)
            continue

        if dest.exists() and not force:
            print(f"[SKIP] Already exists: {rel_target}")
            copied_files.append(rel_target)  # Count as success even if skipped
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dest)
            # Verify the copy was successful
            if not dest.exists():
                raise FileNotFoundError(f"File was not created at {dest}")
            file_size = dest.stat().st_size
            if file_size == 0:
                raise ValueError(f"Copied file is empty: {dest}")
            print(f"[OK] Copied {rel_target} ({file_size / (1024*1024):.1f} MB)", flush=True)
            copied_files.append(rel_target)
        except Exception as e:
            print(f"[ERROR] Failed to copy {rel_target}: {e}", file=sys.stderr, flush=True)
            missing_sources.append(rel_target)

    return copied_files, missing_sources


def download_assets(force: bool = False) -> int:
    """Download assets if any required file is missing."""
    print(f"[INFO] PROJECT_ROOT: {PROJECT_ROOT}", flush=True)
    print(f"[INFO] Checking for existing files...", flush=True)
    
    existing = [
        PROJECT_ROOT / file_spec["target"]
        for file_spec in REQUIRED_FILES
        if (PROJECT_ROOT / file_spec["target"]).exists()
    ]
    print(f"[INFO] Found {len(existing)}/{len(REQUIRED_FILES)} existing files", flush=True)
    
    if len(existing) == len(REQUIRED_FILES) and not force:
        print("All required data files are already present. Nothing to do.", flush=True)
        return 0

    print(f"Downloading assets from {GOOGLE_DRIVE_URL} ...", flush=True)
    print(f"Looking for {len(REQUIRED_FILES)} required files...", flush=True)
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"[INFO] Using temp directory: {tmp_dir}", flush=True)
            drive_root = _download_drive_folder(Path(tmp_dir))
            print(f"[INFO] Drive folder downloaded to: {drive_root}", flush=True)
            copied, missing = _copy_required_assets(drive_root, force=force)
            
            # Verify files were actually copied
            print(f"[INFO] Verification: Copied {len(copied)}, Missing {len(missing)}", flush=True)
            verified_missing = []
            for file_spec in REQUIRED_FILES:
                dest = PROJECT_ROOT / file_spec["target"]
                if not dest.exists():
                    verified_missing.append(dest)
                    print(f"[ERROR] File not found after copy: {dest}", file=sys.stderr, flush=True)
                elif dest.exists() and dest.stat().st_size == 0:
                    verified_missing.append(dest)
                    print(f"[ERROR] File exists but is empty: {dest}", file=sys.stderr, flush=True)
                else:
                    print(f"[VERIFY] File OK: {dest} ({dest.stat().st_size} bytes)", flush=True)
            
            if verified_missing:
                print(f"\n[ERROR] {len(verified_missing)} files are still missing or empty after copy:", file=sys.stderr, flush=True)
                for m in verified_missing:
                    print(f"  - {m}", file=sys.stderr, flush=True)
                print(f"\n[DEBUG] PROJECT_ROOT: {PROJECT_ROOT}", file=sys.stderr, flush=True)
                print(f"[DEBUG] PROJECT_ROOT exists: {PROJECT_ROOT.exists()}", file=sys.stderr, flush=True)
                return 1
            
            if missing:
                print(f"\n[ERROR] {len(missing)} files could not be found in Drive:", file=sys.stderr, flush=True)
                for m in missing:
                    print(f"  - {m}", file=sys.stderr, flush=True)
                return 1
            
            if copied:
                print(f"\n[SUCCESS] Downloaded {len(copied)} files successfully.", flush=True)
            else:
                print("\n[INFO] No new files downloaded (all already exist).", flush=True)
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

    print("Data download complete.", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Download project data assets from Google Drive.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite existing files.",
    )
    args = parser.parse_args()
    return download_assets(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())

