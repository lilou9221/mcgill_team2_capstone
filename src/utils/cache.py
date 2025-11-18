"""
Cache Utility Module

Provides caching functionality for clipped rasters and other expensive operations.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


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
    # Cache version: increment this to force cache invalidation across all instances
    # Version 2: Added to force invalidation when switching from 3000m to 250m SMAP files
    CACHE_VERSION = "v2"
    
    # Normalize coordinates to fixed precision for consistent hashing
    lat_rounded = round(lat, 6)
    lon_rounded = round(lon, 6)
    radius_rounded = round(radius_km, 2)
    
    # Create hash components: cache version, coordinates, radius, and source file info
    hash_components = [
        f"cache_version_{CACHE_VERSION}",
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


def get_cache_dir(processed_dir: Path, cache_type: str = "clipped_rasters") -> Path:
    """
    Get the cache directory path.
    
    Parameters
    ----------
    processed_dir : Path
        Path to processed data directory
    cache_type : str, optional
        Type of cache (default: "clipped_rasters")
        Options: "clipped_rasters", "raster_to_dataframe", "h3_indexes", etc.
    
    Returns
    -------
    Path
        Path to cache directory
    """
    cache_dir = processed_dir / "cache" / cache_type
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


def cleanup_old_coordinate_caches(
    cache_dir: Path,
    current_lat: float,
    current_lon: float,
    current_radius_km: float,
    source_files: List[Path]
) -> int:
    """
    Clean up old coordinate-specific caches, preserving protected caches.
    
    Protected caches:
    - Full state cache (no coordinates)
    - Specific coordinates (-13, -56, 100km)
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory to clean
    current_lat : float
        Current latitude (to preserve its cache)
    current_lon : float
        Current longitude (to preserve its cache)
    current_radius_km : float
        Current radius (to preserve its cache)
    source_files : List[Path]
        List of source files (to generate current cache key)
    
    Returns
    -------
    int
        Number of cache entries removed
    """
    if not cache_dir.exists():
        return 0
    
    # Protected coordinates: (-13, -56, 100km)
    protected_lat = -13.0
    protected_lon = -56.0
    protected_radius = 100.0
    
    # Generate protected cache key
    protected_cache_key = generate_cache_key(protected_lat, protected_lon, protected_radius, source_files)
    
    # Generate current cache key
    current_cache_key = generate_cache_key(current_lat, current_lon, current_radius_km, source_files)
    
    # Load metadata for all caches to determine which have coordinates
    removed_count = 0
    for item in cache_dir.iterdir():
        if not item.is_dir():
            continue
        
        cache_key = item.name
        # Skip current cache and protected cache
        if cache_key == current_cache_key or cache_key == protected_cache_key:
            continue
        
        # Check metadata to see if this is a coordinate-specific cache
        metadata_path = get_cache_metadata_path(cache_dir, cache_key)
        if not metadata_path.exists():
            # No metadata - might be an old cache format, check if it's not the current one
            continue
        
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Check if this cache has coordinates (is coordinate-specific)
            if "lat" in metadata and "lon" in metadata and "radius_km" in metadata:
                cache_lat = metadata["lat"]
                cache_lon = metadata["lon"]
                cache_radius = metadata["radius_km"]
                
                # Skip if this is the protected coordinates
                if (round(cache_lat, 6) == round(protected_lat, 6) and 
                    round(cache_lon, 6) == round(protected_lon, 6) and 
                    round(cache_radius, 2) == round(protected_radius, 2)):
                    continue
                
                # Skip if this is the current coordinates
                if (round(cache_lat, 6) == round(current_lat, 6) and 
                    round(cache_lon, 6) == round(current_lon, 6) and 
                    round(cache_radius, 2) == round(current_radius_km, 2)):
                    continue
                
                # This is an old coordinate-specific cache - remove it
                import shutil
                shutil.rmtree(item, ignore_errors=True)
                metadata_path.unlink(missing_ok=True)
                removed_count += 1
        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip if metadata is invalid
            continue
    
    return removed_count


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


# DataFrame cache functions
def generate_dataframe_cache_key(
    source_files: List[Path],
    band: int = 1,
    nodata_handling: str = "skip",
    pattern: str = "*.tif"
) -> str:
    """
    Generate a cache key for raster to DataFrame conversion.
    
    Parameters
    ----------
    source_files : List[Path]
        List of source GeoTIFF files
    band : int, optional
        Raster band index (default: 1)
    nodata_handling : str, optional
        Nodata handling strategy (default: "skip")
    pattern : str, optional
        File pattern used (default: "*.tif")
    
    Returns
    -------
    str
        Cache key (hexadecimal hash)
    """
    # Cache version: increment this to force cache invalidation across all instances
    # Version 2: Added to force invalidation when switching from 3000m to 250m SMAP files
    CACHE_VERSION = "v2"
    
    # Create hash components: cache version, conversion parameters, and source file info
    hash_components = [
        f"cache_version_{CACHE_VERSION}",
        f"band_{band}",
        f"nodata_{nodata_handling}",
        f"pattern_{pattern}",
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


def save_dataframe_cache_metadata(
    cache_dir: Path,
    cache_key: str,
    source_files: List[Path],
    band: int,
    nodata_handling: str,
    pattern: str,
    cached_dataframes: Dict[str, Path]
) -> None:
    """
    Save DataFrame cache metadata to JSON file.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    source_files : List[Path]
        List of source files
    band : int
        Raster band index
    nodata_handling : str
        Nodata handling strategy
    pattern : str
        File pattern
    cached_dataframes : Dict[str, Path]
        Dictionary mapping DataFrame names to cached file paths
    """
    metadata = {
        "cache_key": cache_key,
        "band": band,
        "nodata_handling": nodata_handling,
        "pattern": pattern,
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
        "cached_dataframes": {
            name: str(path) for name, path in cached_dataframes.items()
        },
    }
    
    metadata_path = get_cache_metadata_path(cache_dir, cache_key)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def load_dataframe_cache_metadata(cache_dir: Path, cache_key: str) -> Optional[Dict]:
    """
    Load DataFrame cache metadata from JSON file.
    
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
    return load_cache_metadata(cache_dir, cache_key)


