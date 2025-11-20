# src/analysis/biochar_recommender.py
from pathlib import Path
import pandas as pd

# Phantom integration placeholder.
# Intentionally points to the CSV in crop_data/ so we can wire it up later.
DATASET_PATH = Path(__file__).parent.parent.parent / "data" / "crop_data" / "Dataset_feedstock_ML.csv"

def recommend_biochar(hex_df: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder recommender that keeps the pipeline stable while we finish
    integrating the crop_data/Dataset_feedstock_ML.csv dataset.
    """
    if DATASET_PATH.exists():
        status = "Dataset detected in crop_data/"
        reason = "Biochar recommender placeholder — link to crop_data dataset pending"
    else:
        status = "Dataset missing"
        reason = "Provide Dataset_feedstock_ML.csv in data/crop_data/"

    hex_df["Recommended_Feedstock"] = status
    hex_df["Recommendation_Reason"] = reason
    return hex_df
