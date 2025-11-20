# UPS Standard/Express Saver - Integration Report (Phase 3)

**Date:** 2025-11-20
**Phase:** Phase 3 - UPS Integration
**Status:** ⚠️ **PARTIAL** - ETL Complete, Pricing Logic Needs Fixes

---

## Executive Summary

Successfully extracted **1,541 rate bands** from UPS Excel file covering **2 services** (Express Saver, Standard) across **28 unique zones**. However, integration is **INCOMPLETE** due to:

1. ❌ **Missing Zone→Country Mappings** (only 10 countries mapped out of 200+)
2. ❌ **Pricing Engine Bugs** (negative surcharges not calculated correctly)
3. ⚠️ **Multiple Rates Per Weight** (Doc vs Pkg types not handled properly)

**Recommendation:** Complete zone mappings + fix surcharge logic before production use.

---

## Integration Statistics

### Data Extracted

| Metric | Value |
|--------|-------|
| Excel sheets processed | 2 (Express Saver, Standard) |
| Rate bands extracted | 1,541 |
| UPS zones identified | 28 unique zones |
| Countries mapped | 10 (CN, ID, JP, MY, PH, TW, VN, KH, LA, GB) |
| Countries missing | 190+ (DE, FR, IT, ES, US, AU, etc.) |
| ETL code lines | 485 |

### Normalized Data

| Table | Records Added |
|-------|---------------|
| carriers | +1 (UPS) |
| services | +2 (Express Saver, Standard) |
| tariff_scopes | +56 (28 zones × 2 services) |
| tariff_scope_countries | +20 (INCOMPLETE - 90% missing) |
| tariff_bands | +1,541 |
| surcharge_rules | +3 (documented but not working) |

### Total Engine Data (4 Carriers)

- **Carriers:** 4 (La Poste, Spring, FedEx, UPS)
- **Services:** 6
- **Tariff Scopes:** 109
- **Tariff Bands:** 4,097
- **Countries:** 200+ (via resolver, but UPS only 10 mapped)

---

## UPS Services Extracted

### 1. UPS Express Saver (EXPRESS_SAVER)

**Characteristics:**
- **Code:** `UPS_EXPRESS_SAVER`
- **Type:** EXPRESS
- **Direction:** EXPORT (France → World)
- **Max Weight:** 70kg
- **Rate Bands:** 965
- **Zones:** 20 (TB: 3, 4, 5, 8, 51, 52, 505 | WW: 6, 7, 8, 9, 10, 11, 12, 13, 703, etc.)
- **Documented Surcharges:**
  - Fuel Discount: -30% on freight
  - Residential Discount: -50% on freight (if residential delivery)

**Excel Source:** Sheet `04_Expédition-Express Saver`

---

### 2. UPS Standard (STANDARD)

**Characteristics:**
- **Code:** `UPS_STANDARD`
- **Type:** GROUND
- **Direction:** EXPORT (France → World)
- **Max Weight:** 70kg
- **Rate Bands:** 576
- **Zones:** 24 (DOM: 1, 2, 3, 4, 11, 22, 33, 4-Corse | TB: 4, 5, 6, 7, etc.)
- **Documented Surcharges:**
  - Weekly Delivery Surcharge: +100% on freight

**Excel Source:** Sheet `06_Expédition-Standard mono-colis`

**Note:** "DOM" (Domestic) zones are for France domestic shipments. "TB" (Trade Bloc) likely refers to Europe.

---

## Zone Mapping - Critical Issue

### Known Zone→Country Mappings (from Excel)

| Zone | Market | Countries | ISO2 Codes |
|------|--------|-----------|------------|
| 11 | WW | China, Indonesia, Japan, Malaysia, Philippines, Taiwan | CN, ID, JP, MY, PH, TW |
| 12 | WW | Vietnam | VN |
| 13 | WW | Cambodia, Laos | KH, LA |
| 703 | WW | United Kingdom | GB |

