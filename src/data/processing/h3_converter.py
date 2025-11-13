
"""
H3 indexing helpers for in-memory DataFrames.

The previous workflow persisted intermediate CSV files to disk. These utilities
operate directly on pandas DataFrames so downstream stages can continue working
in memory while still offering optional persistence hooks for debugging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Optional

import h3
import pandas as pd


def _validate_resolution(resolution: int) -> None:
    if not isinstance(resolution, int) or not 0 <= resolution <= 15:
        raise ValueError(
            f"H3 resolution must be an integer between 0 and 15, got {resolution}"
        )


def _persist_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def add_h3_to_dataframe(
    df: pd.DataFrame,
    resolution: int = 7,
    lat_column: str = "lat",
    lon_column: str = "lon",
) -> pd.DataFrame:
    """
    Return a copy of ``df`` with ``h3_index`` column.

    The input DataFrame must contain numeric latitude/longitude columns. Rows
    with invalid coordinates are dropped before indexing.

    Note: Boundaries are NOT generated here. They are added after merge and aggregation
    to optimize memory usage.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with lat/lon columns
    resolution : int, default 7
        H3 resolution (0-15)
    lat_column : str, default "lat"
        Name of latitude column
    lon_column : str, default "lon"
        Name of longitude column

    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame with h3_index column (no boundaries)
    """
    _validate_resolution(resolution)

    if df.empty:
        raise ValueError("Input DataFrame is empty.")

    for column in (lat_column, lon_column):
        if column not in df.columns:
            raise KeyError(f"Missing required column '{column}' in DataFrame.")

    working = df.dropna(subset=[lat_column, lon_column]).copy()
    if working.empty:
        raise ValueError("No valid coordinates after dropping NaNs.")

    valid = (
        (working[lat_column].between(-90, 90))
        & (working[lon_column].between(-180, 180))
    )
    working = working[valid]
    if working.empty:
        raise ValueError("No valid coordinates after range validation.")

    working["h3_index"] = working.apply(
        lambda row: h3.latlng_to_cell(row[lat_column], row[lon_column], resolution),
        axis=1,
    )
    
    # Boundaries are NOT generated here - they are added after merge and aggregation
    # to optimize memory usage (see add_h3_boundaries_to_dataframe in suitability.py)

    return working


def process_dataframes_with_h3(
    tables: Mapping[str, pd.DataFrame],
    resolution: int = 7,
    lat_column: str = "lat",
    lon_column: str = "lon",
    persist_dir: Optional[Path] = None,
    clean_persist_dir: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Add H3 indexes to each DataFrame in ``tables``.

    Note: Boundaries are NOT generated here. They are added after merge and aggregation
    to optimize memory usage.

    Parameters
    ----------
    tables
        Mapping of dataset names to DataFrames.
    resolution
        H3 resolution (0-15, higher = finer hexagons).
    lat_column / lon_column
        Coordinate column names.
    persist_dir
        Optional directory to persist CSV snapshots for debugging.
    clean_persist_dir
        When ``True`` (default) existing CSV files in ``persist_dir`` are
        removed before writing new ones.

    Returns
    -------
    Dict[str, pd.DataFrame]
        Updated mapping containing copies of each DataFrame with H3 index columns (no boundaries).
    """
    _validate_resolution(resolution)

    if not tables:
        print("No DataFrames supplied for H3 indexing.")
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
                print(f"\nRemoved {removed} existing H3 snapshot(s) from {persist_dir}")

    processed: Dict[str, pd.DataFrame] = {}
    print(
        f"\nProcessing {len(tables)} DataFrame(s) with H3 resolution {resolution}..."
    )

    for name, df in tables.items():
        try:
            print(f"  Processing {name}...")
            enriched = add_h3_to_dataframe(
                df=df,
                resolution=resolution,
                lat_column=lat_column,
                lon_column=lon_column,
            )
            print(f"    Added H3 indexes to {len(enriched):,} row(s) (boundaries will be added after merge)")
            processed[name] = enriched

            if persist_dir:
                snapshot_path = persist_dir / f"{name}.csv"
                _persist_dataframe(enriched, snapshot_path)
                print(f"    Snapshot saved to {snapshot_path}")

        except Exception as exc:
            print(f"  Error processing {name}: {type(exc).__name__}: {exc}")

    if not processed:
        print("No DataFrames were successfully processed with H3.")

    return processed


if __name__ == "__main__":  # pragma: no cover - manual debug helper
    from pathlib import Path

    print(
        """============================================================
H3 Index Conversion - Debug Mode
============================================================"""
    )

    project_root = Path(__file__).parent.parent.parent.parent
    sample_dir = project_root / "data" / "processed" / "debug_tables"

    tables: Dict[str, pd.DataFrame] = {}
    if sample_dir.exists():
        for csv_path in sample_dir.glob("*.csv"):
            tables[csv_path.stem] = pd.read_csv(csv_path)

    if not tables:
        print("No sample CSV snapshots found for H3 demonstration.")
    else:
        processed = process_dataframes_with_h3(
            tables=tables,
            persist_dir=sample_dir / "h3_debug",
        )
        print(f"\nProcessed {len(processed)} table(s) with H3 indexing.")

