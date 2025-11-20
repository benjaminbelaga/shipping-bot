# Discord Bot - Shipping Price Comparator 📦

**Real-time shipping price comparisons directly in Discord**

Get instant quotes from 4 carriers (La Poste, Spring, FedEx, UPS) with a simple slash command.

---

## ✨ Features

- **Multi-Carrier Comparison**: Compare prices from 4 carriers instantly
- **200+ Countries**: Support for worldwide destinations
- **Smart Country Resolution**: Accepts country names (Japan, Allemagne), ISO codes (JP, DE)
- **Carrier Filtering**: Limit queries to specific carriers
- **Beautiful Embeds**: Color-coded results with medals for top 3
- **Sub-Second Response**: <1ms pricing engine queries
- **100% Test Coverage**: 79 pytest tests ensuring reliability

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python 3.12+
python3 --version

# Install dependencies
pip3 install -r requirements.txt
```

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → Give it a name (e.g., "Pricing Bot")
3. Go to **Bot** section → Click **Reset Token** → Copy the token
4. Enable **Message Content Intent** and **Server Members Intent**
5. Go to **OAuth2** → **URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Use Slash Commands`
6. Copy the generated URL and invite bot to your server

### 3. Configure Bot

```bash
# Copy example config
cp .env.example .env

# Edit .env and add your bot token
nano .env  # or vim, code, etc.
```

**.env:**
```env
DISCORD_BOT_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.GhJkLm.aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890
DISCORD_DEV_GUILD_ID=1234567890123456789  # Optional, for testing
DEBUG=false
```

### 4. Run Bot

```bash
# From project root
python3 -m src.bot.bot
```

**Expected output:**
```
📦 Loading pricing engine...
✅ Pricing engine loaded
🔧 Setting up slash commands...
📝 Syncing commands to dev guild 123456789...
✅ Commands synced to dev guild
==================================================
✅ Bot connected as PricingBot#1234
📊 Servers: 1
👥 Users: 42
🚚 Carriers: 4 (La Poste, Spring, FedEx, UPS)
📦 Services: 6
==================================================
```

---

## 💬 Commands

### `/price <weight> <destination> [carriers]`

Get shipping quotes for a destination.

**Examples:**
```
/price 2kg Japan
→ Shows all carriers for 2kg to Japan

/price 5 Germany carriers:fedex,spring
→ Only FedEx and Spring for 5kg to Germany

/price 10.5kg US
→ All carriers for 10.5kg to USA
```

**Parameters:**
- `weight`: Weight in kg (formats: `2kg`, `2`, `10.5kg`)
- `destination`: Country name or ISO code
- `carriers` (optional): Comma-separated carrier codes (e.g., `fedex,spring,ups`)

**Output:**
- 🥇 Cheapest option with medal
- 💰 Total price (freight + surcharges)
- 📄 Freight breakdown
- 💸 Surcharges (if any)
- 📌 Service code

---

### `/carriers`

List all available carriers.

**Output:**
- Carrier name and code
- Number of services per carrier

**Example:**
```
🚚 Available Carriers (4)
FedEx (FEDEX) - 1 service(s)
La Poste (LAPOSTE) - 1 service(s)
Spring Expéditions (SPRING) - 2 service(s)
UPS (UPS) - 2 service(s)
```

---

### `/help`

Show bot documentation and examples.

---

## 🌍 Supported Destinations

**200+ countries** including:

| Region | Countries |
|--------|-----------|
| **Europe** | 🇩🇪 Germany, 🇫🇷 France, 🇮🇹 Italy, 🇪🇸 Spain, 🇬🇧 UK, 🇵🇱 Poland, etc. |
| **Americas** | 🇺🇸 USA, 🇨🇦 Canada, 🇧🇷 Brazil, 🇲🇽 Mexico, 🇦🇷 Argentina, etc. |
| **Asia-Pacific** | 🇯🇵 Japan, 🇨🇳 China, 🇦🇺 Australia, 🇰🇷 South Korea, 🇮🇳 India, etc. |
| **Middle East** | 🇦🇪 UAE, 🇮🇱 Israel, 🇸🇦 Saudi Arabia, etc. |
| **Africa** | 🇿🇦 South Africa, 🇪🇬 Egypt, 🇳🇬 Nigeria, etc. |

