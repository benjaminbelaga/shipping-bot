# FedEx Integration Plan - Complete Rebuild from PDF Data
**Date:** 2025-11-21
**Status:** ✅ Ready to implement
**Priority:** HIGH - Corrects major coverage gaps

---

## 🎯 Executive Summary

### Problem
Previous FedEx data was **incomplete and incorrect**:
- ❌ South Korea (KR) marked as "not covered"
- ❌ Germany (DE) limited to "24kg minimum"
- ❌ Georgia (GE) marked as "not covered"
- ❌ Russia (RU) marked as "not covered"

### Solution
User provided **2 clean CSV files** extracted directly from FedEx PDF contract:
1. **fedex_export_zone_chart.csv** - 193 countries × 7 services = 1116 mappings
2. **fedex_ipe_export_rates.csv** - 861 pricing rows for IPE Export

### Coverage Verification ✅

| Country | Old Status | New Status | Zones |
|---------|-----------|------------|-------|
| **South Korea** | ❌ Not covered | ✅ **Zone B** | IPE, IP, IE, IPF, IEF |
| **Germany** | ❌ 24kg+ only | ✅ **Zone R (0.5kg+)** | IPE, IP, RE, IPF, REF |
| **Georgia** | ❌ Not covered | ✅ **Zone C** | IPE, IP, IE, IPF, IEF |
| **Russia** | ❌ Not covered | ✅ **Zone W** | IPE, IP, IE, IPF, IEF |
| Japan | ✅ Zone I | ✅ **Zone I** | All services |

---

## 📊 FedEx CSV Data Analysis

### Zone Chart (`fedex_export_zone_chart.csv`)

**Structure:**
```csv
country_name,country_iso2,product,zone,page_number
South Korea,KR,IPE,B,26
South Korea,KR,IP,B,26
South Korea,KR,IE,B,26
```

**Statistics:**
- **Total rows:** 1,116
- **Unique countries:** 193
- **Products/Services:** 7 (IPE, IP, IE, RE, IPF, IEF, REF)
- **Zones:** A-X (16+ zones)

**Data Quality:**
- ✅ ISO2 codes pre-mapped (KR, DE, GE, RU, JP all correct)
- ✅ Clean CSV format
- ⚠️ Some countries missing ISO2 (e.g., "Antigua & Barbuda") - needs manual mapping

### IPE Export Rates (`fedex_ipe_export_rates.csv`)

**Structure:**
```csv
service_code,direction,package_type,zone,min_weight_kg,max_weight_kg,price_eur,is_min_charge
FDX_IPE_EXPORT,EXPORT,Pak,B,2.0,2.0,17.33,False
FDX_IPE_EXPORT,EXPORT,Package,I,3.0,3.0,16.56,False
```

**Statistics:**
- **Total rows:** 861
- **Service:** FDX_IPE_EXPORT (International Priority Express)
- **Package types:** Envelope, Pak, Package
- **Weight range:** 0.5kg - 70kg (and per-kg bands 71-300+)
- **Zones:** A-X covered

**Data Quality:**
- ✅ `min_weight_kg`, `max_weight_kg` already parsed
- ✅ `is_min_charge` flag pre-calculated
- ✅ `price_eur` as float
- ✅ Clean, ready to import

---

## 🔧 ETL Implementation Plan

### Phase 1: FedEx Zone Mapping ETL

**Script:** `src/etl/fedex_zones.py`

**Input:** `/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_export_zone_chart.csv`

**Process:**
1. **Read zone chart CSV**
2. **Create services** (if not existing):
   ```python
   services_map = {
       'IPE': ('FDX_IPE_EXPORT', 'FedEx International Priority Express Export'),
       'IP': ('FDX_IP_EXPORT', 'FedEx International Priority Export'),
       'IE': ('FDX_IE_EXPORT', 'FedEx International Economy Export'),
       'RE': ('FDX_RE_EXPORT', 'FedEx Regional Economy Export'),
       'IPF': ('FDX_IPF_EXPORT', 'FedEx International Priority Freight Export'),
       'IEF': ('FDX_IEF_EXPORT', 'FedEx International Economy Freight Export'),
       'REF': ('FDX_REF_EXPORT', 'FedEx Regional Economy Freight Export')
   }
   ```

