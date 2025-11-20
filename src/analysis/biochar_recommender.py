# src/analysis/biochar_recommender.py
import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIG ---
EXCEL_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "Dataset_feedstock_ML.xlsx"
# Change to "data/raw" or wherever you put the original Excel file

# Load and clean once at import time
def load_and_clean_biochar_db():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Biochar Properties ")
    
    # Parse pore size column
    def parse_pore(text):
        if pd.isna(text):
            return np.nan, np.nan
        text = str(text).strip()
        sa = pv = np.nan
        parts = [p.strip() for p in text.replace(";", " ").split()]
        for p in parts:
            if "m²/g" in p or "m^2/g" in p or "m2/g" in p:
                try: sa = float(p.split()[0])
                except: pass
            if "cm³/g" in p or "cm^3/g" in p:
                try: pv = float(p.split()[0])
                except: pass
        return sa, pv
    
    sa, pv = zip(*df["pore size"].apply(parse_pore))
    df["Surface_Area_m2g"] = pd.to_numeric(sa, errors='coerce')
    df["Pore_Volume_cm3g"] = pd.to_numeric(pv, errors='coerce')
    
    # Clean numeric columns
    numeric_cols = ["Fixed carbon content", "Volatile matter", "Ash content", "pH", 
                    "C (%)", "H/C ratio", "O/C ratio", "Moisture content"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create readable name: "Type (Final Temperature°C)"
    df["Temp_C"] = pd.to_numeric(df["Final Temperature"], errors='coerce')
    df["Feedstock"] = df["Type"].fillna("Unknown")
    df["Full_Name"] = df["Feedstock"] + " (" + df["Temp_C"].fillna(0).astype(int).astype(str) + "°C)"
    df["Full_Name"] = df["Full_Name"].str.replace(" (0°C)", "", regex=False)
    
    # Select only columns we need
    cols_we_need = {
        "Full_Name": "Full_Name",
        "Fixed carbon content": "Fixed_Carbon",
        "Volatile matter": "Volatile_Matter", 
        "Ash content": "Ash_Content",
        "pH": "pH",
        "Surface_Area_m2g": "Surface_Area_m2g",
        "Pore_Volume_cm3g": "Pore_Volume_cm3g",
        "C (%)": "C_percent",
        "H/C ratio": "H_C",
        "O/C ratio": "O_C",
    }
    db = df.rename(columns={v: k for k, v in cols_we_need.items() if v in df.columns})
    db = db[list(cols_we_need.keys())].copy()
    
    return db

# Load once
BIOCHAR_DB = load_and_clean_biochar_db()
print(f"Loaded {len(BIOCHAR_DB)} biochars from Excel")

# --- RECOMMENDATION ENGINE ---
def score_biochar(row, targets):
    score = 0.0
    weight = 100.0 / len([v for v in targets.values() if v is not None])  # equal weight
    
    # Fixed Carbon
    if targets.get("fc_max") is not None and pd.notna(row["Fixed_Carbon"]) and row["Fixed_Carbon"] <= targets["fc_max"]:
        score += weight
    if targets.get("fc_range"):
        lo, hi = targets["fc_range"]
        if pd.notna(row["Fixed_Carbon"]) and lo <= row["Fixed_Carbon"] <= hi:
            score += weight
            
    # Volatile Matter
    if targets.get("vm_min") is not None and pd.notna(row["Volatile_Matter"]) and row["Volatile_Matter"] > targets["vm_min"]:
        score += weight
    if targets.get("vm_max") is not None and pd.notna(row["Volatile_Matter"]) and row["Volatile_Matter"] < targets["vm_max"]:
        score += weight
        
    # Ash
    if targets.get("ash_min") is not None and pd.notna(row["Ash_Content"]) and row["Ash_Content"] >= targets["ash_min"]:
        score += weight
    if targets.get("ash_max") is not None and pd.notna(row["Ash_Content"]) and row["Ash_Content"] <= targets["ash_max"]:
        score += weight
            
    # pH
    if targets.get("ph_min") is not None and pd.notna(row["pH"]) and row["pH"] >= targets["ph_min"]:
        score += weight
    if targets.get("ph_max") is not None and pd.notna(row["pH"]) and row["pH"] <= targets["ph_max"]:
        score += weight
            
    # Surface Area
    if targets.get("sa_min") is not None and pd.notna(row["Surface_Area_m2g"]) and row["Surface_Area_m2g"] >= targets["sa_min"]:
        score += weight
    if targets.get("sa_max") is not None and pd.notna(row["Surface_Area_m2g"]) and row["Surface_Area_m2g"] <= targets["sa_max"]:
        score += weight
            
    # Pore Volume
    if targets.get("pv_min") is not None and pd.notna(row["Pore_Volume_cm3g"]) and row["Pore_Volume_cm3g"] >= targets["pv_min"]:
        score += weight
        
    return score

def recommend_biochar(hex_df: pd.DataFrame) -> pd.DataFrame:
    db = BIOCHAR_DB.copy()
    results = []
    
    for _, row in hex_df.iterrows():
        soc = row.get("mean_soc", 0) / 10          # g/kg → %
        moisture = row.get("mean_moisture", 0) * 100  # fraction → %
        ph = row.get("mean_ph", 7.0)
        
        # 1. Combined (your original logic)
        if soc > 5.0:
            comb_name = "No biochar application recommended"
            comb_reason = "High SOC (>5%)"
        else:
            if moisture >= 80:
                targets = {"fc_max": 50, "vm_min": 30, "ash_min": 40, "ph_min": 10}
                reason = "High moisture"
            else:
                targets = {"fc_range": (60, 85), "vm_max": 20, "ash_max": 20, "ph_min": 7, "ph_max": 9.5, "sa_min": 150}
                reason = "Low moisture"
                
            if ph < 6.0:
                targets.update({"ash_min": 25, "ph_min": 10, "sa_min": 200})
                reason += " + Acidic soil"
            elif ph > 7.0:
                targets.update({"ash_max": 10, "ph_max": 6.0, "sa_min": 200})
                reason += " + Alkaline soil"
                
            db["score"] = db.apply(lambda r: score_biochar(r, targets), axis=1)
            best = db.loc[db["score"].idxmax()]
            comb_name = best["Full_Name"]
            comb_reason = reason
            
        # 2. Moisture only
        targets_m = {"fc_max": 50, "vm_min": 30, "ash_min": 40, "ph_min": 10, "sa_max": 50} if moisture >= 80 \
            else {"fc_range": (60,85), "vm_max": 20, "ash_max": 20, "ph_min": 7, "ph_max": 9.5, "sa_min": 150, "sa_max": 400}
        db["score"] = db.apply(lambda r: score_biochar(r, targets_m), axis=1)
        best_m = db.loc[db["score"].idxmax()]
        
        # 3. SOC only
        if soc > 5.0:
            soc_name, soc_reason = "No application", "SOC too high"
        elif soc < 2.6:
            targets_soc = {"vm_max": 15, "ash_min": 20, "ash_max": 30, "ph_max": 10}
            db["score"] = db.apply(lambda r: score_biochar(r, targets_soc), axis=1)
            best_soc = db.loc[db["score"].idxmax()]
            soc_name, soc_reason = best_soc["Full_Name"], "Very low SOC"
        else:
            soc_name, soc_reason = "Any high-C biochar", "Moderate SOC"
            
        # 4. pH only
        targets_ph = {"ash_min": 25, "ph_min": 10, "sa_min": 200} if ph < 6.0 \
            else {"ash_max": 10, "ph_max": 6.0, "sa_min": 200}
        db["score"] = db.apply(lambda r: score_biochar(r, targets_ph), axis=1)
        best_ph = db.loc[db["score"].idxmax()]
        
        results.append({
            "Recommended_Feedstock_Combined": comb_name,
            "Recommendation_Reason_Combined": comb_reason,
            "Recommended_Feedstock_Moisture": best_m["Full_Name"],
            "Recommended_Feedstock_SOC": soc_name,
            "Recommended_Feedstock_pH": best_ph["Full_Name"],
            "Recommendation_Reason_Moisture": "High moisture" if moisture >= 80 else "Low moisture",
            "Recommendation_Reason_SOC": soc_reason,
            "Recommendation_Reason_pH": "Acidic soil" if ph < 6.0 else "Alkaline soil",
        })
        
    return pd.concat([hex_df, pd.DataFrame(results, index=hex_df.index)], axis=1)
