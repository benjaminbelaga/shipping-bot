# Pricing Engine - Architecture & Canonical Data Model

**Version:** 1.0.0
**Date:** 2025-11-20
**Author:** Benjamin Belaga

---

## Table of Contents

1. [Overview](#overview)
2. [Canonical Data Model](#canonical-data-model)
3. [ETL Contract](#etl-contract)
4. [Pricing Engine Logic](#pricing-engine-logic)
5. [Country Resolution](#country-resolution)
6. [Adding New Carriers](#adding-new-carriers)
7. [Testing Strategy](#testing-strategy)

---

## Overview

### Purpose

Unified pricing engine that compares shipping rates across multiple carriers (La Poste, Spring, FedEx, UPS, etc.) and returns the cheapest option for any `(weight, destination)` query.

### Design Principles

1. **Carrier Agnostic:** Single canonical data model for all carriers
2. **Extensible:** Add new carriers without touching core engine
3. **Fast:** In-memory engine with O(1) lookups, <1ms query time
4. **Accurate:** Handles complex pricing (zones, bands, surcharges, DDP/DAP)
5. **Maintainable:** Clear separation: ETL → Data → Engine → API

### Architecture Diagram

```
┌─────────────┐
│ Raw Data    │ PDF/Excel/CSV from carriers
│ data/raw/   │
└──────┬──────┘
       │
       │ ETL Pipeline (carrier-specific)
       ▼
┌─────────────┐
│Intermediate │ Parsed tables (carrier-specific format)
│data/inter/  │
└──────┬──────┘
       │
       │ Normalization (to canonical schema)
       ▼
┌─────────────┐
│ Normalized  │ 7 CSV files (canonical model)
│data/norm/   │ - carriers.csv
└──────┬──────┘ - services.csv
       │        - tariff_scopes.csv
       │        - tariff_scope_countries.csv
       │        - tariff_bands.csv
       │        - surcharge_rules.csv
       │        - country_aliases.csv
       │
       │ Loaded at startup
       ▼
┌─────────────┐
│   Engine    │ In-memory indexes
│ PricingEngine│ - (service, country) → scope
└──────┬──────┘ - (scope, weight) → band
       │        - (service) → surcharges
       │
       │ Query: price(2kg, "Australie")
       ▼
┌─────────────┐
│   Results   │ Sorted list of offers
│   [{...}]   │ [{carrier, service, price}, ...]
└─────────────┘
```

---

## Canonical Data Model

All ETL scripts **MUST** produce data conforming to this schema.

### 1. carriers.csv

**Purpose:** Define carriers (transporters).

**Schema:**
```csv
carrier_id, code, name, currency
1, LAPOSTE, "La Poste", EUR
2, SPRING, "Spring Expéditions", EUR
3, FEDEX, "FedEx", EUR
4, UPS, "UPS", EUR
```

**Fields:**
- `carrier_id` (int): Unique identifier
- `code` (str): Short code (UPPERCASE, no spaces)
- `name` (str): Commercial name
- `currency` (str): Base currency for tariffs (EUR, USD, etc.)

**Rules:**
- `code` must be unique
- `currency` must be ISO 4217 (EUR, USD, GBP, etc.)

---

### 2. services.csv

**Purpose:** Define carrier services (products).

**Schema:**
```csv
service_id,carrier_id,code,label,direction,origin_iso2,incoterm,service_type,max_weight_kg,volumetric_divisor,active_from,active_to
1,1,LAPOSTE_DELIVENGO,"Delivengo Profil 2025",EXPORT,FR,DAP,ECONOMY,30.0,5000,2025-02-01,
2,2,SPRING_EUROPE,"Spring Europe domicile",EXPORT,FR,DAP,ECONOMY,20.0,5000,2023-01-01,
3,3,FEDEX_IP,"FedEx International Priority Export",EXPORT,FR,DAP,EXPRESS,70.0,5000,2024-01-01,
4,4,UPS_EXPRESS_SAVER,"UPS Express Saver",EXPORT,FR,DAP,EXPRESS,70.0,5000,2023-04-22,
```

**Fields:**
- `service_id` (int): Unique identifier
- `carrier_id` (int): Foreign key to carriers
- `code` (str): Unique service code (CARRIER_PRODUCTNAME)
- `label` (str): Commercial name
- `direction` (enum): EXPORT | IMPORT | DOMESTIC
- `origin_iso2` (str): Origin country (ISO 3166-1 alpha-2)
- `incoterm` (enum): DAP | DDP
- `service_type` (enum): EXPRESS | ECONOMY | GROUND | MAIL
- `max_weight_kg` (float): Maximum weight accepted
- `volumetric_divisor` (float): For volumetric weight (default: 5000)
- `active_from` (date): Start date (YYYY-MM-DD) or empty
- `active_to` (date): End date or empty

**Rules:**
- `code` must be unique
- `direction` ∈ {EXPORT, IMPORT, DOMESTIC}
- `incoterm` ∈ {DAP, DDP}
- `service_type` ∈ {EXPRESS, ECONOMY, GROUND, MAIL}
- `origin_iso2` must be valid ISO 3166-1 alpha-2

---

### 3. tariff_scopes.csv

**Purpose:** Define tariff zones/regions for pricing.

**Schema:**
```csv
scope_id,service_id,code,description,is_catch_all
1,1,DELIVENGO_DE_BOXABLE,"Delivengo Allemagne - Boxable",False
2,1,DELIVENGO_GB_NONBOXABLE,"Delivengo UK - Non Boxable",False
3,2,SPRING_EU_DE,"Spring Europe - Allemagne",False
4,3,FDX_IP_ZONE_A,"FedEx IP - Zone A",False
5,4,UPS_EXPRESS_SAVER_ZONE_11,"UPS Express Saver - Zone 11",False
```

**Fields:**
- `scope_id` (int): Unique identifier
- `service_id` (int): Foreign key to services
- `code` (str): Unique scope code
- `description` (str): Human-readable description
- `is_catch_all` (bool): True if this scope covers unmapped countries

**Rules:**
- `code` must be unique
- One scope = one (service, zone/country, package_type) combination
- For carriers with package types (Boxable/Doc/Pkg), create separate scopes

**Examples:**
- FedEx: `FDX_IP_ZONE_A`, `FDX_IP_ZONE_B`, ..., `FDX_IP_ZONE_X`
- UPS: `UPS_EXPRESS_SAVER_ZONE_11`, `UPS_STANDARD_ZONE_4`
- Spring: `SPRING_EU_DE`, `SPRING_ROW_AU`
- La Poste: `DELIVENGO_DE_BOXABLE`, `DELIVENGO_US_ENCOMBRANT`

---

### 4. tariff_scope_countries.csv

**Purpose:** Map countries to tariff scopes.

**Schema:**
```csv
scope_id,country_iso2
1,DE
2,GB
3,DE
4,AT
4,BE
4,CH
5,CN
5,JP
5,MY
```

**Fields:**
- `scope_id` (int): Foreign key to tariff_scopes
- `country_iso2` (str): Country code (ISO 3166-1 alpha-2)

**Rules:**
- `country_iso2` must be valid ISO 3166-1 alpha-2
- One country can belong to multiple scopes (different services)
- For zone-based carriers (FedEx, UPS), generate from zone charts

**Note:** If a carrier's zone chart is incomplete, document in ETL script:
```python
# UPS Zone 11: CN, ID, JP, MY, PH, TW (from Excel)
# UPS Zone 3-10: UNKNOWN (zone chart not provided)
```

---

### 5. tariff_bands.csv

**Purpose:** Define price bands by weight.

**Schema:**
```csv
band_id,scope_id,min_weight_kg,max_weight_kg,base_amount,amount_per_kg,is_min_charge
1,1,0.0,0.1,3.90,0.0,False
2,1,0.1,0.25,4.00,0.0,False
3,1,0.0,30.0,3.35,2.6,False
4,4,0.5,0.5,12.50,0.0,False
5,4,1.0,1.0,14.20,0.0,False
```

**Fields:**
- `band_id` (int): Unique identifier
- `scope_id` (int): Foreign key to tariff_scopes
- `min_weight_kg` (float): Minimum weight (inclusive)
- `max_weight_kg` (float): Maximum weight (inclusive)
- `base_amount` (float): Base price (EUR)
- `amount_per_kg` (float): Price per kg (EUR/kg)
- `is_min_charge` (bool): True if this is a minimum charge

**Pricing Formula:**
```python
freight = base_amount + (amount_per_kg * weight_kg)
```

**Rules:**
- For fixed-price bands (Spring, UPS): `min_weight_kg = max_weight_kg`, `amount_per_kg = 0`
- For linear pricing (La Poste): `base_amount = tarif_pli`, `amount_per_kg = tarif_kg`
- Bands must cover all weights from 0 to `service.max_weight_kg`

**Examples:**
- **Fixed:** `min=2.0, max=2.0, base=32.44, per_kg=0` → 2kg costs 32.44 EUR
- **Linear:** `min=0, max=30, base=3.35, per_kg=2.6` → 5kg costs 3.35 + 2.6*5 = 16.35 EUR

---

### 6. surcharge_rules.csv

**Purpose:** Define surcharges/discounts applied to freight.

**Schema:**
```csv
surcharge_id,service_id,name,kind,basis,value,conditions
1,2,SPRING_EU_FUEL,PERCENT,FREIGHT,5.0,{}
2,4,UPS_FUEL_DISCOUNT,PERCENT,FREIGHT,-30.0,{}
3,4,UPS_RESIDENTIAL_DISCOUNT,PERCENT,FREIGHT,-50.0,{"delivery_type":"residential"}
4,4,UPS_WEEKLY_SURCHARGE,PERCENT,FREIGHT,100.0,{"delivery_frequency":"weekly"}
```

**Fields:**
- `surcharge_id` (int): Unique identifier
- `service_id` (int): Foreign key to services
- `name` (str): Surcharge name
- `kind` (enum): PERCENT | FIXED | PER_KG
- `basis` (enum): FREIGHT | TOTAL
- `value` (float): Percentage (5.0 = +5%) or amount (EUR)
- `conditions` (json): Optional conditions for application

**Calculation:**
```python
if kind == "PERCENT":
    surcharge = freight * (value / 100)
elif kind == "FIXED":
    surcharge = value
elif kind == "PER_KG":
    surcharge = value * weight_kg

if basis == "TOTAL":
    # Apply to running total (freight + previous surcharges)
    pass
```

**Rules:**
- `kind` ∈ {PERCENT, FIXED, PER_KG}
- `basis` ∈ {FREIGHT, TOTAL}
- Negative `value` = discount (e.g., UPS -30% fuel discount)
- Apply surcharges in order: negative first, then positive
- Final total must be >= 0

**Conditions Format:**
```json
{}                                    // Always apply
{"delivery_type": "residential"}     // Only if residential
{"duty_mode": "DDP"}                 // Only if DDP
{"delivery_frequency": "weekly"}     // Only if weekly delivery
```

---

### 7. country_aliases.csv

**Purpose:** Resolve country names/codes to ISO2.

**Schema:**
```csv
alias,country_iso2
australie,AU
australia,AU
au,AU
royaume-uni,GB
uk,GB
great britain,GB
états-unis,US
usa,US
us,US
etats-unis,US
allemagne,DE
germany,DE
de,DE
```

**Fields:**
- `alias` (str): Country name/code (lowercase, normalized)
- `country_iso2` (str): ISO 3166-1 alpha-2 code

**Rules:**
- `alias` must be unique (after normalization)
- Normalization: lowercase, strip accents, remove punctuation
- Include:
  - ISO2 codes (DE, FR, US)
  - English names (Germany, United States)
  - French names (Allemagne, États-Unis)
  - Common variations (USA, UK, GB)
  - Partial matches OK ("australi" → AU)

**Usage:**
```python
def resolve_country(query: str) -> str:
    normalized = normalize_string(query)  # lowercase, strip accents
    return ALIASES.get(normalized, None)
```

---

## ETL Contract

Every carrier ETL **MUST** implement:

### File Structure

```
src/etl/
  <carrier>.py         # ETL script (e.g., fedex.py, ups.py)
data/raw/
  <carrier>/           # Raw files (PDF, Excel, CSV)
data/intermediate/
  <carrier>_*.csv      # Intermediate parsed data
data/normalized/
  carriers.csv         # Append to these
  services.csv
  tariff_scopes.csv
  tariff_scope_countries.csv
  tariff_bands.csv
  surcharge_rules.csv
```

### Required Functions

```python
def extract_raw() -> pd.DataFrame:
    """
    Read carrier's PDF/Excel/CSV and parse to intermediate DataFrames.

    Returns:
        DataFrame(s) with carrier-specific structure

    Examples:
        - fedex_zone_chart.csv: country_iso2, zone
        - fedex_ip_rates.csv: zone, weight_kg, price_eur
        - ups_rates.csv: service, zone, weight_kg, price_eur, package_type
    """
    pass

def normalize_to_canonical():
    """
    Transform intermediate data to canonical schema.
    Append to normalized CSV files:
    - carriers.csv
    - services.csv
    - tariff_scopes.csv
    - tariff_scope_countries.csv
    - tariff_bands.csv
    - surcharge_rules.csv (if applicable)

    Rules:
    - Determine next IDs by reading existing CSVs
    - Append mode (never overwrite)
    - Validate schema before writing
    - Log warnings for incomplete data (e.g., missing zone mappings)
    """
    pass
```

### Normalization Rules

1. **Weights:** Always in kg (float)
2. **Prices:** Always in EUR (float)
3. **Countries:** Always ISO 3166-1 alpha-2 (e.g., FR, DE, US)
4. **Dates:** YYYY-MM-DD or empty string
5. **Booleans:** True/False (Python) or 1/0 (CSV)

### Handling Incomplete Data

If zone chart is incomplete:

```python
# Document in code
INCOMPLETE_ZONES = {
    "zone_3": [],  # Countries unknown
    "zone_4": [],  # TODO: Obtain official zone chart
}

print(f"⚠️  WARNING: {len(mapped)} countries mapped, ~{190-len(mapped)} missing")
print(f"   Action required: Obtain official zone chart from carrier")
```

Commit with warning in message:
```
[FEAT] Carrier X integration - PARTIAL ⚠️
- Zone mappings: 5% complete (10/200 countries)
- Required: Official zone chart
```

---

## Pricing Engine Logic

### Query Flow

```python
def price(dest: str, weight_kg: float) -> List[PriceOffer]:
    # 1. Resolve country
    dest_iso2 = country_resolver.resolve(dest)  # "Australie" → "AU"

    # 2. For each service
    offers = []
    for service in all_services:
        # 3. Find scope (zone)
        scope = find_scope(service.id, dest_iso2)
        if not scope:
            continue  # Service doesn't cover this country

        # 4. Find band (weight)
        band = find_band(scope.id, weight_kg)
        if not band:
            continue  # Weight out of range

        # 5. Calculate freight
        freight = band.base_amount + band.amount_per_kg * weight_kg

        # 6. Calculate surcharges
        surcharges = calculate_surcharges(service.id, freight, weight_kg, conditions)

        # 7. Total
        total = freight + surcharges

        offers.append(PriceOffer(
            carrier=service.carrier,
            service=service,
            freight=freight,
            surcharges=surcharges,
            total=total
        ))

    # 8. Sort by total (cheapest first)
    return sorted(offers, key=lambda o: o.total)
```

### Scope Selection

Priority order:
1. **Specific country:** `scope_countries[country_iso2] = scope_id`
2. **Catch-all zone:** `scope.is_catch_all = True`
3. **Not found:** Skip service

### Band Selection

For a given scope and weight:
1. Find all bands where `min_weight_kg <= weight <= max_weight_kg`
2. If multiple matches, pick first (bands should not overlap)
3. If no match, service doesn't support this weight

### Surcharge Calculation

**Order of operations:**
1. Apply **negative surcharges** (discounts) first
2. Apply **positive surcharges** (fees) second
3. Ensure `total >= 0`

**Algorithm:**
```python
def calculate_surcharges(service_id, freight, weight_kg, conditions):
    rules = get_applicable_rules(service_id, conditions)

    # Sort: negative first, positive last
    rules.sort(key=lambda r: r.value)

    total_surcharge = 0
    running_total = freight

    for rule in rules:
        if rule.kind == "PERCENT":
            amount = running_total * (rule.value / 100)
        elif rule.kind == "FIXED":
            amount = rule.value
        elif rule.kind == "PER_KG":
            amount = rule.value * weight_kg

        total_surcharge += amount

        if rule.basis == "TOTAL":
            running_total += amount  # Compound

    return total_surcharge
```

**Example: UPS Express Saver (JP 2kg)**
```
Freight: 32.44 EUR
Surcharge 1: -30% (Fuel) = -9.73 EUR
Surcharge 2: -50% (Residential, if applicable) = -16.22 EUR (on original freight)
Total: 32.44 - 9.73 = 22.71 EUR (without residential)
```

---

## Country Resolution

### Implementation

```python
class CountryResolver:
    def __init__(self, aliases_file: str):
        self.aliases = load_aliases_csv(aliases_file)
        # Pre-compute normalized map
        self.map = {
            self.normalize(alias): iso2
            for alias, iso2 in self.aliases
        }

    def normalize(self, s: str) -> str:
        """Lowercase, remove accents, strip punctuation"""
        s = s.lower()
        s = unidecode(s)  # États-Unis → etats-unis
        s = re.sub(r'[^\w\s]', '', s)  # Remove punctuation
        s = s.strip()
        return s

    def resolve(self, query: str) -> Optional[str]:
        """
        Resolve country query to ISO2.

        Examples:
            "Australie" → "AU"
            "2kg Australie" → "AU" (extracts country from query)
            "États-Unis" → "US"
            "usa" → "US"
            "DE" → "DE"
        """
        # Extract country from query (remove weight patterns)
        country = re.sub(r'\d+(\.\d+)?\s*(kg|g|lb)', '', query, flags=re.I).strip()

        normalized = self.normalize(country)

        # Exact match
        if normalized in self.map:
            return self.map[normalized]

        # Partial match (e.g., "australi" → "australie")
        for alias, iso2 in self.map.items():
            if normalized in alias or alias in normalized:
                return iso2

        return None
```

### Alias Coverage

Minimum 200 aliases covering:
- ISO2 codes: DE, FR, US, AU, ...
- English names: Germany, France, United States, Australia, ...
- French names: Allemagne, États-Unis, Australie, ...
- Common variations: USA, UK, GB, ...
- Partial matches: "australi", "etatsunis", ...

---

## Adding New Carriers

### Checklist

1. **Obtain data files**
   - Rate sheets (PDF, Excel, CSV)
   - Zone charts (if applicable)
   - Surcharge documentation
   - Service descriptions

2. **Create ETL script**
   ```bash
   touch src/etl/<carrier>.py
   ```

3. **Implement functions**
   - `extract_raw()` → intermediate CSV
   - `normalize_to_canonical()` → append to normalized CSVs

4. **Test**
   ```bash
   python3 src/etl/<carrier>.py
   python3 src/cli/price_cli.py 2kg AU  # Should include new carrier
   ```

5. **Document**
   - Create `<CARRIER>-INTEGRATION-REPORT.md`
   - Update `README.md`
   - Document limitations (if any)

6. **Commit**
   ```bash
   git add -A
   git commit -m "[FEAT] <Carrier> integration - <status>"
   ```

### Example: Adding Chronopost

```python
# src/etl/chronopost.py
def extract_raw():
    pdf_path = "data/raw/chronopost/tarifs_2025.pdf"
    # ... parse PDF
    df = pd.DataFrame({
        'country': [...],
        'weight_kg': [...],
        'price_eur': [...]
    })
    df.to_csv("data/intermediate/chronopost_rates.csv")
    return df

def normalize_to_canonical():
    # Read intermediate
    df = pd.read_csv("data/intermediate/chronopost_rates.csv")

    # Determine next IDs
    next_carrier_id = get_next_id("data/normalized/carriers.csv")
    next_service_id = get_next_id("data/normalized/services.csv")
    # ...

    # Append to carriers.csv
    append_csv("data/normalized/carriers.csv", {
        'carrier_id': next_carrier_id,
        'code': 'CHRONOPOST',
        'name': 'Chronopost',
        'currency': 'EUR'
    })

    # ... append to other CSVs

if __name__ == "__main__":
    extract_raw()
    normalize_to_canonical()
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_country_resolver.py
def test_resolve_french_names():
    resolver = CountryResolver("data/normalized/country_aliases.csv")
    assert resolver.resolve("Australie") == "AU"
    assert resolver.resolve("États-Unis") == "US"
    assert resolver.resolve("Allemagne") == "DE"

def test_resolve_english_names():
    assert resolver.resolve("Australia") == "AU"
    assert resolver.resolve("United States") == "US"
    assert resolver.resolve("Germany") == "DE"

def test_resolve_iso2_codes():
    assert resolver.resolve("AU") == "AU"
    assert resolver.resolve("US") == "US"
    assert resolver.resolve("DE") == "DE"

def test_resolve_partial_matches():
    assert resolver.resolve("australi") == "AU"
    assert resolver.resolve("2kg Australie") == "AU"

# tests/test_surcharges.py
def test_positive_surcharge():
    freight = 100.0
    rules = [SurchargeRule(kind="PERCENT", value=5.0)]
    assert calculate_surcharges(freight, rules) == 5.0

def test_negative_surcharge():
    freight = 100.0
    rules = [SurchargeRule(kind="PERCENT", value=-30.0)]
    assert calculate_surcharges(freight, rules) == -30.0

def test_mixed_surcharges():
    freight = 100.0
    rules = [
        SurchargeRule(kind="PERCENT", value=-30.0),  # -30 EUR
        SurchargeRule(kind="PERCENT", value=5.0)     # +5 EUR on original
    ]
    # Total: 100 - 30 + 5 = 75 EUR
    assert calculate_surcharges(freight, rules) == -25.0

# tests/test_pricing_engine.py
def test_fedex_cheaper_than_spring_for_usa():
    offers = engine.price(dest="US", weight_kg=2.0)
    assert offers[0].carrier.code == "FEDEX"
    assert offers[0].total < 15.0  # FedEx ~14.46 EUR

def test_spring_cheaper_than_laposte_for_germany():
    offers = engine.price(dest="DE", weight_kg=0.5)
    assert offers[0].carrier.code == "SPRING"
    assert offers[0].total < 5.0  # Spring ~4.41 EUR
```

### Integration Tests

```python
def test_complete_workflow():
    # 1. Run all ETLs
    subprocess.run(["python3", "src/etl/laposte.py"])
    subprocess.run(["python3", "src/etl/spring.py"])
    subprocess.run(["python3", "src/etl/fedex.py"])
    subprocess.run(["python3", "src/etl/ups.py"])

    # 2. Load engine
    engine = PricingEngine.from_csv_folder("data/normalized")

    # 3. Test queries
    offers_au = engine.price("AU", 2.0)
    assert len(offers_au) >= 2
    assert offers_au[0].total > 0

    offers_de = engine.price("DE", 0.5)
    assert len(offers_de) >= 2
```

### Validation Tests

```python
def test_all_countries_mapped():
    """Verify all tariff_scopes have at least one country mapped"""
    scopes = load_csv("data/normalized/tariff_scopes.csv")
    countries = load_csv("data/normalized/tariff_scope_countries.csv")

    for scope in scopes:
        if not scope.is_catch_all:
            assert scope.id in countries.scope_id.values, \
                f"Scope {scope.code} has no countries mapped"

def test_no_overlapping_bands():
    """Verify tariff_bands don't overlap within a scope"""
    bands = load_csv("data/normalized/tariff_bands.csv")

    for scope_id in bands.scope_id.unique():
        scope_bands = bands[bands.scope_id == scope_id]
        # Check for overlaps
        for i, band1 in scope_bands.iterrows():
            for j, band2 in scope_bands.iterrows():
                if i >= j:
                    continue
                # Bands shouldn't overlap
                assert not (band1.min_weight_kg < band2.max_weight_kg and
                           band2.min_weight_kg < band1.max_weight_kg)
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Engine load time | < 200ms | ~100ms |
| Query latency (single) | < 1ms | <1ms |
| Query throughput | > 10,000/sec | ~15,000/sec |
| Memory usage | < 50MB | ~15MB |
| Countries supported | 200+ | 200+ |
| Carriers supported | 10+ | 4 (2 complete, 2 partial) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-20 | Initial architecture document |

---

**Author:** Benjamin Belaga
**Repository:** `benjaminbelaga/pricing-engine`
**License:** Proprietary
