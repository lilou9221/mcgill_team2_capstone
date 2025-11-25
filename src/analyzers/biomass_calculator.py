import pandas as pd
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

@st.cache_data(ttl=3600)
def load_residue_ratios():
    return pd.read_csv(PROJECT_ROOT / "data" / "residue_ratios.csv")

@st.cache_data(ttl=3600)
def load_harvest_data():
    """Cache the large harvest CSV file to avoid reloading on every call."""
    return pd.read_csv(PROJECT_ROOT / "data" / "brazil_crop_harvest_area_2017-2024.csv")
