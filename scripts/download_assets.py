#!/usr/bin/env python
"""
Download required GeoTIFF and shapefile assets from Cloudflare R2 (primary) or Google Drive (fallback).

Usage:
    python scripts/download_assets.py

Optional flags:
    --force         Re-download and overwrite existing files.
    --source r2     Use Cloudflare R2 (default, recommended)
    --source gdrive Use Google Drive (fallback, may be rate-limited)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cloudflare R2 (primary source - fast and reliable)
R2_BASE_URL = "https://pub-d86172a936014bdc9e794890543c5f66.r2.dev"

# Google Drive (fallback)
GOOGLE_DRIVE_FOLDER_ID = "1FvG4FM__Eam2pXggHdo5piV7gg2bljjt"
GOOGLE_DRIVE_URL = f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"

# Only file that needs R2 download (others are in GitHub repo)
REQUIRED_FILES = [
    "soil_moisture_res_250_sm_surface.tif",
]


def download_from_r2(force: bool = False) -> int:
    """Download assets from Cloudflare R2 (fast and reliable)."""
    if requests is None:
        print("[ERROR] requests library not installed. Run: pip install requests", file=sys.stderr)
        return 1
    
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    skipped = []
    errors = []
    
    print(f"[INFO] Downloading from Cloudflare R2: {R2_BASE_URL}", flush=True)
    print(f"[INFO] Target directory: {data_dir}", flush=True)
    
    for filename in REQUIRED_FILES:
        dest = data_dir / filename
        
        if dest.exists() and dest.stat().st_size > 0 and not force:
            print(f"[SKIP] Already exists: {filename}")
            skipped.append(filename)
            continue
        
        url = f"{R2_BASE_URL}/{filename}"
        try:
            print(f"[DOWNLOAD] {filename}...", end=" ", flush=True)
            response = requests.get(url, timeout=300, stream=True)
            response.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"OK ({size_mb:.1f} MB)")
            downloaded.append(filename)
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(filename)
    
    print(f"\n[SUMMARY] Downloaded: {len(downloaded)}, Skipped: {len(skipped)}, Errors: {len(errors)}")
    
    if errors:
        print(f"[ERROR] Failed to download: {', '.join(errors)}", file=sys.stderr)
        return 1
    
    print("[SUCCESS] All files ready.", flush=True)
    return 0


def download_from_gdrive(force: bool = False) -> int:
    """Fallback: Download from Google Drive using gdown."""
    try:
        import gdown
        import shutil
        import tempfile
    except ImportError:
        print("[ERROR] gdown not installed. Use: pip install gdown", file=sys.stderr)
        return 1
    
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Downloading from Google Drive: {GOOGLE_DRIVE_URL}", flush=True)
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "drive_download"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            gdown.download_folder(
                id=GOOGLE_DRIVE_FOLDER_ID,
                output=str(output_dir),
                quiet=False,
                use_cookies=False,
                remaining_ok=True,
            )
            
            # Find downloaded files
            all_files = list(output_dir.rglob("*"))
            files_only = {f.name: f for f in all_files if f.is_file()}
            
            for filename in REQUIRED_FILES:
                dest = data_dir / filename
                if dest.exists() and not force:
                    continue
                
                # Case-insensitive search
                src = files_only.get(filename)
                if not src:
                    for name, path in files_only.items():
                        if name.lower() == filename.lower():
                            src = path
                            break
                
                if src:
                    shutil.copy2(src, dest)
                    print(f"[OK] Copied {filename}")
                else:
                    print(f"[ERROR] Not found: {filename}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Google Drive download failed: {e}", file=sys.stderr)
        return 1
    
    return 0


def download_assets(force: bool = False, source: str = "r2") -> int:
    """Download assets from specified source."""
    print(f"[INFO] PROJECT_ROOT: {PROJECT_ROOT}", flush=True)
    
    # Check existing files
    data_dir = PROJECT_ROOT / "data"
    existing = [f for f in REQUIRED_FILES if (data_dir / f).exists()]
    print(f"[INFO] Found {len(existing)}/{len(REQUIRED_FILES)} existing files", flush=True)
    
    if len(existing) == len(REQUIRED_FILES) and not force:
        print("All required data files are already present. Nothing to do.", flush=True)
        return 0
    
    if source == "r2":
        return download_from_r2(force=force)
    elif source == "gdrive":
        return download_from_gdrive(force=force)
    else:
        print(f"[ERROR] Unknown source: {source}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download project data assets from Cloudflare R2 or Google Drive."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite existing files.",
    )
    parser.add_argument(
        "--source",
        choices=["r2", "gdrive"],
        default="r2",
        help="Download source: r2 (default, recommended) or gdrive (fallback).",
    )
    args = parser.parse_args()
    return download_assets(force=args.force, source=args.source)


if __name__ == "__main__":
    raise SystemExit(main())

