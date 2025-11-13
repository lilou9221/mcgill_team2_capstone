"""
Cache Utility Module

Provides caching functionality for clipped rasters and other expensive operations.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def generate_cache_key(lat: float, lon: float, radius_km: float, source_files: List[Path]) -> str:
    """
    Generate a cache key based on coordinates, radius, and source file metadata.
    
    Parameters
    ----------
    lat : float
        Latitude of the center point
    lon : float
        Longitude of the center point
    radius_km : float
        Radius in kilometers
    source_files : List[Path]
        List of source GeoTIFF files
    
    Returns
    -------
    str
        Cache key (hexadecimal hash)
    """
    # Normalize coordinates to fixed precision for consistent hashing
    lat_rounded = round(lat, 6)
    lon_rounded = round(lon, 6)
    radius_rounded = round(radius_km, 2)
    
    # Create hash components: coordinates, radius, and source file info
    hash_components = [
        f"lat_{lat_rounded}",
        f"lon_{lon_rounded}",
        f"radius_{radius_rounded}",
    ]
    
    # Add source file info (name and modification time)
    # Sort files for consistent hashing
    sorted_files = sorted(source_files, key=lambda p: p.name)
    for file_path in sorted_files:
        if file_path.exists():
            # Use filename and modification time
            mtime = file_path.stat().st_mtime
            file_info = f"{file_path.name}_{mtime}"
            hash_components.append(file_info)
    
    # Create hash from all components
    hash_string = "|".join(hash_components)
    cache_key = hashlib.md5(hash_string.encode()).hexdigest()
    
    return cache_key


def get_cache_dir(processed_dir: Path) -> Path:
    """
    Get the cache directory path.
    
    Parameters
    ----------
    processed_dir : Path
        Path to processed data directory
    
    Returns
    -------
    Path
        Path to cache directory
    """
    cache_dir = processed_dir / "cache" / "clipped_rasters"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_metadata_path(cache_dir: Path, cache_key: str) -> Path:
    """
    Get the path to cache metadata file.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Path
        Path to metadata JSON file
    """
    return cache_dir / f"{cache_key}.metadata.json"


def save_cache_metadata(
    cache_dir: Path,
    cache_key: str,
    lat: float,
    lon: float,
    radius_km: float,
    source_files: List[Path],
    cached_files: List[Path]
) -> None:
    """
    Save cache metadata to JSON file.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    lat : float
        Latitude
    lon : float
        Longitude
    radius_km : float
        Radius in kilometers
    source_files : List[Path]
        List of source files
    cached_files : List[Path]
        List of cached output files
    """
    metadata = {
        "cache_key": cache_key,
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
        "created_at": datetime.now().isoformat(),
        "source_files": [
            {
                "path": str(file_path),
                "name": file_path.name,
                "mtime": file_path.stat().st_mtime if file_path.exists() else None,
                "size": file_path.stat().st_size if file_path.exists() else None,
            }
            for file_path in sorted(source_files, key=lambda p: p.name)
        ],
        "cached_files": [str(file_path) for file_path in cached_files],
    }
    
    metadata_path = get_cache_metadata_path(cache_dir, cache_key)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def load_cache_metadata(cache_dir: Path, cache_key: str) -> Optional[Dict]:
    """
    Load cache metadata from JSON file.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Optional[Dict]
        Metadata dictionary if found, None otherwise
    """
    metadata_path = get_cache_metadata_path(cache_dir, cache_key)
    if not metadata_path.exists():
        return None
    
    try:
        with open(metadata_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def is_cache_valid(cache_dir: Path, cache_key: str, source_files: List[Path]) -> Tuple[bool, Optional[str]]:
    """
    Check if cache is valid by comparing source file modification times.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    source_files : List[Path]
        List of source files to check
    
    Returns
    -------
    Tuple[bool, Optional[str]]
        (is_valid, reason) - True if cache is valid, False otherwise with reason
    """
    metadata = load_cache_metadata(cache_dir, cache_key)
    if metadata is None:
        return False, "Cache metadata not found"
    
    # Check if all cached files exist
    cached_files = metadata.get("cached_files", [])
    for cached_file_path in cached_files:
        cached_path = Path(cached_file_path)
        if not cached_path.exists():
            return False, f"Cached file not found: {cached_path.name}"
    
    # Check if source files have changed
    source_file_info = {info["name"]: info["mtime"] for info in metadata.get("source_files", [])}
    
    for source_file in source_files:
        if not source_file.exists():
            return False, f"Source file not found: {source_file.name}"
        
        # Check if file is in metadata
        if source_file.name not in source_file_info:
            return False, f"New source file detected: {source_file.name}"
        
        # Check if modification time has changed
        current_mtime = source_file.stat().st_mtime
        cached_mtime = source_file_info[source_file.name]
        
        if current_mtime != cached_mtime:
            return False, f"Source file changed: {source_file.name} (mtime: {current_mtime} != {cached_mtime})"
    
    # Check if there are missing source files (files removed)
    current_file_names = {file.name for file in source_files}
    cached_file_names = set(source_file_info.keys())
    
    if cached_file_names != current_file_names:
        return False, f"Source file list changed: {cached_file_names} != {current_file_names}"
    
    return True, None


def get_cached_files(cache_dir: Path, cache_key: str) -> Optional[List[Path]]:
    """
    Get list of cached files for a cache key.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Optional[List[Path]]
        List of cached file paths if found, None otherwise
    """
    metadata = load_cache_metadata(cache_dir, cache_key)
    if metadata is None:
        return None
    
    # Get cache subdirectory for this cache key
    cache_subdir = get_cache_subdirectory(cache_dir, cache_key)
    
    # Get cached file names from metadata
    cached_files = metadata.get("cached_files", [])
    if not cached_files:
        return None
    
    # Try to find files in cache subdirectory first, then fall back to absolute paths
    cached_paths: List[Path] = []
    for cached_file_str in cached_files:
        cached_path = Path(cached_file_str)
        
        # First, try to find file in cache subdirectory (most likely location)
        file_name = cached_path.name
        cache_file_path = cache_subdir / file_name
        if cache_file_path.exists():
            cached_paths.append(cache_file_path)
        elif cached_path.is_absolute() and cached_path.exists():
            # Fall back to absolute path if it exists
            cached_paths.append(cached_path)
        else:
            # File not found in either location
            return None
    
    # Verify all files exist
    if len(cached_paths) > 0 and all(path.exists() for path in cached_paths):
        return cached_paths
    
    return None


def get_cache_subdirectory(cache_dir: Path, cache_key: str) -> Path:
    """
    Get the subdirectory for a specific cache entry.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Path
        Path to cache subdirectory
    """
    cache_subdir = cache_dir / cache_key
    cache_subdir.mkdir(parents=True, exist_ok=True)
    return cache_subdir


def clear_cache(cache_dir: Path, cache_key: Optional[str] = None) -> int:
    """
    Clear cache entries.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : Optional[str]
        Specific cache key to clear. If None, clears all cache.
    
    Returns
    -------
    int
        Number of cache entries cleared
    """
    if cache_key is None:
        # Clear all cache
        if not cache_dir.exists():
            return 0
        
        count = 0
        for item in cache_dir.iterdir():
            if item.is_dir():
                # Remove cache subdirectory
                import shutil
                shutil.rmtree(item, ignore_errors=True)
                count += 1
            elif item.suffix == ".json":
                # Remove metadata file
                item.unlink(missing_ok=True)
                count += 1
        
        return count
    else:
        # Clear specific cache entry
        cache_subdir = cache_dir / cache_key
        metadata_path = get_cache_metadata_path(cache_dir, cache_key)
        
        count = 0
        if cache_subdir.exists():
            import shutil
            shutil.rmtree(cache_subdir, ignore_errors=True)
            count += 1
        
        if metadata_path.exists():
            metadata_path.unlink(missing_ok=True)
            count += 1
        
        return count

