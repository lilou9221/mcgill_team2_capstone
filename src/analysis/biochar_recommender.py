# src/analysis/biochar_recommender.py
import pandas as pd
import numpy as np
from pathlib import Path

# Load once at import time
BIOCHAR_DB = pd.read_csv(Path(__file__).parent.parent.parent / "data" / "processed" / "biochar_database_clean.csv")
BIOCHAR_DB["Full_Name"] = BIOCHAR_DB["Feedstock"] + " (" + BIOCHAR_DB["Temp_C"].astype(int).astype(str) + "°C)"

def parse_pore_size(text):
    if pd.isna(text) or not text:
        return np.nan, np.nan
    parts = str(text).split(";")
    sa = pv = np.nan
    for p in parts:
        if "m²/g" in p or "m^2/g" in p:
            sa = float(p.split()[0])
        if "cm³/g" in p or "cm^3/g" in p:
            pv = float(p.split()[0])
    return sa, pv

def recommend_biochar(hex_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 8 new columns to hex_df (in-place):
    - Recommended_Feedstock_Combined + Reason_Combined
    - Recommended_Feedstock_Moisture + Reason_Moisture
    - Recommended_Feedstock_SOC + Reason_SOC
    - Recommended_Feedstock_pH + Reason_pH
    """
    db = BIOCHAR_DB.copy()

    # Helper scoring function (0-100)
    def score_row(row, targets):
        score = 0
        if targets.get("Fixed_Carbon_max") is not None and row["Fixed_Carbon"] <= targets["Fixed_Carbon_max"]: score += 20
        if targets.get("Fixed_Carbon_range") and targets["Fixed_Carbon_range"][0] <= row["Fixed_Carbon"] <= targets["Fixed_Carbon_range"][1]: score += 25
        if targets.get("Volatile_max") and row["Volatile_Matter"] > targets["Volatile_max"]: score += 20
        if targets.get("Volatile_min") and row["Volatile_Matter"] < targets["Volatile_min"]: score += 20
        if targets.get("Ash_max") and row["Ash_Content"] > targets["Ash_max"]: score += 20
        if targets.get("Ash_min") and row["Ash_Content"] < targets["Ash_min"]: score += 20
        if targets.get("pH_min") and row["pH"] > targets["pH_min"]: score += 20
        if targets.get("pH_max") and row["pH"] < targets["pH_max"]: score += 20
        if targets.get("Surface_Area_max") and row["Surface_Area_m2g"] < targets["Surface_Area_max"]: score += 15
        if targets.get("Surface_Area_min") and row["Surface_Area_m2g"] > targets["Surface_Area_min"]: score += 20
        if targets.get("Pore_Volume_max") and row["Pore_Volume_cm3g"] < targets["Pore_Volume_max"]: score += 15
        if targets.get("Pore_Volume_min") and row["Pore_Volume_cm3g"] > targets["Pore_Volume_min"]: score += 15
        return score

    results = []
    for idx, hex_row in hex_df.iterrows():
        soc = hex_row.get("mean_soc", 0) / 10  # assuming SOC is in g/kg → convert to %
        moisture = hex_row.get("mean_moisture", 0) * 100  # fraction → %
        ph = hex_row.get("mean_ph", 7.0)

        # 1. COMBINED RECOMMENDATION (your original logic)
        if soc > 5.0:
            combined_feed = "No biochar application recommended"
            combined_reason = "SOC already high (>5%)"
        else:
            if moisture >= 80:
                targets = {"Fixed_Carbon_max": 50, "Volatile_max": 30, "Ash_max": 40, "pH_min": 10, "Surface_Area_max": 100}
                reason = "High moisture (≥80%)"
            else:
                targets = {"Fixed_Carbon_range": (60, 85), "Volatile_min": 20, "Ash_min": 20, "pH_min": 7, "pH_max": 9.5, "Surface_Area_min": 150}
                reason = "Low moisture (<80%)"

            if ph < 6.0:
                targets.update({"Ash_max": 100, "Ash_min": 25, "pH_min": 10, "Surface_Area_min": 200})
                reason += " + Acidic soil"
            elif ph > 7.0:
                targets.update({"Ash_min": 10, "pH_max": 6.0, "Surface_Area_min": 200})
                reason += " + Alkaline soil"

            db["score"] = db.apply(lambda r: score_row(r, targets), axis=1)
            best = db.loc[db["score"].idxmax()]
            combined_feed = best["Full_Name"]
            combined_reason = reason

        # 2. MOISTURE-ONLY
        if moisture >= 80:
            targets = {"Fixed_Carbon_max": 50, "Volatile_max": 30, "Ash_max": 40, "pH_min": 10, "Surface_Area_max": 50, "Pore_Volume_max": 0.1}
            reason_m = "High moisture → needs high ash, low stability"
        else:
            targets = {"Fixed_Carbon_range": (60,85), "Volatile_min": 20, "Ash_min": 20, "pH_min": 7, "pH_max": 9.5,
                       "Surface_Area_min": 150, "Surface_Area_max": 400, "Pore_Volume_min": 0.2, "Pore_Volume_max": 0.5}
            reason_m = "Low moisture → needs high stability & porosity"

        db["score"] = db.apply(lambda r: score_row(r, targets), axis=1)
        best_m = db.loc[db["score"].idxmax()]

        # 3. SOC-ONLY
        if soc > 5.0:
            feed_soc = "No application"
            reason_soc = "SOC too high (>5%)"
        elif soc < 2.6:
            targets = {"Volatile_min": 15, "Ash_min": 20, "Ash_max": 30, "C_percent_min": 60, "O_C_max": 0.4, "pH_max": 10}
            reason_soc = "Very low SOC → needs ultra-stable biochar"
            db["score"] = db.apply(lambda r: score_row(r, targets), axis=1)
            best_soc = db.loc[db["score"].idxmax()]
            feed_soc = best_soc["Full_Name"]
        else:
            feed_soc = "Any high-carbon biochar suitable"
            reason_soc = "SOC moderate (2.6–5.0%)"

        # 4. pH-ONLY
        if ph < 6.0:
            targets = {"Ash_min": 25, "pH_min": 10, "Surface_Area_min": 200}
            reason_ph = "Acidic soil → needs strong liming biochar"
        else:
            targets = {"Ash_min": 10, "pH_max": 6.0, "Surface_Area_min": 200}
            reason_ph = "Alkaline soil → needs acidic, low-ash biochar"

        db["score"] = db.apply(lambda r: score_row(r, targets), axis=1)
        best_ph = db.loc[db["score"].idxmax()]

        results.append({
            "Recommended_Feedstock_Combined": combined_feed,
            "Recommendation_Reason_Combined": combined_reason,
            "Recommended_Feedstock_Moisture": best_m["Full_Name"],
            "Recommendation_Reason_Moisture": reason_m,
            "Recommended_Feedstock_SOC": feed_soc if 'feed_soc' in locals() else best_soc["Full_Name"],
            "Recommendation_Reason_SOC": reason_soc if 'reason_soc' in locals() else "Low SOC",
            "Recommended_Feedstock_pH": best_ph["Full_Name"],
            "Recommendation_Reason_pH": reason_ph,
        })

    result_df = pd.DataFrame(results, index=hex_df.index)
    return pd.concat([hex_df, result_df], axis=1)
