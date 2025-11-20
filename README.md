# Shipping Price Comparator Bot

**Discord bot for real-time shipping price comparison across multiple carriers**

🤖 Discord Bot • 📦 Multi-carrier pricing • 🌍 203 countries • 🚀 Deployed on Contabo VPS

---

## 🎯 Purpose

Compare shipping prices across 4 major carriers to find the best rates for international shipping from Paris, France.

**Carriers Supported**:
- 🔴 **FedEx** (2 services, 178 countries)
- 🟠 **Spring GDS** (2 services, 37 countries)
- 🟣 **La Poste Delivengo** (1 service, 31 countries)
- 🟤 **UPS** (6 services WWE + API, 127 countries)

**Total Coverage**: 15,897 pricing bands • 203 unique countries

---

## 🚀 Deployment

**Server**: Contabo VPS
**IP**: 95.111.255.235
**Location**: `/opt/pricing-engine/`
**Platform**: Discord Bot
**Status**: 🟢 **ONLINE** (100% complete - Yoyaku Logistics Bot#8579)

---

## 📊 Current Status (2025-11-20)

### 🎉 **PRODUCTION - 100% OPERATIONAL** 🎉
- ✅ Core pricing engine (100%)
- ✅ FedEx integration (178 countries, 10,692 bands)
- ✅ Spring GDS integration (37 countries, 740 bands)
- ✅ La Poste integration (31 countries, 620 bands)
- ✅ UPS WWE CSV (6 services, 127 countries, 3,845 bands)
- ✅ **UPS API** (100%) - Real-time pricing with negotiated rates! 🎉
- ✅ **Discord Bot** (100%) - Yoyaku Logistics Bot#8579 ONLINE
- ✅ **Production Deployment** (100%) - Contabo VPS, PM2 managed
- ✅ **3 Slash Commands** - /price, /carriers, /help
- ✅ **42 Users** - 1 Discord server connected

### 🎮 How to Use (In Discord)
```
/help              → Show usage guide
/carriers          → List all 4 carriers
/price 2kg Japan   → Compare prices for 2kg to Japan
/price 5kg US carriers:fedex,ups  → Filter by carriers
```

### 📚 Documentation (3,000+ lines)
- [PRODUCTION-DEPLOYMENT-2025-11-20.md](PRODUCTION-DEPLOYMENT-2025-11-20.md) - **🎉 Complete deployment report**
- [DEPLOYMENT-STATUS-2025-11-20.md](DEPLOYMENT-STATUS-2025-11-20.md) - Pre-deployment status
- [ROADMAP.md](ROADMAP.md) - **100% complete!** 🎊
- [docs/UPS-API-INTEGRATION-GUIDE.md](docs/UPS-API-INTEGRATION-GUIDE.md) - UPS API setup
- [docs/DISCORD-BOT-SETUP.md](docs/DISCORD-BOT-SETUP.md) - Bot deployment guide

---

## 🔧 Architecture

### Core Components

```
src/
├── engine/         # Pricing calculation engine
│   ├── models.py   # Data models (Origin, Destination, PriceOffer)
│   ├── loader.py   # CSV data loader
│   └── engine.py   # Main pricing logic
├── etl/            # Data extraction pipelines
│   ├── fedex_extractor.py
│   ├── spring_extractor.py
│   ├── laposte_extractor.py
│   └── ups_all_services.py
├── integrations/   # External APIs
│   └── ups_api.py  # UPS Rating API client
└── bot/            # Discord bot (TODO)
    └── bot.py
```

### Data Model

**4-layer structure**:
1. **Carriers** - Transporter metadata (FedEx, Spring, etc.)
2. **Services** - Shipping services per carrier (FedEx IP Export, UPS Standard, etc.)
3. **Scopes** - Geographic/tariff zones per service
4. **Bands** - Weight-based pricing tiers per scope

**Format**: CSV (normalized data model in `data/normalized/`)

---

## 💻 Usage

### Pricing Engine (Python API)

```python
from src.engine.engine import PricingEngine, ORIGIN_PARIS

# Initialize engine
engine = PricingEngine(origin=ORIGIN_PARIS)

# Get all offers for destination
offers = engine.price('US', weight_kg=2.0)

# Display results
for offer in offers:
    print(f"{offer.service_label}: {float(offer.total)} EUR")
    if offer.is_suspended:
        print(f"  ⚠️ {offer.warning}")
```

### Discord Bot (Coming Soon)

```
/price 2kg USA
→ Shows all available carriers with prices

/price-api 2kg USA
→ Real-time UPS API pricing (when working)

/compare 2kg USA JP
→ Compare prices for multiple destinations

/services
→ List all carriers and coverage
```

---

## 🗂️ Data Sources

### Static CSV (Production Ready)
- **FedEx**: Excel extraction → 10,692 pricing bands
- **Spring GDS**: Excel extraction → 740 pricing bands
- **La Poste**: Excel extraction → 620 pricing bands
- **UPS WWE**: Excel extraction → 3,845 pricing bands

### API Integration (In Progress)
- **UPS Rating API**: OAuth2 + REST (blocked on error 111100)

**Source Files**:
- `data/raw/` - Original Excel files
- `data/intermediate/` - ETL processing
- `data/normalized/` - Final CSV format

---

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Git
- UPS Developer credentials (for API)
- Discord bot token (for bot)

### Setup

```bash
# Clone repository
git clone https://github.com/benjaminbelaga/shipping-bot.git
cd shipping-bot

# Install dependencies
pip install -r requirements.txt

# Configure credentials (UPS API)
cp ~/.credentials/yoyaku/api-keys/ups.env.template ~/.credentials/yoyaku/api-keys/ups.env
# Edit ups.env with your credentials

# Test pricing engine
python3 -c "
from src.engine.engine import PricingEngine, ORIGIN_PARIS
engine = PricingEngine(origin=ORIGIN_PARIS)
offers = engine.price('US', 2.0)
print(f'Found {len(offers)} offers for USA 2kg')
"
```

---

## 📚 Documentation

### Main Docs
- [ROADMAP.md](ROADMAP.md) - Project roadmap with milestones
- [STATUS-UPS-INTEGRATION.md](STATUS-UPS-INTEGRATION.md) - UPS API integration status

### UPS Specific
- [docs/UPS_SERVICES_GUIDE.md](docs/UPS_SERVICES_GUIDE.md) - Complete UPS nomenclature
- [docs/UPS_API_INTEGRATION.md](docs/UPS_API_INTEGRATION.md) - Technical API guide
- [docs/UPS_INTEGRATION_COMPLETE.md](docs/UPS_INTEGRATION_COMPLETE.md) - Full integration report

---

## ⚠️ Known Issues

### 🔴 UPS API Error 111100

**Issue**: UPS Rating API returns error "The requested service is invalid from the selected origin"

**Status**: Blocked - Investigating with UPS Developer Support

**Impact**: Cannot use real-time UPS pricing (fallback to WWE CSV working)

**Details**: See [STATUS-UPS-INTEGRATION.md](STATUS-UPS-INTEGRATION.md)

**Action Plan**:
1. Open UPS support ticket
2. Test Postman official collection
3. Try payload variations
4. Create new test account if needed

**Timeline**: 1-2 weeks for resolution

---

## 🎯 Milestones

- [x] **Phase 1**: Core engine + data integration (100%) - 2025-11-18
- [ ] **Phase 2**: UPS API resolution (50%) - Target: 2025-11-25
- [ ] **Phase 3**: Discord bot development (0%) - Target: 2025-12-01
- [ ] **Phase 4**: Production deployment (0%) - Target: 2025-12-05

**Overall Progress**: 75%

---

## 🤝 Contributing

This is a private project for business use. Not accepting external contributions.

**Developer**: Benjamin Belaga
**Contact**: ben@yoyaku.fr
**Company**: YOYAKU SARL
**Business**: Music vinyl distribution (yoyaku.io, yydistribution.fr)

---

## 📄 License

Proprietary - All Rights Reserved

---

## 🔗 Links

- **Contabo VPS**: 95.111.255.235
- **Discord**: (Bot invite link coming soon)
- **UPS Developer Portal**: https://developer.ups.com
- **Business**: https://yoyaku.io

---

**Version**: 1.0.0 (Development)
**Last Update**: 2025-11-20
**Status**: 🟡 In Development - 75% Complete