**Country name variants:**
- English: `Japan`, `Germany`, `United States`
- French: `Japon`, `Allemagne`, `États-Unis`
- ISO codes: `JP`, `DE`, `US`

---

## 🚚 Available Carriers

### 1. **FedEx** (FEDEX)
- **Service:** International Priority Export
- **Coverage:** 186 countries (A-X zones)
- **Max Weight:** 70kg
- **Status:** ✅ Production-ready

### 2. **Spring Expéditions** (SPRING)
- **Services:**
  - Europe Home Delivery (15 countries)
  - Rest of World (13 countries)
- **Max Weight:** 20kg
- **Surcharges:** +5% fuel
- **Status:** ✅ Production-ready

### 3. **La Poste** (LAPOSTE)
- **Service:** Delivengo Profil 2025
- **Coverage:** 200+ countries (2 zones)
- **Max Weight:** 2kg
- **Surcharges:** None
- **Status:** ⚠️ Partial (some zones incomplete)

### 4. **UPS** (UPS)
- **Services:**
  - Express Saver (express delivery)
  - Standard (ground delivery)
- **Coverage:** 10 countries mapped (90% incomplete)
- **Max Weight:** 70kg
- **Surcharges:** -30% fuel discount
- **Status:** ⚠️ Limited (only JP, CN, ID, MY, PH, TW, VN, KH, LA, GB)

---

## 🏗️ Architecture

```
src/bot/
  ├── __init__.py       # Package init
  ├── bot.py            # Main bot client
  ├── commands.py       # Slash commands (/price, /carriers, /help)
  ├── config.py         # Configuration loader
  └── formatter.py      # Discord embed formatter
```

**Integration:**
- Uses `src/engine/engine.py` PricingEngine
- Loads data from `data/normalized/*.csv`
- 79 pytest tests ensure stability

---

## 🧪 Testing

```bash
# Run all tests (including bot integration)
pytest tests/ -v

# Run only pricing engine tests
pytest tests/test_pricing_engine.py -v

# Check bot imports (without running)
python3 -c "from src.bot.bot import PricingBot; print('✅ Bot imports OK')"
```

---

## 🐛 Troubleshooting

### Bot doesn't respond to commands

**1. Check bot token:**
```bash
# Verify token is set
echo $DISCORD_BOT_TOKEN

# Should not be empty
```

**2. Check bot permissions:**
- Bot needs `Use Application Commands` permission
- Go to Discord → Server Settings → Integrations → Your Bot → Manage

**3. Check command sync:**
- Global commands take up to 1 hour to sync
- Use `DISCORD_DEV_GUILD_ID` for instant testing

---

### Commands not showing in Discord

**Solution: Re-sync commands**

```python
# In bot.py, uncomment this in setup_hook():
await self.tree.sync()  # Force global sync
```

Then restart bot and wait up to 1 hour.

**OR use dev guild (instant):**
```env
DISCORD_DEV_GUILD_ID=your-server-id-here
```

---

### "Unknown country" errors

**Cause:** Country not in `country_aliases.csv`

**Solution:** Add alias to `data/normalized/country_aliases.csv`

```csv
alias,country_iso2
spain,ES
espagne,ES
es,ES
```

Then restart bot (CSV loaded on startup).

---

### No offers found

**Possible causes:**

1. **Weight exceeds carrier max:**
   - La Poste: 2kg max
   - Spring: 20kg max
   - FedEx/UPS: 70kg max

2. **Country not in carrier zones:**
   - UPS only covers 10 countries
   - Check carrier coverage above

