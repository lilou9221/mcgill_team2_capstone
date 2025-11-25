# Biochar Suitability Scoring System

## Overview

The scoring system evaluates soil quality based on four properties and calculates biochar suitability.

**Key Principle**: Biochar is most beneficial in poor soils, so **lower soil quality = higher biochar suitability**.

## Soil Properties

Each property is rated 0-3:

| Rating | Score | Description |
|--------|-------|-------------|
| Very Poor | 0 | Extreme stress |
| Poor | 1 | Below optimal |
| Moderate | 2 | Acceptable |
| Good | 3 | Optimal |

### 1. Soil Moisture (%)

| Range | Score |
|-------|-------|
| < 20% or > 80% | 0 (Very Poor) |
| 20-30% or 70-80% | 1 (Poor) |
| 30-50% or 60-70% | 2 (Moderate) |
| 50-60% | 3 (Good) |

**Optimal**: 50-60% | **Default if missing**: 50%

### 2. Soil Organic Carbon (%)

| Range | Score |
|-------|-------|
| < 1% | 0 (Very Poor) |
| 1-2% | 1 (Poor) |
| 2-4% | 2 (Moderate) |
| >= 4% | 3 (Good) |

**Optimal**: >= 4% | **Required** (no default)

### 3. Soil pH

| Range | Score |
|-------|-------|
| < 3.0 or > 9.0 | 0 (Very Poor) |
| 3.0-4.5 or 8.0-9.0 | 1 (Poor) |
| 4.5-6.0 or 7.0-8.0 | 2 (Moderate) |
| 6.0-7.0 | 3 (Good) |

**Optimal**: 6.0-7.0 | **Required** (no default)

### 4. Soil Temperature (°C)

| Range | Score |
|-------|-------|
| < 0°C or > 35°C | 0 (Very Poor) |
| 0-10°C or 30-35°C | 1 (Poor) |
| 10-15°C or 25-30°C | 2 (Moderate) |
| 15-25°C | 3 (Good) |

**Optimal**: 15-25°C | **Default if missing**: 20°C

## Weighted Scoring

| Property | Weight | Max Weighted Score |
|----------|--------|-------------------|
| Moisture | 0.5 | 1.5 |
| SOC | 1.0 | 3.0 |
| pH | 0.7 | 2.1 |
| Temperature | 0.2 | 0.6 |
| **Total** | **2.4** | **7.2** |

## Score Calculation

```
Soil Quality Index = (Weighted Sum / 7.2) × 100
Biochar Suitability = 100 - Soil Quality Index
```

## Final Grades

| Biochar Score | Grade | Color | Recommendation |
|---------------|-------|-------|----------------|
| >= 76 | High Suitability | Red | Biochar highly recommended |
| 51-75 | Moderate Suitability | Orange | Biochar recommended |
| 26-50 | Low Suitability | Yellow | Biochar may help |
| < 26 | Not Suitable | Green | Healthy soil, biochar not needed |

## Unit Conversions

| Property | Input Unit | Conversion |
|----------|-----------|------------|
| Moisture | m³/m³ | × 100 → % |
| SOC | g/kg | ÷ 10 → % |
| Temperature | Kelvin | − 273.15 → °C |
| pH | pH units | No conversion |

## Examples

**Poor Soil (High Biochar Suitability):**
- Moisture: 15% → 0 × 0.5 = 0.0
- SOC: 0.8% → 0 × 1.0 = 0.0
- pH: 5.0 → 2 × 0.7 = 1.4
- Temperature: 32°C → 1 × 0.2 = 0.2
- **Total**: 1.6 / 7.2 = 22.2% → **Biochar Score: 77.8** (High)

**Good Soil (Low Biochar Suitability):**
- Moisture: 55% → 3 × 0.5 = 1.5
- SOC: 5.0% → 3 × 1.0 = 3.0
- pH: 6.5 → 3 × 0.7 = 2.1
- Temperature: 20°C → 3 × 0.2 = 0.6
- **Total**: 7.2 / 7.2 = 100% → **Biochar Score: 0** (Not Suitable)
