# UPS Standard Pricing Analysis - Japan 3kg Investigation
**Date:** 2025-11-21
**Issue:** User flagged UPS Standard 4.89 EUR for Japan 3kg as "IMPOSSUIBEL" (impossible)
**Status:** ⚠️ REQUIRES USER CLARIFICATION

---

## 🔍 Executive Summary

User questioned UPS Standard pricing showing **4.89 EUR for Japan 3kg**, which appears 70% cheaper than competing services:

| Service | Price (EUR) | Type | Ratio vs Standard |
|---------|-------------|------|-------------------|
| **UPS Standard** | **4.89** | GROUND | **1.0×** (baseline) |
| FedEx IP | 16.56 | EXPRESS | 3.4× |
| UPS Express Saver | 26.45 | EXPRESS | 5.4× |
| Spring | 33.39 | EXPRESS | 6.8× |
| UPS WWE | 40.74 | ECONOMY | 8.3× |

---

## 📊 Investigation Findings

### 1. CSV Data Verification

**Source:** `data/normalized/tariff_bands.csv`
**Scope:** UPS_STANDARD_ZONE_11 (scope_id=92)
**Countries:** CN, ID, JP, MY, PH, TW (6 countries)

```csv
band_id,scope_id,min_weight,max_weight,base_amount
3526,92,1.0,1.0,4.37
3550,92,2.0,2.0,4.91
3574,92,3.0,3.0,4.89  ← TARGET
3598,92,4.0,4.0,4.90
3622,92,5.0,5.0,4.92
3646,92,6.0,6.0,7.33
```

**Weight Progression Pattern:**
- 1kg: 4.37 EUR
- 2kg: 4.91 EUR (+0.54)
- **3kg: 4.89 EUR** (-0.02) ⚠️ **ANOMALY: Price decreased**
- 4kg: 4.90 EUR (+0.01)
- 5kg: 4.92 EUR (+0.02)
- 6kg: 7.33 EUR (+2.41)

**Observation:** The 3kg price breaks the upward trend. Expected value: ~4.93 EUR (not 4.89).

---

### 2. Service Definition

**Source:** `data/normalized/services.csv`

```csv
service_id,carrier_id,code,label,service_type,max_weight_kg
6,4,UPS_STANDARD,UPS Standard,GROUND,70.0
```

- **Type:** GROUND (not EXPRESS)
- **Characteristics:** Économique, délai long (5-10 jours)
- **Coverage:** 10 pays Asie selon service_restrictions.json

---

### 3. Official Documentation

**Source:** `docs/UPS_SERVICES_GUIDE.md` (lines 5-16, 100)

> **Exemple**: Japon 2kg = **4.91 EUR** ⭐ (meilleur prix pour JP)
>
> **Use case**: Envois économiques vers Asie

**Source:** `data/service_restrictions.json` (line 35)

```json
"UPS_STANDARD": "Service Ground économique pour Asie (10 pays: CN, GB, ID, JP, KH, LA, MY, PH, TW, VN)"
```

✅ Documentation **confirms** UPS Standard at ~4.9 EUR for Japan is **intentional and documented**.

---

### 4. Data Consistency Check

**Countries in CSV vs Documentation:**

| Source | Countries |
|--------|-----------|
| `tariff_scope_countries.csv` | CN, ID, JP, MY, PH, TW **(6 countries)** |
| `service_restrictions.json` | CN, GB, ID, JP, KH, LA, MY, PH, TW, VN **(10 countries)** |

⚠️ **Discrepancy:** 4 countries (GB, KH, LA, VN) listed in restrictions but missing from tariff scopes.

---

## 🎯 Pricing Comparison Analysis

### Japan 3kg - All Available Services

```
Service                    Price    Type       Premium vs Standard
────────────────────────────────────────────────────────────────
UPS Standard               4.89     GROUND     Baseline
FedEx IP Zone I           16.56     EXPRESS    +239%
UPS Express Saver         26.45     EXPRESS    +441%
Spring                    33.39     EXPRESS    +583%
UPS WWE                   40.74     ECONOMY    +733%
```

---

## ⚠️ Critical Questions for User

### Option A: Pricing is Correct (Documentation Valid)