3. **Create tariff scopes** for each (service, zone) combination:
   ```python
   # Example: IPE × Zone B
   TariffScope(
       code='FDX_IPE_ZONE_B',
       service_id=4,  # FDX_IPE_EXPORT
       description='FedEx IPE Export - Zone B'
   )
   ```

4. **Map countries to scopes**:
   ```python
   # South Korea → FDX_IPE_ZONE_B
   TariffScopeCountry(
       scope_id=scope_id,
       country_iso2='KR'
   )
   ```

5. **Handle missing ISO2 codes**:
   - Use existing `country_aliases.csv` to resolve by country_name
   - Log warnings for unresolved countries (manual review)

**Output:**
- `tariff_scopes.csv` - ~120 new scopes (7 services × ~16 zones)
- `tariff_scope_countries.csv` - ~1,100 new country mappings

---

### Phase 2: FedEx IPE Pricing ETL

**Script:** `src/etl/fedex_ipe_rates.py`

**Input:** `/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_ipe_export_rates.csv`

**Process:**
1. **Filter package type** (V1: use "Package" only, ignore Envelope/Pak for simplicity)
2. **Map zones to scope_id**:
   ```python
   # Zone B → find scope_id for FDX_IPE_ZONE_B
   scope_id = find_scope('FDX_IPE_EXPORT', 'B')
   ```

3. **Create tariff bands**:
   ```python
   TariffBand(
       scope_id=scope_id,
       min_weight_kg=min_weight_kg,
       max_weight_kg=max_weight_kg,
       base_amount=price_eur,
       amount_per_kg=0.0,  # Fixed pricing
       is_min_charge=is_min_charge
   )
   ```

4. **Handle weight ranges** (71-99kg, 100-299kg, etc.):
   - For per-kg pricing: set `amount_per_kg` instead of `base_amount`
   - Or expand to individual 1kg bands (depends on engine capability)

**Output:**
- `tariff_bands.csv` - ~860 new pricing bands for IPE

---

### Phase 3: Extend to IP, IE, RE (Future)

**Note:** User said IP/IE/RE rates are also in the PDF but not yet extracted to CSV.

**Plan:**
1. **Reuse IPE extraction code** with different page ranges
2. **Generate:**
   - `fedex_ip_export_rates.csv`
   - `fedex_ie_export_rates.csv`
   - `fedex_re_export_rates.csv`
3. **Run same ETL** as Phase 2 for each service

**Priority:** Medium (IPE alone covers most urgent cases)

---

## 📝 Implementation Checklist

