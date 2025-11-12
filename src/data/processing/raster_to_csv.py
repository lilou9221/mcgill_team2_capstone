
"""
Raster to tabular conversion helpers.

These utilities transform GeoTIFF rasters into in-memory pandas DataFrames
containing longitude, latitude, and value columns. Optional persistence hooks
allow writing intermediary CSVs when required for debugging or archival, but the
default behaviour keeps data in memory so downstream steps can exchange
DataFrames directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy

VALUE_UNIT_PATTERNS: Sequence[Tuple[str, str]] = (
    ("soil_temperature", "K"),
    ("soil_temp", "K"),
    ("soil_moisture", "m3/m3"),
    ("soil_organic_carbon", "g/kg"),
    ("soc", "g/kg"),
    ("soil_ph", "pH"),
)

VALUE_SCALING_PATTERNS: Sequence[Tuple[str, float]] = (
    ("soil_pH", 0.1),
    ("soil_ph", 0.1),
)


def _infer_unit(*names: str) -> Optional[str]:
    """Infer a human-readable unit for the value column."""
    combined = " ".join(name.lower() for name in names if name)
    for pattern, unit in VALUE_UNIT_PATTERNS:
        if pattern in combined:
            return unit
    return None


def _infer_scaling_factor(*names: str) -> Optional[float]:
    """Infer a scaling factor to convert raw raster values."""
    combined = " ".join(name.lower() for name in names if name)
    for pattern, factor in VALUE_SCALING_PATTERNS:
        if pattern.lower() in combined:
            return factor
    return None


def raster_to_dataframe(
    tif_path: Path,
    band: int = 1,
    nodata_handling: str = "skip",
    value_column_name: Optional[str] = None,
) -> pd.DataFrame:
    """
    Convert a GeoTIFF raster into a pandas DataFrame with lon/lat/value columns.

    Parameters
    ----------
    tif_path
        Path to the GeoTIFF to convert.
    band
        Raster band index to read (1-based).
    nodata_handling
        Strategy for nodata values: ``"skip"`` (default) drops them,
        ``"nan"`` replaces with ``NaN``, and ``"zero"`` replaces with ``0``.
    value_column_name
        Optional override for the value column name.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``lon``, ``lat``, and a value column.
    """
    if not tif_path.exists():
        raise FileNotFoundError(f"Input raster not found: {tif_path}")

    base_column_name = value_column_name if value_column_name else tif_path.stem
    unit_label = _infer_unit(base_column_name, tif_path.stem)
    if unit_label and f"({unit_label}" not in base_column_name:
        value_column_name = f"{base_column_name} ({unit_label})"
    else:
        value_column_name = base_column_name
    scaling_factor = _infer_scaling_factor(base_column_name, tif_path.stem)

    with rasterio.open(tif_path) as src:
        height, width = src.height, src.width
        total_pixels = height * width
        print(f"  Reading raster ({height}x{width} = {total_pixels:,} pixels)...", flush=True)
        
        band_data = src.read(band).astype(np.float32)
        if scaling_factor and scaling_factor != 1.0:
            band_data *= scaling_factor

        nodata = src.nodata
        transform = src.transform
        print(f"  Converting coordinates...", flush=True)
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
        lons, lats = xy(transform, rows, cols)
        
        print(f"  Creating DataFrame...", flush=True)

        df = pd.DataFrame(
            {
                "lon": np.asarray(lons).ravel(),
                "lat": np.asarray(lats).ravel(),
                value_column_name: band_data.ravel(),
            }
        )

        if nodata is not None:
            print(f"  Filtering nodata values...", flush=True)
            if nodata_handling == "skip":
                df = df[df[value_column_name] != nodata]
            elif nodata_handling == "nan":
                df.loc[df[value_column_name] == nodata, value_column_name] = np.nan
            elif nodata_handling == "zero":
                df.loc[df[value_column_name] == nodata, value_column_name] = 0
            else:
                raise ValueError(
                    f"Unknown nodata_handling: {nodata_handling}. "
                    "Use 'skip', 'nan', or 'zero'."
                )

        if nodata_handling != "skip":
            df = df.dropna(subset=[value_column_name])

    print(f"  Conversion complete: {len(df):,} valid rows", flush=True)
    return df.reset_index(drop=True)


def _persist_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def convert_all_rasters_to_dataframes(
    input_dir: Path,
    pattern: str = "*.tif",
    band: int = 1,
    nodata_handling: str = "skip",
    persist_dir: Optional[Path] = None,
    clean_persist_dir: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Convert all rasters in ``input_dir`` into pandas DataFrames.

    Parameters
    ----------
    input_dir
        Directory containing GeoTIFF rasters.
    pattern
        Glob pattern for rasters (default ``"*.tif"``).
    band
        Raster band index to read (1-based).
    nodata_handling
        Strategy for nodata values (see :func:`raster_to_dataframe`).
    persist_dir
        Optional directory to persist CSV snapshots of each DataFrame.
    clean_persist_dir
        When ``True`` and ``persist_dir`` is provided, existing CSV files are
        removed before writing new ones.

    Returns
    -------
    Dict[str, pd.DataFrame]
        Mapping from raster stem to DataFrame.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    tif_files = sorted(input_dir.glob(pattern))
    if not tif_files:
        print(f"No GeoTIFF files found in {input_dir} matching pattern {pattern}")
        return {}

    if persist_dir:
        persist_dir.mkdir(parents=True, exist_ok=True)
        if clean_persist_dir:
            removed = 0
            for existing in persist_dir.glob("*.csv"):
                try:
                    existing.unlink()
                    removed += 1
                except Exception as exc:  # pragma: no cover - filesystem variability
                    print(
                        f"  Warning: Could not remove {existing.name}: "
                        f"{type(exc).__name__}: {exc}"
                    )
            if removed:
                print(
                    f"\nRemoved {removed} existing CSV snapshot(s) from {persist_dir}"
                )

    print(f"\nFound {len(tif_files)} GeoTIFF file(s) to convert to DataFrames")

    table_map: Dict[str, pd.DataFrame] = {}
    for tif_path in tif_files:
        try:
            print(f"\nConverting {tif_path.name} to DataFrame...")
            df = raster_to_dataframe(
                tif_path=tif_path,
                band=band,
                nodata_handling=nodata_handling,
            )
            table_map[tif_path.stem] = df

            print(f"  Rows: {len(df):,}")
            print(f"  Columns: {list(df.columns)}")

            if persist_dir:
                snapshot_path = persist_dir / f"{tif_path.stem}.csv"
                _persist_dataframe(df, snapshot_path)
                size_mb = snapshot_path.stat().st_size / (1024 * 1024)
                print(f"  Snapshot saved to {snapshot_path} ({size_mb:.2f} MB)")

        except Exception as exc:
            print(f"  Error converting {tif_path.name}: {type(exc).__name__}: {exc}")

    print(
        f"\nSuccessfully converted {len(table_map)} of {len(tif_files)} raster(s) "
        "to DataFrames"
    )
    return table_map


if __name__ == "__main__":  # pragma: no cover - manual smoke test helper
    import sys

    print(
        """============================================================
Raster to DataFrame Conversion - Debug Mode
============================================================"""
    )

    project_root = Path(__file__).parent.parent.parent.parent
    input_dir = project_root / "data" / "processed"

    if not input_dir.exists():
        print(f"\nInput directory not found: {input_dir}")
        sys.exit(0)

    tables = convert_all_rasters_to_dataframes(
        input_dir=input_dir,
        persist_dir=input_dir / "debug_tables",
        nodata_handling="skip",
    )

    if not tables:
        print("\nNo rasters processed.")
        sys.exit(0)

    first_key = next(iter(tables))
    print(
        f"""\nSample ({first_key}):
{tables[first_key].head()}"""
    )