def is_dataframe_cache_valid(
    cache_dir: Path,
    cache_key: str,
    source_files: List[Path],
    band: int,
    nodata_handling: str,
    pattern: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if DataFrame cache is valid by comparing source file metadata and parameters.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    source_files : List[Path]
        List of source files to check
    band : int
        Raster band index
    nodata_handling : str
        Nodata handling strategy
    pattern : str
        File pattern
    
    Returns
    -------
    Tuple[bool, Optional[str]]
        (is_valid, reason) - True if cache is valid, False otherwise with reason
    """
    metadata = load_dataframe_cache_metadata(cache_dir, cache_key)
    if metadata is None:
        return False, "Cache metadata not found"
    
    # Check parameters match
    if metadata.get("band") != band:
        return False, f"Band mismatch: {metadata.get('band')} != {band}"
    
    if metadata.get("nodata_handling") != nodata_handling:
        return False, f"Nodata handling mismatch: {metadata.get('nodata_handling')} != {nodata_handling}"
    
    if metadata.get("pattern") != pattern:
        return False, f"Pattern mismatch: {metadata.get('pattern')} != {pattern}"
    
    # Check if all cached DataFrames exist
    cached_dataframes = metadata.get("cached_dataframes", {})
    for name, cached_path_str in cached_dataframes.items():
        cached_path = Path(cached_path_str)
        if not cached_path.exists():
            return False, f"Cached DataFrame not found: {name} ({cached_path.name})"
    
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


def get_cached_dataframe_files(cache_dir: Path, cache_key: str) -> Optional[Dict[str, Path]]:
    """
    Get list of cached DataFrame files for a cache key.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Optional[Dict[str, Path]]
        Dictionary mapping DataFrame names to cached file paths if found, None otherwise
    """
    if not PANDAS_AVAILABLE:
        return None
    
    metadata = load_dataframe_cache_metadata(cache_dir, cache_key)
    if metadata is None:
        return None
    
    cached_dataframes = metadata.get("cached_dataframes", {})
    if not cached_dataframes:
        return None
    
    # Get cache subdirectory for this cache key
    cache_subdir = get_cache_subdirectory(cache_dir, cache_key)
    
    # Try to find files in cache subdirectory
    cached_paths: Dict[str, Path] = {}
    for name, cached_path_str in cached_dataframes.items():
        cached_path = Path(cached_path_str)
        
        # First, try to find file in cache subdirectory (most likely location)
        file_name = cached_path.name
        cache_file_path = cache_subdir / file_name
        if cache_file_path.exists():
            cached_paths[name] = cache_file_path
        elif cached_path.is_absolute() and cached_path.exists():
            # Fall back to absolute path if it exists
            cached_paths[name] = cached_path
        else:
            # File not found
            return None
    
    # Verify all files exist
    if len(cached_paths) > 0 and all(path.exists() for path in cached_paths.values()):
        return cached_paths
    
    return None


def load_cached_dataframes(cache_dir: Path, cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Load cached DataFrames from Parquet or CSV files.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Optional[Dict[str, pd.DataFrame]]
        Dictionary mapping DataFrame names to DataFrames if found, None otherwise
    """
    if not PANDAS_AVAILABLE:
        return None
    
    cached_paths = get_cached_dataframe_files(cache_dir, cache_key)
    if cached_paths is None:
        return None
    
    dataframes: Dict[str, Any] = {}
    for name, cached_path in cached_paths.items():
        try:
            # Try to load as Parquet first (faster, more efficient)
            if cached_path.suffix == ".parquet":
                df = pd.read_parquet(cached_path)
            elif cached_path.suffix == ".csv":
                df = pd.read_csv(cached_path)
            else:
                # Try Parquet first, fall back to CSV
                parquet_path = cached_path.with_suffix(".parquet")
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                else:
                    df = pd.read_csv(cached_path)
            
            dataframes[name] = df
        except Exception as e:
            # Failed to load cached DataFrame
            return None
    
    return dataframes if dataframes else None


def save_dataframes_to_cache(
    cache_dir: Path,
    cache_key: str,
    dataframes: Dict[str, Any],
    use_parquet: bool = True
) -> Dict[str, Path]:
    """
    Save DataFrames to cache as Parquet or CSV files.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    dataframes : Dict[str, pd.DataFrame]
        Dictionary mapping DataFrame names to DataFrames
    use_parquet : bool, optional
        Whether to use Parquet format (default: True, faster and more efficient)
    
    Returns
    -------
    Dict[str, Path]
        Dictionary mapping DataFrame names to cached file paths
    """
    if not PANDAS_AVAILABLE:
        return {}
    
    cache_subdir = get_cache_subdirectory(cache_dir, cache_key)
    cached_paths: Dict[str, Path] = {}
    
    for name, df in dataframes.items():
        if use_parquet:
            cached_path = cache_subdir / f"{name}.parquet"
            try:
                df.to_parquet(cached_path, index=False, compression="snappy")
            except Exception:
                # Fall back to CSV if Parquet fails
                cached_path = cache_subdir / f"{name}.csv"
                df.to_csv(cached_path, index=False)
        else:
            cached_path = cache_subdir / f"{name}.csv"
            df.to_csv(cached_path, index=False)
        
        cached_paths[name] = cached_path
    
    return cached_paths


# H3 indexes cache functions
def generate_h3_cache_key(
    dataframes: Dict[str, Any],
    resolution: int,
    lat_column: str = "lat",
    lon_column: str = "lon"
) -> str:
    """
    Generate a cache key for H3 indexing.
    
    Parameters
    ----------
    dataframes : Dict[str, pd.DataFrame]
        Dictionary mapping DataFrame names to DataFrames
    resolution : int
        H3 resolution (0-15)
    lat_column : str, optional
        Name of latitude column (default: "lat")
    lon_column : str, optional
        Name of longitude column (default: "lon")
    
    Returns
    -------
    str
        Cache key (hexadecimal hash)
    """
    # Cache version: increment this to force cache invalidation across all instances
    # Version 2: Added to force invalidation when switching from 3000m to 250m SMAP files
    CACHE_VERSION = "v2"
    
    # Create hash components: cache version, H3 parameters, and DataFrame info
    hash_components = [
        f"cache_version_{CACHE_VERSION}",
        f"resolution_{resolution}",
        f"lat_col_{lat_column}",
        f"lon_col_{lon_column}",
    ]
    
    # Add DataFrame info (name, row count, column hash)
    # Sort by name for consistent hashing
    sorted_names = sorted(dataframes.keys())
    for name in sorted_names:
        df = dataframes[name]
        if df is not None and not df.empty:
            # Create a hash based on DataFrame shape and column names
            # This ensures cache invalidates if DataFrames change significantly
            row_count = len(df)
            col_names = sorted(df.columns.tolist())
            col_hash = hashlib.md5("|".join(col_names).encode()).hexdigest()[:8]
            df_info = f"{name}_{row_count}_{col_hash}"
            hash_components.append(df_info)
    
    # Create hash from all components
    hash_string = "|".join(hash_components)
    cache_key = hashlib.md5(hash_string.encode()).hexdigest()
    
    return cache_key


def save_h3_cache_metadata(
    cache_dir: Path,
    cache_key: str,
    dataframes: Dict[str, Any],
    resolution: int,
    lat_column: str,
    lon_column: str,
    cached_dataframes: Dict[str, Path]
) -> None:
    """
    Save H3 cache metadata to JSON file.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    dataframes : Dict[str, pd.DataFrame]
        Dictionary mapping DataFrame names to DataFrames
    resolution : int
        H3 resolution
    lat_column : str
        Name of latitude column
    lon_column : str
        Name of longitude column
    cached_dataframes : Dict[str, Path]
        Dictionary mapping DataFrame names to cached file paths
    """
    metadata = {
        "cache_key": cache_key,
        "resolution": resolution,
        "lat_column": lat_column,
        "lon_column": lon_column,
        "created_at": datetime.now().isoformat(),
        "dataframes": {
            name: {
                "rows": len(df) if df is not None and not df.empty else 0,
                "columns": sorted(df.columns.tolist()) if df is not None and not df.empty else []
            }
            for name, df in sorted(dataframes.items())
        },
        "cached_dataframes": {
            name: str(path) for name, path in cached_dataframes.items()
        },
    }
    
    metadata_path = get_cache_metadata_path(cache_dir, cache_key)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def load_h3_cache_metadata(cache_dir: Path, cache_key: str) -> Optional[Dict]:
    """
    Load H3 cache metadata from JSON file.
    
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
    return load_cache_metadata(cache_dir, cache_key)


def is_h3_cache_valid(
    cache_dir: Path,
    cache_key: str,
    dataframes: Dict[str, Any],
    resolution: int,
    lat_column: str,
    lon_column: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if H3 cache is valid by comparing DataFrame metadata and parameters.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    dataframes : Dict[str, pd.DataFrame]
        Dictionary mapping DataFrame names to DataFrames
    resolution : int
        H3 resolution
    lat_column : str
        Name of latitude column
    lon_column : str
        Name of longitude column
    
    Returns
    -------
    Tuple[bool, Optional[str]]
        (is_valid, reason) - True if cache is valid, False otherwise with reason
    """
    metadata = load_h3_cache_metadata(cache_dir, cache_key)
    if metadata is None:
        return False, "Cache metadata not found"
    
    # Check parameters match
    if metadata.get("resolution") != resolution:
        return False, f"Resolution mismatch: {metadata.get('resolution')} != {resolution}"
    
    if metadata.get("lat_column") != lat_column:
        return False, f"Lat column mismatch: {metadata.get('lat_column')} != {lat_column}"
    
    if metadata.get("lon_column") != lon_column:
        return False, f"Lon column mismatch: {metadata.get('lon_column')} != {lon_column}"
    
    # Check if all cached DataFrames exist
    cached_dataframes = metadata.get("cached_dataframes", {})
    for name, cached_path_str in cached_dataframes.items():
        cached_path = Path(cached_path_str)
        if not cached_path.exists():
            return False, f"Cached DataFrame not found: {name} ({cached_path.name})"
    
    # Check if DataFrame metadata matches
    cached_df_info = metadata.get("dataframes", {})
    for name, df in dataframes.items():
        if name not in cached_df_info:
            return False, f"New DataFrame detected: {name}"
        
        # Check row count and columns match
        cached_info = cached_df_info[name]
        if cached_info["rows"] != len(df) if df is not None and not df.empty else 0:
            return False, f"DataFrame row count changed: {name} ({cached_info['rows']} != {len(df) if df is not None and not df.empty else 0})"
        
        cached_cols = set(cached_info.get("columns", []))
        current_cols = set(df.columns.tolist()) if df is not None and not df.empty else set()
        if cached_cols != current_cols:
            return False, f"DataFrame columns changed: {name}"
    
    # Check if there are missing DataFrames (DataFrames removed)
    current_df_names = set(dataframes.keys())
    cached_df_names = set(cached_df_info.keys())
    
    if cached_df_names != current_df_names:
        return False, f"DataFrame list changed: {cached_df_names} != {current_df_names}"
    
    return True, None


def load_cached_h3_dataframes(cache_dir: Path, cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Load cached H3-indexed DataFrames from Parquet or CSV files.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    
    Returns
    -------
    Optional[Dict[str, pd.DataFrame]]
        Dictionary mapping DataFrame names to DataFrames if found, None otherwise
    """
    return load_cached_dataframes(cache_dir, cache_key)


def save_h3_dataframes_to_cache(
    cache_dir: Path,
    cache_key: str,
    dataframes: Dict[str, Any],
    use_parquet: bool = True
) -> Dict[str, Path]:
    """
    Save H3-indexed DataFrames to cache as Parquet or CSV files.
    
    Parameters
    ----------
    cache_dir : Path
        Cache directory
    cache_key : str
        Cache key
    dataframes : Dict[str, pd.DataFrame]
        Dictionary mapping DataFrame names to DataFrames
    use_parquet : bool, optional
        Whether to use Parquet format (default: True, faster and more efficient)
    
    Returns
    -------
    Dict[str, Path]
        Dictionary mapping DataFrame names to cached file paths
    """
    return save_dataframes_to_cache(cache_dir, cache_key, dataframes, use_parquet)

