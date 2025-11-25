
# ============================================================
# STREAMLIT APP – FINAL POLISHED & LIGHTNING-FAST VERSION + YOUR REQUESTS
# ============================================================
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import subprocess
import os
import time
import traceback

# ============================================================
# PAGE CONFIG + SESSION STATE
# ============================================================
st.set_page_config(
    page_title="Biochar Suitability Mapper",
    page_icon="Leaf",
    layout="wide",
    initial_sidebar_state="expanded"
)

for key, default in [
    ("analysis_running", False), ("current_process", None), ("analysis_results", None),
    ("data_downloaded", False), ("existing_results_checked", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# PROJECT SETUP
# ============================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
from src.utils.config_loader import load_config

@st.cache_data
def get_config():
    try:
        config = load_config()
        defaults = {
            "data": {"raw": "data/raw", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }
        for k, v in defaults.items():
            config.setdefault(k, v)
        return config
    except:
        return {
            "data": {"raw": "data/raw", "processed": "data/processed"},
            "output": {"html": "output/html"},
            "processing": {"h3_resolution": 7}
        }

config = get_config()
DOWNLOAD_SCRIPT = PROJECT_ROOT / "scripts" / "download_assets.py"
REQUIRED_DATA_FILES = [
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.shp",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.dbf",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.shx",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.prj",
    PROJECT_ROOT / "data" / "boundaries" / "BR_Municipios_2024" / "BR_Municipios_2024.cpg",
    PROJECT_ROOT / "data" / "crop_data" / "Updated_municipality_crop_production_data.csv",
    PROJECT_ROOT / "data" / "raw" / "SOC_res_250_b0.tif",
    PROJECT_ROOT / "data" / "raw" / "SOC_res_250_b10.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_moisture_res_250_sm_surface.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_pH_res_250_b0.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_pH_res_250_b10.tif",
    PROJECT_ROOT / "data" / "raw" / "soil_temp_res_250_soil_temp_layer1.tif",
]

# (Keep all your existing functions: check_required_files_exist, ensure_required_data, styling, etc.)
# ... [ALL YOUR ORIGINAL CODE FROM ensure_required_data() TO THE END OF STYLING] ...

# === YOUR ORIGINAL STYLING (unchanged) ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, .stApp {font-family: 'Inter', sans-serif; background-color: #FFFFFF !important; color: #000 !important;}
    body, html, .stApp, div, span, p, h1, h2, h3, h4, h5, h6 {color: #000 !important;}
    section[data-testid="stSidebar"] {background-color: #173a30 !important;}
    section[data-testid="stSidebar"] * {color: white !important;}
    .header-title {font-size: 3.4rem; font-weight: 700; text-align: center; color: #173a30; margin: 2rem 0 0.5rem;}
    .header-subtitle {text-align: center; color: #444444; font-size: 1.3rem; margin-bottom: 3rem;}
    .stButton > button {background-color: #64955d !important; color: white !important; border-radius: 999px; font-weight: 600; height: 3.2em;}
    .stButton > button:hover {background-color: #527a48 !important;}
    .metric-card {background: white; padding: 1.8rem; border-radius: 14px; border-left: 6px solid #64955d; box-shadow: 0 6px 20px rgba(0,0,0,0.08); text-align: center;}
    .metric-card h4 {margin: 0 0 0.5rem; color: #173a30; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.8px;}
    .metric-card p {margin: 0; font-size: 2.4rem; font-weight: 700; color: #333333;}
    .legend-box {background: white; padding: 28px; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.1); max-width: 760px; margin: 50px auto; text-align: center; border: 1px solid #eee;}
    .footer {text-align: center; padding: 6rem 0 3rem; color: #666; border-top: 1px solid #eee; margin-top: 8rem; font-size: 0.95rem;}
</style>
""", unsafe_allow_html=True)

# === HEADER & SIDEBAR (your original) ===
st.markdown('<div class="header-title">Biochar Suitability Mapper</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Precision soil health & crop residue intelligence for sustainable biochar in Mato Grosso</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Analysis Settings")
    use_coords = st.checkbox("Analyze around a location", value=True)
    lat = lon = radius = None
    if use_coords:
        c1, c2 = st.columns(2)
        with c1: lat = st.number_input("Latitude", value=-13.0, format="%.6f")
        with c2: lon = st.number_input("Longitude", value=-56.0, format="%.6f")
        radius = st.slider("Radius (km)", 25, 100, 100, 25)
    h3_res = st.slider("H3 Resolution", 5, 9, 7)
    run_btn = st.button("Run Analysis", type="primary", width='stretch')
    if st.button("Reset Cache & Restart"):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

# === YOUR FULL ORIGINAL PIPELINE & RESULT LOADING CODE (unchanged) ===
# (Keep everything from "if run_btn:" down to the end of result loading)

# === YOUR ORIGINAL FARMER & INVESTOR TABS UP TO THIS POINT (unchanged) ===
# (Keep all the code you already have for maps, recs, investor map, etc.)

# ========================================================
# FARMER TAB – ADD YOUR REQUESTED SOURCING TOOL HERE
# ========================================================
with farmer_tab:
            # === SOURCING TOOL – YOUR REQUEST (ADDED ONLY) ===
        st.markdown("### Sourcing Tool – Crop Residue & Biochar Potential (Mato Grosso only)")

        @st.cache_data(ttl=3600)
        def load_ratios():
            return pd.read_excel("data/raw/residue_ratios.xlsx")

        ratios = load_ratios()

        crop_mapping = {
            "Soybean": "Soja (em grão)",
            "Maize": "Milho (em grão)",
            "Sugarcane": "Cana-de-açúcar",
            "Cotton": "Algodão herbáceo (em caroço)"
        }

        col1, col2 = st.columns(2)
        with col1:
            crop = st.selectbox("Select crop", options=list(crop_mapping.keys()), key="sourcing_crop")
        with col2:
            farmer_yield = st.number_input("Your yield (kg/ha) – optional", min_value=0, value=None, step=100, key="sourcing_yield")

        if st.button("Calculate Biochar Potential", type="primary", key="calc_sourcing"):
            harvest = pd.read_excel("data/raw/brazil_crop_harvest_area_2017-2024.xlsx")
            df_crop = harvest[(harvest["Crop"] == crop_mapping[crop]) & 
                            (harvest["Municipality"].str.contains("(MT)"))]
            latest_year = df_crop["Year"].max()
            df_crop = df_crop[df_crop["Year"] == latest_year].copy()

            ratio_row = ratios[ratios["Crop"] == crop.split()[0]].iloc[0]
            urr = ratio_row["URR (t residue/t grain) Assuming AF = 0.5"] if pd.notna(ratio_row["URR (t residue/t grain) Assuming AF = 0.5"]) else ratio_row["Doesn't require AF"]

            yield_used = farmer_yield or 3500
            residue_t_ha = (yield_used / 1000) * urr
            biochar_t_ha = residue_t_ha * 0.30

            df_crop["Residue_t_total"] = residue_t_ha * df_crop["Harvested_area_ha"]
            df_crop["Biochar_t_total"] = biochar_t_ha * df_crop["Harvested_area_ha"]
            df_crop["Biochar_t_per_ha"] = biochar_t_ha

            total_biochar = df_crop["Biochar_t_total"].sum()
            st.success(f"{latest_year} • {len(df_crop)} municipalities • Total biochar: {total_biochar:,.0f} tons")

            display = df_crop[["Municipality", "Harvested_area_ha", "Biochar_t_per_ha", "Biochar_t_total"]].head(50)
            display = display.rename(columns={
                "Harvested_area_ha": "Area (ha)",
                "Biochar_t_per_ha": "Biochar (t/ha)",
                "Biochar_t_total": "Total Biochar (tons)"
            })
            st.dataframe(display, use_container_width=True)
            st.download_button("Download full table", df_crop.to_csv(index=False).encode(), f"MT_{crop}_biochar.csv", key="dl_sourcing")
    if csv_path and df is not None and map_paths:
        # Your existing soil maps & recs code stays here

        # === NEW: YOUR ORIGINAL REQUEST – BIOMASS TABLE + YIELD INPUT ===
        st.markdown("### Sourcing Tool – Crop Residue & Biochar Potential (Mato Grosso only)")

        # Load residue ratios
        @st.cache_data(ttl=3600)
        def load_ratios():
            return pd.read_excel("data/raw/residue_ratios.xlsx")

        ratios = load_ratios()

        crop_mapping = {
            "Soybean": "Soja (em grão)",
            "Maize": "Milho (em grão)",
            "Sugarcane": "Cana-de-açúcar",
            "Cotton": "Algodão herbáceo (em caroço)"
        }

        col1, col2 = st.columns(2)
        with col1:
            crop = st.selectbox("Select crop", options=list(crop_mapping.keys()))
        with col2:
            farmer_yield = st.number_input("Your yield (kg/ha) – optional", min_value=0, value=None, step=100)

        if st.button("Calculate Biochar Potential", type="primary"):
            harvest = pd.read_excel("data/raw/brazil_crop_harvest_area_2017-2024.xlsx")
            df_crop = harvest[(harvest["Crop"] == crop_mapping[crop]) & 
                            (harvest["Municipality"].str.contains("(MT)"))]
            latest_year = df_crop["Year"].max()
            df_crop = df_crop[df_crop["Year"] == latest_year].copy()

            ratio_row = ratios[ratios["Crop"] == crop_mapping[crop].split()[0]].iloc[0]
            urr = ratio_row["URR (t residue/t grain) Assuming AF = 0.5"] if pd.notna(ratio_row["URR (t residue/t grain) Assuming AF = 0.5"]) else ratio_row["Doesn't require AF"]

            yield_used = farmer_yield or 3500
            residue_t_ha = (yield_used / 1000) * urr
            biochar_t_ha = residue_t_ha * 0.30

            df_crop["Residue_t_total"] = residue_t_ha * df_crop["Harvested_area_ha"]
            df_crop["Biochar_t_total"] = biochar_t_ha * df_crop["Harvested_area_ha"]
            df_crop["Biochar_t_per_ha"] = biochar_t_ha

            total_biochar = df_crop["Biochar_t_total"].sum()
            st.success(f"{latest_year} • Total biochar potential: {total_biochar:,.0f} tons")

            display = df_crop[["Municipality", "Harvested_area_ha", "Biochar_t_per_ha", "Biochar_t_total"]].head(50)
            display = display.rename(columns={
                "Municipality": "Municipality",
                "Harvested_area_ha": "Area (ha)",
                "Biochar_t_per_ha": "Biochar (t/ha)",
                "Biochar_t_total": "Total Biochar (tons)"
            })
            st.dataframe(display, use_container_width=True)
            st.download_button("Download full table", df_crop.to_csv(index=False).encode(), f"MT_{crop}_biochar.csv")

    else:
        st.info("Run the analysis to view results.")

# === KEEP YOUR ORIGINAL INVESTOR TAB & FOOTER UNCHANGED ===
# (Everything else stays exactly as you had it)

st.markdown("""
<div class="footer">
    <strong>Residual Carbon</strong> • McGill University Capstone Project<br>
    Precision biochar mapping for farmers and investors in Mato Grosso, Brazil
</div>
""", unsafe_allow_html=True)