If documentation is accurate:
- ✅ UPS Standard is a real Ground service with ~4.9 EUR rates to Asia
- ✅ Dramatically cheaper than Express (GROUND vs EXPRESS comparison)
- ✅ Service exists in contract and should be displayed
- ⚠️ Minor fix needed: 3kg should be 4.93 EUR (not 4.89) to follow progression

### Option B: Pricing is Incorrect (Documentation Invalid)

If user's contract doesn't include UPS Standard:
- ❌ Service shouldn't exist in database
- ❌ Should be removed from `services.csv` and `tariff_bands.csv`
- ❌ Documentation was created from incorrect/outdated contract data

### Option C: Service Exists but Pricing is Wrong

If service exists but at different rates:
- ⚠️ Need correct pricing from actual UPS contract
- ⚠️ ETL script needs to be re-run with correct source data
- ⚠️ Check `data/raw/PROPOSITION TARIFAIRE YOYAKU 2023.xlsx`

---

## 🔧 Recommended Actions

### Immediate (Awaiting User Clarification)

**Question for user:**

> **Do you actually have UPS Standard Ground service in your contract for Asia (China, Japan, etc.)?**
>
> - **If YES:** Confirm pricing is ~4.9 EUR for 1-5kg range, or provide correct rates
> - **If NO:** Remove UPS_STANDARD service entirely from database
> - **If UNSURE:** Check physical UPS contract or email UPS account manager

### If Service is Valid (Option A)

```bash
# Minor fix: Correct 3kg pricing from 4.89 → 4.93
# File: data/normalized/tariff_bands.csv, line with band_id=3574
```

### If Service is Invalid (Option B)

```bash
# Remove UPS_STANDARD from:
# 1. data/normalized/services.csv (service_id=6)
# 2. data/normalized/tariff_scopes.csv (scope_id=92)
# 3. data/normalized/tariff_scope_countries.csv (scope_id=92)
# 4. data/normalized/tariff_bands.csv (scope_id=92, ~24 rows)
# 5. data/service_restrictions.json (notes section)
# 6. docs/UPS_SERVICES_GUIDE.md (section 1)
```

### If Pricing Needs Correction (Option C)

```bash
# Re-run ETL with correct source data:
# python src/etl/ups_all_services.py --source data/raw/CORRECT_FILE.xlsx
```

---

## 📝 Technical Notes

### Source Files Referenced

- `data/normalized/tariff_bands.csv` - Pricing data (band_id 3574)
- `data/normalized/services.csv` - Service definitions (service_id 6)
- `data/normalized/tariff_scope_countries.csv` - Country mappings (scope_id 92)
- `data/service_restrictions.json` - Service notes and restrictions
- `docs/UPS_SERVICES_GUIDE.md` - User documentation
- `data/raw/PROPOSITION TARIFAIRE YOYAKU 2023.xlsx` - Source contract (not readable in current format)

### ETL Process

Based on documentation reference (line 185-186 of UPS_SERVICES_GUIDE.md):
- **Source file:** `PROPAL YOYAKU ECONOMY DDU (1).xlsx`
- **ETL script:** `src/etl/ups_all_services.py`
- **Total bands:** 3,845
- **Countries:** 127 (all UPS services combined)

---

## 🚨 User Action Required

**User must clarify:**

1. **Does UPS Standard Ground service exist in your contract?**
2. **If yes, is pricing ~4.9 EUR for lightweight Asia shipments correct?**
3. **Should this service be displayed to customers in bot results?**

**Based on user's explicit feedback:**
- "IMPOSSUIBEL" suggests user believes pricing is impossible
- "corrige ce qu'il faut stp" requests fixing what's wrong
- This implies either service doesn't exist OR pricing is dramatically wrong

---

## 🎯 Next Steps

1. **AWAIT USER CLARIFICATION** on service validity
2. Based on response:
   - **Option A:** Minor price fix (4.89 → 4.93 for 3kg)
   - **Option B:** Complete service removal
   - **Option C:** Re-ETL with correct contract data
3. Redeploy to production after fix
4. Test Japan 3kg query to verify correction

---

**Analysis by:** Benjamin Belaga
**Reference:** User message "1. 🥇 UPS Standard - 4.89 EUR IMPOSSUIBEL d'autre ausis peux cher!!! double check bien stp"
