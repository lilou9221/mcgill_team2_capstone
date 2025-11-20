"""PyDeck map builder for municipality-level crop area (investor view)."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import pandas as pd
import pydeck as pdk


def _find_boundary_file(boundary_dir: Path) -> Path:
    """Return the first boundary file we can read (GPKG or SHP)."""
    for pattern in ("*.gpkg", "*.shp"):
        matches = sorted(boundary_dir.glob(pattern))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"No boundary files found in {boundary_dir}. Expected a .gpkg or .shp file."
    )


def _normalize_name(value: str) -> str:
    if value is None:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("utf-8")
    return (
        value.replace("'", "")
        .replace("-", " ")
        .replace("  ", " ")
        .strip()
        .lower()
    )


def load_municipality_boundaries(boundary_dir: Path) -> gpd.GeoDataFrame:
    boundary_file = _find_boundary_file(boundary_dir)
    gdf = gpd.read_file(boundary_file)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf["NM_MUN_norm"] = gdf["NM_MUN"].apply(_normalize_name)
    gdf["SIGLA_UF"] = gdf["SIGLA_UF"].astype(str)
    return gdf


# No special fallback required now; we'll use every numeric column.


def _infer_numeric_columns(df: pd.DataFrame) -> None:
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass


def load_crop_area_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    _infer_numeric_columns(df)

    if "municipality_name" in df.columns:
        df["municipality_name_norm"] = df["municipality_name"].apply(_normalize_name)
    else:
        df["municipality_name_norm"] = (
            df["municipality_with_state"]
            .str.split("(")
            .str[0]
            .str.strip()
            .apply(_normalize_name)
        )
    df["state_abbrev"] = df["municipality_with_state"].str.extract(r"\((.*?)\)").iloc[:, 0]
    df["state_abbrev"] = df["state_abbrev"].fillna("").str.strip().str.upper()

    numeric_cols = df.select_dtypes(include="number").columns
    df["total_crop_area_ha"] = df[numeric_cols].fillna(0).sum(axis=1)

    agg = (
        df.groupby(["municipality_name_norm", "state_abbrev"], as_index=False)["total_crop_area_ha"]
        .sum()
    )
    return agg


def _simplify_geometries(gdf: gpd.GeoDataFrame, tolerance: float = 0.01) -> gpd.GeoDataFrame:
    """Simplify geometries to lighten the map without breaking topology."""
    if tolerance <= 0:
        return gdf
    try:
        simplified = gdf.geometry.simplify(tolerance, preserve_topology=True)
        simplified = simplified.buffer(0)
        simplified_series = gpd.GeoSeries(
            simplified, index=gdf.index, crs=gdf.crs, name=gdf.geometry.name
        )
        gdf = gdf.set_geometry(simplified_series)
    except Exception as exc:
        print(f"Warning: could not simplify geometries ({exc})")
    return gdf


def prepare_investor_crop_area_geodata(
    boundary_dir: Path, waste_csv_path: Path, simplify_tolerance: float = 0.01
) -> gpd.GeoDataFrame:
    boundaries = load_municipality_boundaries(boundary_dir)
    boundaries = _simplify_geometries(boundaries, simplify_tolerance)
    crop_df = load_crop_area_dataframe(waste_csv_path)
    merged = boundaries.merge(
        crop_df,
        left_on=["NM_MUN_norm", "SIGLA_UF"],
        right_on=["municipality_name_norm", "state_abbrev"],
        how="left",
    )
    merged["total_crop_area_ha"] = merged["total_crop_area_ha"].fillna(0.0)
    merged["display_value"] = merged["total_crop_area_ha"]
    return merged


def _value_to_color(value: float, vmax: float) -> Tuple[int, int, int, int]:
    if vmax <= 0:
        return (200, 200, 200, 120)
    ratio = min(max(value / vmax, 0.0), 1.0)
    r = int(255 * ratio)
    g = int(200 * (1 - ratio))
    b = int(90 + 50 * ratio)
    return (r, g, b, 180)


def create_municipality_waste_deck(
    merged_gdf: gpd.GeoDataFrame,
) -> pdk.Deck:
    vmax = merged_gdf["display_value"].max()
    merged_gdf = merged_gdf.copy()
    merged_gdf["fill_color"] = merged_gdf["display_value"].apply(
        lambda v: _value_to_color(v, vmax)
    )

    geojson_data = json.loads(
        merged_gdf[
            ["geometry", "NM_MUN", "SIGLA_UF", "display_value", "fill_color"]
        ].to_json()
    )

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_data,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=0.5,
        pickable=True,
        auto_highlight=True,
    )

    center = merged_gdf.geometry.union_all().centroid
    view_state = pdk.ViewState(
        latitude=center.y,
        longitude=center.x,
        zoom=4.0,
        min_zoom=3,
        max_zoom=12,
        pitch=0,
    )

    tooltip = {
        "html": """
        <b>Municipality:</b> {NM_MUN}<br>
        <b>State:</b> {SIGLA_UF}<br>
        <b>Total Crop Area (ha):</b> {display_value}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "#333333",
        },
    }

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip=tooltip,
    )


def build_investor_waste_deck(
    boundary_dir: Path, waste_csv_path: Path, simplify_tolerance: float = 0.01
) -> Tuple[pdk.Deck, gpd.GeoDataFrame]:
    merged_gdf = prepare_investor_crop_area_geodata(
        boundary_dir, waste_csv_path, simplify_tolerance=simplify_tolerance
    )
    deck = create_municipality_waste_deck(merged_gdf)
    return deck, merged_gdf