**Total:** 10 countries mapped (5% coverage)

### Missing Zone Mappings

**Unmapped zones:** 3, 4, 5, 6, 7, 8, 9, 10, 51, 52, 505, 1, 2, 22, 33, etc.

**Critical missing countries:**
- **Europe:** Germany (DE), France (FR), Italy (IT), Spain (ES), Netherlands (NL), Belgium (BE)
- **Americas:** USA (US), Canada (CA), Brazil (BR), Mexico (MX)
- **Asia:** India (IN), South Korea (KR), Thailand (TH), Singapore (SG)
- **Oceania:** Australia (AU), New Zealand (NZ)

**Root Cause:** UPS Excel file does not contain a comprehensive zone chart like FedEx PDF did. Only 4 zones have country names in column headers.

**Required Action:**
1. Contact UPS for official France→World zone chart document
2. Or manually build mapping based on UPS public zone charts
3. Update `UPS_ZONE_COUNTRIES_PARTIAL` dictionary in `src/etl/ups.py`
4. Re-run ETL: `python3 src/etl/ups.py`

---

## Pricing Engine Issues

### Issue 1: Negative Surcharges Not Calculated Correctly

**Symptoms:**
```
Query: 2kg → Japan

UPS Express Saver:
  Fret: 32.44 EUR
  TOTAL: 6.49 EUR  ❌ Should be ~22.71 EUR (32.44 - 30%)
```

**Expected Behavior:**
- Freight: 32.44 EUR
- Fuel Discount (-30%): -9.73 EUR
- **Total: 22.71 EUR**

**Actual Behavior:**
- Total shows 6.49 EUR (incorrect)

**Root Cause:** Pricing engine (`src/engine/engine.py`) likely doesn't handle negative percentage surcharges correctly, or there's a bug in surcharge calculation.

**Fix Required:**
1. Review `_calculate_surcharges()` method in `engine.py`
2. Ensure negative values work: `amount = freight * (surcharge_value / 100)`
3. Test with UPS surcharges: -30%, -50%, +100%

---

### Issue 2: Multiple Rates Per Weight (Package Types)

**Symptoms:**
UPS has different rates for same weight depending on package type:
```
2.0kg Zone 11:
  - 32.44 EUR (Doc)
  - 24.95 EUR (Doc)
  - 26.44 EUR (Pkg)
  - 28.68 EUR (Pkg)
```

**Current Behavior:** Engine picks one arbitrarily (likely first match).

**Ideal Behavior:** Engine should either:
1. Pick cheapest rate per weight
2. Or expose package type as a user parameter (`!price 2kg JP doc`)
3. Or create separate scopes per package type (UPS_EXPRESS_SAVER_ZONE_11_DOC, etc.)

**Recommendation:** For now, use cheapest rate per weight. Package type selection can be Phase 5 enhancement.

---

### Issue 3: Surcharge Conditions Not Implemented

**Documented surcharges:**
```json
{
  "delivery_type": "residential",    // Not implemented
  "delivery_frequency": "weekly"     // Not implemented
}
```

**Current Behavior:** Surcharges are stored in CSV but conditions are ignored by engine.

**Fix Required:**
1. Add parameters to pricing queries: `residential: bool`, `delivery_frequency: str`
2. Implement condition matching in `_calculate_surcharges()`
3. Update CLI to accept optional flags: `!price 2kg JP --residential`

**Priority:** Low (Phase 5 enhancement)

---

## Test Results

### Test 1: 2kg → Japan (Zone 11)

```
✅ 5 offers found:

1. ⚠️  UPS Express Saver: 6.49 EUR  (INCORRECT - surcharge bug)
2. ⚠️  UPS Standard: 9.82 EUR  (INCORRECT - surcharge bug)
3. ✅ FedEx IP Export: 13.91 EUR
4. ✅ La Poste Delivengo: 25.75 EUR
5. ✅ Spring ROW: 28.98 EUR
```

