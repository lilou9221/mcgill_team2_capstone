"""PyDeck map builder for municipality-level crop area (investor view)."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import pandas as pd
import pydeck as pdk

# Try to import streamlit for caching (if available)
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    # Create a dummy cache decorator if streamlit is not available
    def _dummy_cache(func):
        return func
    st = type('obj', (object,), {'cache_data': lambda *args, **kwargs: lambda f: f})()


def _find_boundary_file(boundary_dir: Path) -> Path:
    """Return the first boundary file we can read (GPKG or SHP).
    
    In flat structure, boundary_dir is data/ and shapefile components are directly in it.
    """
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
    """Load municipality boundaries with caching if Streamlit is available."""
    def _load_impl(boundary_dir: Path) -> gpd.GeoDataFrame:
        boundary_file = _find_boundary_file(boundary_dir)
        gdf = gpd.read_file(boundary_file)
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        gdf["NM_MUN_norm"] = gdf["NM_MUN"].apply(_normalize_name)
        gdf["SIGLA_UF"] = gdf["SIGLA_UF"].astype(str)
        return gdf
    
    if HAS_STREAMLIT:
        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_load(boundary_dir_str: str):
            return _load_impl(Path(boundary_dir_str))
        return _cached_load(str(boundary_dir))
    return _load_impl(boundary_dir)


def _infer_numeric_columns(df: pd.DataFrame) -> None:
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass


def load_crop_area_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load crop area dataframe with caching if Streamlit is available."""
    def _load_impl(csv_path: Path) -> pd.DataFrame:
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

        valid_cols = [col for col in df.columns if col is not None and isinstance(col, str)]
        area_cols = [col for col in valid_cols if col.endswith('(ha)')]
        production_cols = [col for col in valid_cols if col.endswith('(ton)') and not col.startswith('Residue')]
        residue_cols = [col for col in valid_cols if col.startswith('Residue') and col.endswith('(ton)')]
        
        totals = pd.DataFrame({
            "total_crop_area_ha": df[area_cols].fillna(0).sum(axis=1),
            "total_crop_production_ton": pd.to_numeric(df[production_cols].fillna(0).sum(axis=1), errors='coerce').fillna(0).round().astype(int),
            "total_crop_residue_ton": pd.to_numeric(df[residue_cols].fillna(0).sum(axis=1), errors='coerce').fillna(0).round().astype(int)
        })
        df = pd.concat([df, totals], axis=1)

        agg = (
            df.groupby(["municipality_name_norm", "state_abbrev"], as_index=False).agg({
                "total_crop_area_ha": "sum",
                "total_crop_production_ton": "sum",
                "total_crop_residue_ton": "sum"
            })
        )
        agg["total_crop_production_ton"] = pd.to_numeric(agg["total_crop_production_ton"], errors='coerce').fillna(0).round().astype(int)
        agg["total_crop_residue_ton"] = pd.to_numeric(agg["total_crop_residue_ton"], errors='coerce').fillna(0).round().astype(int)
        return agg
    
    if HAS_STREAMLIT:
        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_load(csv_path_str: str):
            return _load_impl(Path(csv_path_str))
        return _cached_load(str(csv_path))
    return _load_impl(csv_path)


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
        print(f"Could not simplify geometries ({exc})")
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
    # Fill NaN values with 0.0 for all three data types
    # Safely convert to numeric and then to int
    merged["total_crop_area_ha"] = pd.to_numeric(merged["total_crop_area_ha"], errors='coerce').fillna(0.0)
    merged["total_crop_production_ton"] = pd.to_numeric(merged["total_crop_production_ton"], errors='coerce').fillna(0).astype(int)
    merged["total_crop_residue_ton"] = pd.to_numeric(merged["total_crop_residue_ton"], errors='coerce').fillna(0).astype(int)
    
    # Mark when production/residue should show N/A (area > 0 but production/residue = 0)
    merged["production_is_na"] = (merged["total_crop_area_ha"] > 0) & (merged["total_crop_production_ton"] == 0)
    merged["residue_is_na"] = (merged["total_crop_area_ha"] > 0) & (merged["total_crop_residue_ton"] == 0)
    
    # Default display value is crop area (maintains current behavior)
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
    data_type: str = "area",
) -> pdk.Deck:
    """
    Create municipality waste deck with specified data type.
    
    Args:
        merged_gdf: GeoDataFrame with municipality boundaries and crop data
        data_type: One of 'area', 'production', or 'residue'
    
    Returns:
        pydeck Deck object
    """
    # Validate data type
    if data_type not in ["area", "production", "residue"]:
        data_type = "area"
    
    # Select columns and calculate max value based on data type
    if data_type == "area":
        value_col = "total_crop_area_ha"
        label = "Total Crop Area"
        unit = "ha"
    elif data_type == "production":
        value_col = "total_crop_production_ton"
        label = "Total Crop Production"
        unit = "ton"
    else:  # residue
        value_col = "total_crop_residue_ton"
        label = "Total Crop Residue"
        unit = "ton"
    
    merged_gdf = merged_gdf.copy()
    vmax = merged_gdf[value_col].max() if merged_gdf[value_col].max() > 0 else 1
    
    # Ensure N/A flags exist (defensive check for cached data or older versions)
    if "production_is_na" not in merged_gdf.columns:
        merged_gdf["production_is_na"] = (merged_gdf["total_crop_area_ha"] > 0) & (merged_gdf["total_crop_production_ton"] == 0)
    if "residue_is_na" not in merged_gdf.columns:
        merged_gdf["residue_is_na"] = (merged_gdf["total_crop_area_ha"] > 0) & (merged_gdf["total_crop_residue_ton"] == 0)
    
    # Calculate colors only for the selected data type (optimize memory)
    # Set grey color for N/A values in production and residue maps
    if data_type == "production":
        merged_gdf["fill_color"] = merged_gdf.apply(
            lambda row: (128, 128, 128, 180) if row["production_is_na"] else _value_to_color(row[value_col], vmax),
            axis=1
        )
    elif data_type == "residue":
        merged_gdf["fill_color"] = merged_gdf.apply(
            lambda row: (128, 128, 128, 180) if row["residue_is_na"] else _value_to_color(row[value_col], vmax),
            axis=1
        )
    else:  # area
        merged_gdf["fill_color"] = merged_gdf[value_col].apply(
            lambda v: _value_to_color(v, vmax)
        )
    
    # Round production and residue to nearest integer for display
    # Format as N/A if area > 0 but production/residue = 0
    # Format numbers with comma separators for thousands
    if data_type == "production":
        # Safely convert to int, handling NA values
        merged_gdf["display_value_raw"] = pd.to_numeric(merged_gdf[value_col], errors='coerce').fillna(0).astype(int)
        # Format as string: show "N/A" if area > 0 but production = 0, otherwise show the number with commas
        merged_gdf["display_value"] = merged_gdf.apply(
            lambda row: "N/A" if row["production_is_na"] else f"{int(row['display_value_raw']):,}",
            axis=1
        )
    elif data_type == "residue":
        # Safely convert to int, handling NA values
        merged_gdf["display_value_raw"] = pd.to_numeric(merged_gdf[value_col], errors='coerce').fillna(0).astype(int)
        # Format as string: show "N/A" if area > 0 but residue = 0, otherwise show the number with commas
        merged_gdf["display_value"] = merged_gdf.apply(
            lambda row: "N/A" if row["residue_is_na"] else f"{int(row['display_value_raw']):,}",
            axis=1
        )
    else:  # area
        # Format area with comma separators
        merged_gdf["display_value"] = merged_gdf[value_col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")

    # Include only necessary columns in GeoJSON (optimize memory)
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
        zoom=3.0,
        min_zoom=3,
        max_zoom=12,
        pitch=0,
    )

    tooltip = {
        "html": f"""
        <b>Municipality:</b> {{NM_MUN}}<br>
        <b>State:</b> {{SIGLA_UF}}<br>
        <b>{label} ({unit}):</b> {{display_value}}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "#333333",
        },
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip=tooltip,
    )
    
    return deck


def build_investor_waste_deck_html(
    boundary_dir: Path, waste_csv_path: Path, output_path: Path, simplify_tolerance: float = 0.01, data_type: str = "area"
) -> Tuple[str, gpd.GeoDataFrame]:
    """Build investor waste deck and save as HTML."""
    merged_gdf = prepare_investor_crop_area_geodata(
        boundary_dir, waste_csv_path, simplify_tolerance=simplify_tolerance
    )
    deck = create_municipality_waste_deck(merged_gdf, data_type=data_type)
    
    # Generate HTML - pydeck's to_html() returns None if called without arguments
    try:
        # Use to_html with a file path, then read it back
        temp_html = output_path.parent / f"temp_{output_path.name}"
        deck.to_html(str(temp_html))
        html_content = temp_html.read_text(encoding='utf-8')
        temp_html.unlink()  # Clean up temp file
    except Exception as e:
        # Fallback: try to_html() without arguments (returns string)
        html_content = deck.to_html()
        if html_content is None:
            raise ValueError(f"Failed to generate HTML from deck: {e}")
    
    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding='utf-8')
    
    return html_content, merged_gdf