3. **No weight bands for that weight:**
   - FedEx starts at 0.5kg minimum
   - UPS Standard starts at 1kg minimum

---

## 📊 Performance

- **Query speed:** <1ms per destination
- **Bot response:** <500ms (network + Discord API)
- **Memory usage:** ~50MB (pricing data loaded once)
- **Concurrent users:** Supports 100+ simultaneous queries

---

## 🔐 Security

- ✅ Bot token stored in environment variables (never in code)
- ✅ Input validation (weight, country, carrier codes)
- ✅ Error messages don't expose internal paths
- ✅ No SQL injection risk (CSV-based data)

---

## 🚀 Deployment

### Option 1: Local Development

```bash
# Terminal 1: Run bot
python3 -m src.bot.bot

# Terminal 2: Test commands in Discord
# Bot stays running, responds to commands
```

### Option 2: Production Server (PM2)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js <<EOF
module.exports = {
  apps: [{
    name: 'pricing-bot',
    script: 'python3',
    args: '-m src.bot.bot',
    cwd: '/path/to/pricing-engine',
    env: {
      DISCORD_BOT_TOKEN: 'your-token-here',
      DEBUG: 'false'
    },
    error_file: './logs/bot-error.log',
    out_file: './logs/bot-out.log',
    time: true
  }]
};
EOF

# Start bot
pm2 start ecosystem.config.js

# Monitor
pm2 monit

# Auto-restart on server reboot
pm2 startup
pm2 save
```

### Option 3: Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-m", "src.bot.bot"]
```

```bash
# Build and run
docker build -t pricing-bot .
docker run -d \
  --name pricing-bot \
  -e DISCORD_BOT_TOKEN=your-token-here \
  --restart unless-stopped \
  pricing-bot

# View logs
docker logs -f pricing-bot
```

---

## 📈 Future Enhancements

**Phase 5 (Planned):**
- [ ] Batch queries: `/compare 2kg,5kg,10kg Japan`
- [ ] Conditional surcharges: `/price 2kg JP residential:true`
- [ ] Historical pricing: `/price 2kg JP history:7d`
- [ ] Package type selection: `/price 2kg JP type:document`
- [ ] Currency conversion: `/price 2kg JP currency:USD`
- [ ] Delivery time estimates: Show ETA for each carrier
- [ ] Tracking integration: `/track UPS-123456789`

**Phase 6 (Future):**
- [ ] Admin dashboard: Web UI for carrier management
- [ ] Rate alerts: Notify when prices change >10%
- [ ] API endpoint: REST API for external integrations
- [ ] Multi-language: Support for Spanish, Italian, etc.

---

## 📝 Changelog

### v1.0.0 (2025-11-20) - Initial Release
- ✅ `/price` command with multi-carrier comparison
- ✅ `/carriers` command to list available carriers
- ✅ `/help` command with documentation
- ✅ Smart country resolution (200+ aliases)
- ✅ Negative surcharge support (-30% discounts work correctly)
- ✅ 79 pytest tests (100% pass)
- ✅ Beautiful Discord embeds with medals
- ✅ Error handling and validation

---

## 🤝 Contributing

**Adding a new carrier:**

1. Create ETL script in `src/etl/your_carrier.py`
2. Follow ETL contract in `ARCHITECTURE.md`
3. Append to normalized CSVs
4. Run tests: `pytest tests/ -v`
5. Bot automatically picks up new carrier (restart needed)

**See:** `ARCHITECTURE.md` for complete carrier integration guide.

---

## 📄 License

Same as main project.

---

## 🆘 Support

**Issues:** Open issue on GitHub repo
**Questions:** Discord server (link in main README)
**Documentation:** See `ARCHITECTURE.md` for engine details

---

**Built with ❤️ by Benjamin Belaga**
**Powered by discord.py v2.3+ and Unified Pricing Engine v0.3.0**