**Winner:** Should be FedEx (13.91 EUR) after fixing UPS bugs.

---

### Test 2: 1kg → UK (Zone 703)

```
✅ 2 offers found:

1. ✅ La Poste Delivengo: 5.75 EUR
2. ⚠️  UPS Express Saver: 23.99 EUR  (Displayed "Fret: 119.95 EUR" - clearly wrong)
```

**Winner:** La Poste (5.75 EUR)

**Note:** FedEx doesn't cover UK in our rate tables (Zone X missing), Spring doesn't have UK.

---

### Test 3: 2kg → Germany

```
❌ UPS not found (DE not mapped to any zone)

✅ 2 offers found:
1. Spring Europe: 4.41 EUR
2. La Poste Delivengo: 4.65 EUR
```

**Winner:** Spring (4.41 EUR)

**Missing:** UPS should cover Germany (likely Zone 4 or 5) but zone mapping incomplete.

---

## Files Created/Modified

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/etl/ups.py` | 485 | UPS ETL pipeline |
| `data/intermediate/ups_rates.csv` | 1,542 | Raw extracted rates |
| `UPS-INTEGRATION-REPORT.md` | (this file) | Phase 3 documentation |

### Modified Files

| File | Change |
|------|--------|
| `data/normalized/carriers.csv` | +1 carrier (UPS) |
| `data/normalized/services.csv` | +2 services |
| `data/normalized/tariff_scopes.csv` | +56 scopes |
| `data/normalized/tariff_scope_countries.csv` | +20 countries (incomplete) |
| `data/normalized/tariff_bands.csv` | +1,541 bands |
| `data/normalized/surcharge_rules.csv` | +3 rules |

---

## Comparison: UPS vs FedEx Integration

| Aspect | FedEx | UPS |
|--------|-------|-----|
| **Zone Chart** | ✅ Complete (186 countries) | ❌ Incomplete (10 countries) |
| **Data Source** | 91-page PDF | Excel (18 sheets) |
| **Extraction Difficulty** | ⭐⭐⭐⭐ (Hard - multi-page tables) | ⭐⭐ (Easy - structured Excel) |
| **Rate Bands** | 2,055 | 1,541 |
| **Zones** | 14 (A-X) | 28 (1-703) |
| **Pricing Logic** | ✅ Working | ❌ Surcharge bugs |
| **Production Ready** | ✅ Yes | ❌ No (requires fixes) |

**Key Difference:** FedEx PDF included comprehensive zone→country chart. UPS Excel did not.

---

## Required Actions to Complete UPS Integration

### Priority 1: Critical (Blocking Production)

1. **Obtain UPS Zone Chart** ⭐⭐⭐⭐⭐
   - Contact UPS France for official zone mapping document
   - Or use public UPS zone charts (may differ from contract rates)
   - Update `UPS_ZONE_COUNTRIES_PARTIAL` in `ups.py`
   - **Effort:** 2-4 hours (manual data entry)

2. **Fix Surcharge Calculation** ⭐⭐⭐⭐
   - Debug `_calculate_surcharges()` in `engine.py`
   - Test negative percentages (-30%, -50%)
   - Verify calculations match expected results
   - **Effort:** 1-2 hours (code debugging)

### Priority 2: Enhancement (Nice to Have)

3. **Handle Multiple Package Types** ⭐⭐⭐
   - Decide strategy: cheapest rate vs user selection
   - Implement package type parameter in queries
   - **Effort:** 2-3 hours

4. **Implement Surcharge Conditions** ⭐⭐
   - Add `residential`, `delivery_frequency` parameters
   - Update CLI to accept flags
   - **Effort:** 3-4 hours

5. **Extract Additional UPS Services** ⭐
   - Expedited (sheet 05)
   - UPS Access Point (sheets 09-10)
   - Import services (sheets 11-17)
   - **Effort:** 4-6 hours (similar to current ETL)

### Priority 3: Optional (Phase 5)

6. **Unit Tests for UPS** ⭐
   - Test zone mappings
   - Test surcharge calculations
   - Test edge cases (Doc vs Pkg)
   - **Effort:** 3-4 hours

7. **Performance Optimization** ⭐
   - Deduplicate rates (choose cheapest per weight)
   - Optimize scope lookups
   - **Effort:** 2 hours

---

## Lessons Learned

### What Went Well

1. **Excel Parsing Simpler Than PDF:** Using `pandas.read_excel()` is much easier than `pdfplumber` multi-page extraction.

2. **Modular ETL Design:** Adding UPS didn't require changes to core engine - just append to normalized CSVs.

3. **Zone Structure Clear:** UPS zone headers were well-structured and easy to parse.

### Challenges

1. **Missing Zone Chart:** Unlike FedEx, UPS Excel didn't include comprehensive country mappings. This is a **major blocker**.

2. **Negative Surcharges:** Pricing engine wasn't designed for negative percentage surcharges (discounts). This reveals a design limitation.

3. **Package Type Ambiguity:** UPS differentiates Doc vs Pkg rates. Engine assumes single rate per weight. This requires architecture decision.

4. **Incomplete Excel Info:** Many zones (3, 4, 5, 6, 7, 8, 9, 10, 51, 52, 505) have no country hints in the Excel file.

### Recommendations for Future Integrations

1. **Always Request Zone Charts:** When receiving carrier rate sheets, explicitly ask for zone→country mapping document.

2. **Support Negative Surcharges:** Extend `_calculate_surcharges()` to handle both positive and negative values robustly.

3. **Package Type as Parameter:** Design engine to accept `package_type: str` parameter for carriers that differentiate.

4. **Validation Scripts:** Create automated validation that checks for missing zone mappings before marking integration "complete".

---

## Current Status

### ✅ Completed

- [x] Excel structure analysis (18 sheets identified)
- [x] Express Saver rates extraction (965 bands)
- [x] Standard rates extraction (576 bands)
- [x] Normalization to canonical schema
- [x] CSV append (all tables updated)
- [x] Surcharge rules documented (3 rules)
- [x] Partial zone mapping (10 countries)
- [x] Basic pricing tests (JP, GB)

### ⚠️ Partial / Needs Fixes

- [ ] **Zone→Country mapping** (only 5% complete)
- [ ] **Surcharge calculation** (negative percentages broken)
- [ ] **Package type handling** (Doc vs Pkg ambiguity)
- [ ] **Pricing accuracy** (results unreliable due to surcharge bugs)

### ❌ Not Started

- [ ] Additional UPS services (Expedited, Access Point, Import)
- [ ] Surcharge conditions implementation (residential, weekly)
- [ ] Unit tests for UPS
- [ ] Performance optimization (deduplication)
- [ ] Production readiness validation

---

## Conclusion

**Phase 3 Status:** ⚠️ **PARTIAL SUCCESS**

UPS ETL is complete and data is normalized, but **integration is not production-ready** due to:

1. **Missing zone mappings** (90% of countries unmapped)
2. **Broken surcharge logic** (negative percentages don't work)
3. **Ambiguous package types** (Doc vs Pkg not handled)

**Recommendation:**
- **DO NOT** use UPS pricing in production until fixes are complete
- **DO** complete Priority 1 actions (zone chart + surcharge fix)
- **CONSIDER** UPS as "data available but not reliable" until validation passes

**Next Steps:**
1. Contact UPS for official zone chart
2. Fix surcharge calculation bug
3. Re-test all mapped countries
4. Only then: commit Phase 3 and move to Phase 4 (Discord bot)

**Estimated Fix Time:** 3-6 hours (assuming UPS provides zone chart)

---

**Author:** Benjamin Belaga
**Version:** 0.3.0-alpha (UPS partial)
**Integration Date:** 2025-11-20
**Status:** ⚠️ INCOMPLETE - Requires Priority 1 fixes