### ✅ Completed
- [x] Remove UPS Standard Ground service (doesn't exist in contract)
- [x] Verify FedEx CSV data quality
- [x] Confirm key countries coverage (KR, DE, GE, RU, JP)

### 🔄 In Progress
- [ ] Write `fedex_zones.py` ETL script
- [ ] Write `fedex_ipe_rates.py` ETL script
- [ ] Handle missing ISO2 country codes
- [ ] Test locally with Japan, South Korea, Germany queries

### ⏳ Pending
- [ ] Extract IP/IE/RE rates from PDF (or request from user)
- [ ] Deploy to production
- [ ] Update bot to announce FedEx coverage improvements
- [ ] Archive old incorrect FedEx analysis document

---

## 🧪 Testing Plan

### Test Queries (Before vs After)

| Query | Old Result | Expected New Result |
|-------|-----------|---------------------|
| `2kg South Korea` | ❌ No FedEx | ✅ FedEx IPE Zone B (~17 EUR) |
| `3kg Japan` | ✅ FedEx Zone I 16.56 EUR | ✅ Same (verify consistency) |
| `5kg Germany` | ❌ No FedEx (24kg min) | ✅ FedEx IPE Zone R |
| `1kg Georgia` | ❌ No FedEx | ✅ FedEx IPE Zone C |
| `10kg Russia` | ❌ No FedEx | ✅ FedEx IPE Zone W |

### Verification Commands

```bash
# Local testing
python3 src/cli/price_cli.py 2kg KR
python3 src/cli/price_cli.py 3kg JP
python3 src/cli/price_cli.py 5kg DE
python3 src/cli/price_cli.py 1kg GE
python3 src/cli/price_cli.py 10kg RU

# Production Discord bot
/price 2kg South Korea
/price 3kg Japan
/price 5kg Germany
/price 1kg Georgia
/price 10kg Russia
```

---

## 🚀 Deployment Plan

### Step 1: Local Development
1. Write ETL scripts
2. Run ETLs to generate new CSV data
3. Test with CLI tool
4. Verify pricing accuracy against PDF

### Step 2: Production Deployment
```bash
# Sync new data files
rsync -avz data/normalized/ yoyaku-server:/opt/pricing-engine/data/normalized/

# Restart bot
ssh yoyaku-server "pm2 restart pricing-bot"

# Monitor logs
ssh yoyaku-server "pm2 logs pricing-bot --lines 50"
```

### Step 3: Verification
1. Test all 5 queries in Discord
2. Compare results with PDF FedEx rates
3. Verify no regression on existing countries (US, CA, AU, etc.)

---

## 📚 Technical Reference

### File Locations

**Source CSV (provided by user):**
- `/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_export_zone_chart.csv`
- `/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_ipe_export_rates.csv`

**ETL Scripts (to create):**
- `src/etl/fedex_zones.py`
- `src/etl/fedex_ipe_rates.py`

**Output (normalized data):**
- `data/normalized/services.csv` (add FedEx services if missing)
- `data/normalized/tariff_scopes.csv` (add ~120 FedEx scopes)
- `data/normalized/tariff_scope_countries.csv` (add ~1,100 mappings)
- `data/normalized/tariff_bands.csv` (add ~860 IPE pricing bands)

**Documentation:**
- `docs/FEDEX-INTEGRATION-PLAN-2025-11-21.md` (this file)
- `docs/FEDEX-RAW-DATA-EXPORT-2025-11-21.txt` (old, to archive)
- `docs/FEDEX-COVERAGE-ANALYSIS-2025-11-21.md` (old, INVALID - to archive)

---

## ⚠️ Known Issues & Workarounds

### Issue 1: Missing ISO2 Codes
**Problem:** Some countries in zone chart don't have ISO2 (e.g., "Antigua & Barbuda")

**Workaround:**
```python
# Use country_aliases.csv for fallback mapping
if not iso2:
    iso2 = resolve_country_name(country_name, aliases_csv)
    if not iso2:
        logger.warning(f"⚠️ Missing ISO2 for: {country_name}")
```

### Issue 2: Package Type Selection
**Problem:** Zone chart has Envelope/Pak/Package with different pricing

**V1 Solution:** Use "Package" only (most common)

**V2 Solution:** Detect package type from order dimensions/weight and apply correct pricing

---

## 🎯 Success Criteria

- ✅ South Korea queries return FedEx options
- ✅ Germany queries work from 0.5kg (not 24kg+)
- ✅ Georgia queries return FedEx options
- ✅ Russia queries return FedEx options
- ✅ Japan pricing remains consistent (16.56 EUR for 3kg IPE Zone I)
- ✅ No regression on other countries (US, CA, AU, BR, etc.)
- ✅ Bot loads without errors
- ✅ All test queries complete in <3 seconds

---

**Next Steps:**
1. User approval of this plan
2. Implement `fedex_zones.py` ETL
3. Implement `fedex_ipe_rates.py` ETL
4. Test locally
5. Deploy to production

**Estimated time:** 2-3 hours for full ETL + testing + deployment

---

**Created by:** Benjamin Belaga
**References:** FedEx PDF contract, user-provided CSV extracts
