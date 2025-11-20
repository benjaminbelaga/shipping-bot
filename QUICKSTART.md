# Quick Start Guide - Pricing Engine

## 🚀 Installation

```bash
cd ~/repos/pricing-engine
pip install -r requirements.txt
```

## 📊 Run ETL Scripts

### La Poste Delivengo

```bash
python3 src/etl/laposte.py
```

**Output:**
- `data/intermediate/laposte_delivengo_raw.csv` - Données brutes extraites
- `data/normalized/carriers.csv` - Transporteur LAPOSTE
- `data/normalized/services.csv` - Service DELIVENGO_2025
- `data/normalized/tariff_scopes.csv` - 8 scopes (DE, GB, US, ZONE1, ZONE2...)
- `data/normalized/tariff_bands.csv` - 8 bands (formule: base + per_kg * weight)

### Spring Expéditions

```bash
python3 src/etl/spring.py
```

**Output:**
- `data/intermediate/spring_raw.csv` - 493 rows (Europe + Reste du monde)
- Adds SPRING carrier
- Adds 2 services: SPRING_EU_HOME, SPRING_ROW_HOME
- Adds 29 scopes (par pays: DE, IT, AU, US, etc.)
- Adds 493 bands (17 tranches de poids par pays)
- Adds 2 surcharges: SPRING_EU_FUEL, SPRING_ROW_FUEL (5%)

## 💻 CLI Usage

### Basic Queries

```bash
# Australie
python3 src/cli/price_cli.py 2kg Australie

# États-Unis
python3 src/cli/price_cli.py 2kg US

# Allemagne
python3 src/cli/price_cli.py 500g DE

# Italie
python3 src/cli/price_cli.py 1kg Italie
```

### Supported Formats

```bash
2kg AU              # ISO2 code
2 kg Australie      # Nom français
0.5 australia       # Nom anglais (case-insensitive)
500g DE             # Grammes (convertis automatiquement)
1.5kg "États-Unis"  # Accents supportés
```

## 📈 Example Output

```
======================================================================
🔍 Query: 2.0kg → Australie
======================================================================

✅ 2 offers found (sorted by price):

1. La Poste - Delivengo Profil 2025
   💰 TOTAL: 25.75 EUR HT
      └─ Fret: 25.75 EUR
      └─ Scope: DELIVENGO_ZONE2_ENCOMBRANT (0.0-2.0kg)

2. Spring Expéditions - Spring Reste du monde domicile
   💰 TOTAL: 34.55 EUR HT
      └─ Fret: 32.90 EUR
      └─ Surcharges: 1.65 EUR
      └─ Scope: SPRING_ROW_AU (1.5-2.0kg)

======================================================================
🏆 BEST OFFER: La Poste - Delivengo Profil 2025
   25.75 EUR HT
======================================================================
```

## 🧪 Python API

```python
from src.engine.engine import PricingEngine

engine = PricingEngine()

# Get offers
offers = engine.price("Australie", 2.0)

# Best offer
best = offers[0]
print(f"{best.carrier_name}: {float(best.total):.2f} {best.currency}")
```

## 📁 Data Model

### Pricing Formula

```
price = base_amount + amount_per_kg * weight_kg
total = freight + surcharges
```

### Tables

1. **carriers** - Transporteurs (LAPOSTE, SPRING)
2. **services** - Produits tarifaires (DELIVENGO_2025, SPRING_EU_HOME...)
3. **tariff_scopes** - Zones tarifaires (pays ou groupes de pays)
4. **tariff_scope_countries** - Mapping scope → pays ISO2
5. **tariff_bands** - Tranches de poids et prix
6. **surcharge_rules** - Règles de surcharges (fuel, DDP/DAP...)

## 🎯 Current Status

✅ **Implemented:**
- La Poste Delivengo (8 destinations, 0-2kg)
- Spring Europe (15 pays, 17 tranches 100g-20kg)
- Spring Reste du monde (14 pays, 17 tranches)
- Country resolver (50+ pays, 100+ alias)
- Pricing engine (scope matching, band selection, surcharges)
- CLI tool

⏳ **Pending:**
- FedEx International Priority Export (70+ destinations, zones A-X)
- UPS Standard/Express Saver (zones, grilles poids)
- Discord bot integration
- Additional country mappings
- DDP/DAP surcharges (Spring)
- Volumetric weight calculation

## 🔧 Development

### Add New Carrier

1. Create ETL script in `src/etl/`
2. Extract rates to `data/intermediate/`
3. Normalize to canonical schema in `data/normalized/`
4. Run ETL: `python3 src/etl/your_carrier.py`
5. Test: `python3 src/cli/price_cli.py 2kg AU`

### Add Country Alias

Edit `src/engine/country_resolver.py`:

```python
ALIASES = {
    ...
    "nouveaualias": "XX",
}
```

## 📝 Next Steps

1. **FedEx ETL** - Extract zone charts + rate tables from PDF
2. **UPS ETL** - Parse Excel grids
3. **Discord Bot** - Integrate engine with bot (parsing "2kg Australie")
4. **Tests** - Unit tests for edge cases
5. **Performance** - Benchmark with 100+ services

---

**Version:** 0.1.0-alpha
**Author:** Benjamin Belaga
**Date:** 2025-11-20
