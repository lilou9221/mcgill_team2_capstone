import pandas as pd
import streamlit as st
from pathlib import Path

# Get project root (assuming this file is in src/analyzers/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

@st.cache_data(ttl=3600)
def load_residue_ratios():
    return pd.read_csv(PROJECT_ROOT / "data" / "raw" / "residue_ratios.csv")

def calculate_biochar_from_yield(yield_kg_ha, crop_name, pyrolysis_yield=0.30):
    ratios = load_residue_ratios()
    row = ratios[ratios["Crop"] == crop_name]
    if row.empty:
        return 0, 0, 0
    urr = row["URR (t residue/t grain) Assuming AF = 0.5"].iloc[0]
    if pd.isna(urr):
        urr = row["Doesn't require AF"].iloc[0]
    residue_t_ha = (yield_kg_ha / 1000) * urr
    biochar_t_ha = residue_t_ha * pyrolysis_yield
    return round(residue_t_ha, 2), round(biochar_t_ha, 2), urr

def get_mato_grosso_crop_table(crop_portuguese_name, farmer_yield=None):
    harvest = pd.read_csv(PROJECT_ROOT / "data" / "raw" / "brazil_crop_harvest_area_2017-2024.csv")
    df = harvest[(harvest["Crop"] == crop_portuguese_name) & 
                 (harvest["Municipality"].str.contains("(MT)"))]
    latest_year = df["Year"].max()
    df = df[df["Year"] == latest_year].copy()
    
    residue_list = []
    biochar_list = []
    for _, row in df.iterrows():
        yield_to_use = farmer_yield or 3500  # fallback MT avg
        residue, biochar, _ = calculate_biochar_from_yield(yield_to_use, crop_portuguese_name.split()[0])
        residue_list.append(residue * row["Harvested_area_ha"])
        biochar_list.append(biochar * row["Harvested_area_ha"])
    
    df["Residue_t_total"] = residue_list
    df["Biochar_t_total"] = biochar_list
    df["Biochar_t_per_ha"] = df["Biochar_t_total"] / df["Harvested_area_ha"]
    
    return df.sort_values("Biochar_t_total", ascending=False), latest_year
