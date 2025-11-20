# Pricing Engine Unifié - YOYAKU

**Moteur de tarification unifié pour transporteurs internationaux**

## Architecture

```
┌─────────────────┐
│   Bot Discord   │
│   CLI Tool      │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│      Pricing Engine (RAM)       │
│  - Country resolver             │
│  - Scope matcher                │
│  - Band selector                │
│  - Surcharge calculator         │
└────────┬────────────────────────┘
         │
         v
┌─────────────────────────────────┐
│   Normalized Data (CSV/JSON)    │
│  - carriers.csv                 │
│  - services.csv                 │
│  - tariff_scopes.csv            │
│  - tariff_bands.csv             │
│  - surcharge_rules.csv          │
└────────┬────────────────────────┘
         │
         v
┌─────────────────────────────────┐
│       ETL Scripts               │
│  - laposte.py                   │
│  - spring.py                    │
│  - fedex.py                     │
│  - ups.py                       │
└─────────────────────────────────┘
```

## Transporteurs Supportés

| Transporteur | Service(s) | Max Weight | Status |
|-------------|-----------|------------|--------|
| **La Poste** | Delivengo Profil | 2 kg | 🚧 Dev |
| **Spring** | Europe / Reste du monde | 20 kg | 🚧 Dev |
| **FedEx** | IP Export, IE Export, IPE | 70 kg | 📋 Planned |
| **UPS** | Standard, Express Saver | 70 kg | 📋 Planned |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run ETL for La Poste
python src/etl/laposte.py

# Test pricing
python src/cli/price_cli.py 2 AU
```

## Data Model

### Prix = `base_amount + amount_per_kg * weight_kg`

### Tables

1. **carriers** - Transporteurs (FEDEX, UPS, LAPOSTE, SPRING)
2. **services** - Produits tarifaires (DELIVENGO_2025, SPRING_EU_HOME...)
3. **tariff_scopes** - Zones tarifaires (ZONE_A, US, EUROPE1...)
4. **tariff_scope_countries** - Mapping scope → pays ISO2
5. **tariff_bands** - Tranches de poids et prix
6. **surcharge_rules** - Fuel, DDP/DAP, résidentiel...

## Development

```bash
# Structure
pricing-engine/
  data/
    raw/           # PDFs/XLSX originaux (gitignored)
    intermediate/  # CSV bruts extraits
    normalized/    # Modèle canonique
  src/
    etl/          # Scripts d'extraction
    engine/       # Moteur de pricing
    cli/          # Interface ligne de commande
  tests/          # Tests unitaires
```

## Roadmap

- [x] Architecture design
- [ ] ETL La Poste Delivengo
- [ ] ETL Spring Expéditions
- [ ] ETL FedEx International
- [ ] ETL UPS
- [ ] Pricing engine core
- [ ] CLI tool
- [ ] Discord bot integration
- [ ] Tests & validation

---

**Author:** Benjamin Belaga
**Version:** 0.1.0-dev
**Last Updated:** 2025-11-20
