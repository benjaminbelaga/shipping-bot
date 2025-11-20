# Next Steps - Pricing Engine

## ✅ Phase 1 Complete (2025-11-20)

**Implemented:**
- ✅ Base architecture & data model
- ✅ ETL La Poste Delivengo
- ✅ ETL Spring Europe + Reste du monde
- ✅ Country resolver (50+ pays, 100+ alias)
- ✅ Pricing engine core
- ✅ CLI tool
- ✅ Tests validés (AU, US, DE, IT)

**Stats:**
- 2 carriers (La Poste, Spring)
- 3 services
- 37 scopes
- 501 tariff bands
- 2 surcharge rules

---

## 🎯 Phase 2: FedEx International (Pending)

### Objectif
Ajouter FedEx International Priority Export depuis France

### Sources
- `data/raw/FEDEX Courtesy-Net-Rates-15358183-English (2).pdf` (91 pages)
  - Services: IP Export, IE Export, IPE Export
  - Zones A-X (Europe, Monde)
  - Poids: 0.5-70kg (+ per-kg rates >71kg)

### Tasks
1. **Zone Charts Extraction**
   - Page ~22+: "France FedEx International Export Zone Chart"
   - Mapping pays → zones (A, B, C, ..., W, X)
   - ~200 pays à mapper

2. **Rate Tables Extraction**
   - Pages 9-13: IP Export Weight/Zone grids
   - 0.5kg - 70kg par pallier 0.5kg
   - Zones A-X (colonnes)

3. **Per-kg Rates (>71kg)**
   - Tables "Per-kilogram rates" en fin de section
   - Zones A/C/E/H, B/D/F/G/I/T/X, R/S/U/V/W
   - Poids: 71-99kg, 100-299kg, 300-499kg, 500kg+

4. **ETL Implementation**
   ```python
   # src/etl/fedex.py
   def extract_zone_chart(pdf, page_start, page_end):
       # Parse country → zone mapping
       pass

   def extract_rate_table(pdf, page_index, service_code):
       # Parse weight/zone grid
       pass

   def extract_perkg_rates(pdf, page_index):
       # Parse per-kg rates tables
       pass
   ```

5. **Normalization**
   - Carrier: FedEx (id=3)
   - Services: FDX_IP_EXPORT, FDX_IE_EXPORT, FDX_IPE_EXPORT
   - Scopes: ZONE_A, ZONE_B, ..., ZONE_X (per service)
   - Bands: ~1400 (20 zones × 70 poids) + per-kg ranges

**Estimated Complexity:** ⭐⭐⭐⭐ (4/5)
- PDF parsing complex (multi-page tables)
- Zone chart long (200+ pays)
- Many bands to normalize

---

## 🎯 Phase 3: UPS Standard/Express (Pending)

### Objectif
Ajouter UPS Standard et Express Saver depuis France

### Sources
- `data/raw/PROPOSITION TARIFAIRE YOYAKU 2023.xlsx`
- `data/raw/Proposition tarifaire YOYAKU.pptx`

### Tasks
1. **Excel Parsing**
   - Identifier les feuilles (Standard, Express Saver)
   - Grilles Zone × Poids

2. **Zone Mapping**
   - Définir zones UPS (Europe, Monde, etc.)
   - Mapper pays → zones

3. **Surcharges UPS**
   - Fuel: -30% (remise)
   - Residential: -50%
   - Weekly service charge: +100%

4. **ETL Implementation**
   ```python
   # src/etl/ups.py
   import pandas as pd

   def extract_ups_rates(xlsx_path, sheet_name):
       df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
       # Parse zone/weight grid
       pass
   ```

**Estimated Complexity:** ⭐⭐⭐ (3/5)
- Excel parsing simple (pandas)
- Zones à définir
- Surcharges avec conditions

---

## 🎯 Phase 4: Discord Bot Integration (Pending)

### Objectif
Intégrer le moteur dans le bot Discord existant

### Implementation
```python
# Dans le bot Discord
from pricing_engine.src.engine.engine import PricingEngine

engine = PricingEngine()

@client.event
async def on_message(message):
    if message.content.startswith("!price "):
        # Parse "!price 2kg AU"
        query = message.content[7:]  # "2kg AU"
        weight, country = parse_query(query)

        offers = engine.price(country, weight)

        if not offers:
            await message.reply("❌ Aucun tarif trouvé")
            return

        # Format réponse
        lines = [f"**Tarifs pour {weight}kg vers {country}**"]
        for offer in offers[:5]:  # Top 5
            lines.append(
                f"- {offer.carrier_name} – {offer.service_label}: "
                f"**{float(offer.total):.2f} {offer.currency} HT**"
            )

        await message.reply("\n".join(lines))
```

**Tasks:**
1. Adapter parser de requête (Discord vs CLI)
2. Formater réponse pour Discord (embeds)
3. Gérer erreurs user-friendly
4. Ajouter commandes: `!carriers`, `!help`

**Estimated Complexity:** ⭐⭐ (2/5)

---

## 🎯 Phase 5: Optimizations & Polish

### Features
- [ ] Volumetric weight calculation (L×W×H / 5000)
- [ ] DDP/DAP surcharges (Spring page 2 tables)
- [ ] Cache engine in memory (bot startup)
- [ ] Unit tests (pytest)
- [ ] Performance benchmarks
- [ ] Additional country aliases
- [ ] Multi-currency support (EUR, USD)

### Nice-to-Have
- [ ] Web API (FastAPI)
- [ ] Admin dashboard (edit rates)
- [ ] Historical price tracking
- [ ] Carrier comparison charts

---

## 📊 Roadmap

| Phase | Tasks | Status | ETA |
|-------|-------|--------|-----|
| Phase 1 | Architecture + La Poste + Spring | ✅ Done | 2025-11-20 |
| Phase 2 | FedEx IP Export | 📋 Planned | TBD |
| Phase 3 | UPS Standard/Express | 📋 Planned | TBD |
| Phase 4 | Discord Bot | 📋 Planned | TBD |
| Phase 5 | Optimizations | 📋 Planned | TBD |

---

## 🤔 Questions for User

1. **FedEx Priority:**
   - Quels services FedEx prioriser? (IP Export, IE Export, IPE Export?)
   - Toutes les zones (A-X) ou subset?

2. **UPS:**
   - L'Excel contient quelles feuilles exactement?
   - Y a-t-il un zone chart ou faut-il le définir?

3. **Discord Bot:**
   - Repo du bot existant?
   - Format de requête préféré? (`!price 2kg AU` ou `2kg Australie` direct?)

4. **Linear Project Management:**
   - Créer un projet Linear "Pricing Engine" avec ces sprints?
   - Assigner certaines tâches à Yoann (dev externe)?

---

**Version:** 0.1.0-alpha
**Author:** Benjamin Belaga
**Date:** 2025-11-20
