# Discord Bot Setup & Deployment Guide

**Status:** 🚀 READY TO DEPLOY
**Date:** 2025-11-20
**Author:** Benjamin Belaga

---

## 📋 Overview

The Pricing Engine Discord Bot is **100% code complete** and ready for deployment. This guide covers:
1. Discord App creation & token
2. Local testing
3. Production deployment on Contabo VPS

---

## 🎮 Step 1: Create Discord Bot Application

### 1.1 Create Application

1. Go to https://discord.com/developers/applications
2. Click **"New Application"**
3. Name: `YOYAKU Shipping Bot` (or your preference)
4. Click **"Create"**

### 1.2 Configure Bot

1. Go to **"Bot"** tab (left sidebar)
2. Click **"Reset Token"** → Copy the token (save it securely!)
3. Enable these **Privileged Gateway Intents**:
   - ✅ **Message Content Intent** (required for commands)
   - ✅ **Server Members Intent** (optional, for user count)

### 1.3 Configure OAuth2

1. Go to **"OAuth2"** → **"URL Generator"**
2. Select **Scopes**:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Select **Bot Permissions**:
   - ✅ Send Messages
   - ✅ Send Messages in Threads
   - ✅ Embed Links
   - ✅ Use Slash Commands
4. Copy the generated URL at the bottom

### 1.4 Invite Bot to Your Server

1. Open the URL from step 1.3 in your browser
2. Select your Discord server
3. Click **"Authorize"**
4. Complete CAPTCHA

**Result:** Bot should now appear in your server (offline until deployed)

---

## 🔑 Step 2: Configure Credentials

### 2.1 Create Discord Credentials File

```bash
# Create Discord credentials
cat > ~/.credentials/yoyaku/api-keys/discord.env <<'EOF'
# Discord Bot Token
# From: https://discord.com/developers/applications
DISCORD_BOT_TOKEN=your-bot-token-here

# Optional: Development Guild ID (for faster command sync during testing)
# Get by right-clicking your Discord server → Copy Server ID
# Leave empty for production (global commands)
DISCORD_DEV_GUILD_ID=

# Optional: Enable debug logging
DEBUG=false
EOF
```

### 2.2 Update Token

```bash
# Edit the file and paste your bot token
nano ~/.credentials/yoyaku/api-keys/discord.env

# Replace 'your-bot-token-here' with the token from Step 1.2
```

**Security Note:** Never commit this file to Git! Already in `.gitignore`.

### 2.3 Load Credentials

```bash
# Test loading credentials
source ~/.credentials/yoyaku/api-keys/discord.env
echo $DISCORD_BOT_TOKEN  # Should show your token

# Add to your shell startup (optional)
echo "source ~/.credentials/yoyaku/api-keys/discord.env" >> ~/.bashrc
```

---

## 🧪 Step 3: Local Testing

### 3.1 Setup Local Environment

```bash
cd ~/repos/pricing-engine

# Create .env file for local testing
cp .env.example .env

# Edit .env and add your Discord token
nano .env
```

**`.env` file:**
```bash
DISCORD_BOT_TOKEN=your-token-here
DISCORD_DEV_GUILD_ID=your-server-id  # Optional, for faster testing
DEBUG=true
```

### 3.2 Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Key packages:
# - discord.py (Discord bot library)
# - requests (HTTP requests)
# - python-dotenv (env vars)
```

### 3.3 Run Tests

```bash
# Run unit tests
python3 -m pytest tests/ -v

# Should see:
# ====== test session starts ======
# tests/test_engine.py::test_basic_pricing PASSED
# tests/test_loader.py::test_load_carriers PASSED
# ...
# ====== 15 passed in 1.23s ======
```

### 3.4 Start Bot Locally

```bash
# Method 1: Direct execution
python3 -m src.bot.bot

# Method 2: Using run script (if exists)
python3 run_bot.py

# Expected output:
# 🚀 Starting Discord bot...
# 📦 Loading pricing engine...
# ✅ Pricing engine loaded (origin: Paris)
# 🔧 Setting up slash commands...
# ✅ Commands synced to dev guild
# ==================================================
# ✅ Bot connected as YOYAKU Shipping Bot#1234
# 📊 Servers: 1
# 👥 Users: 42
# 🚚 Carriers: 4 (La Poste, Spring, FedEx, UPS)
# 📦 Services: 11
# ==================================================
```

### 3.5 Test Commands in Discord

Go to your Discord server and test:

```
/help
→ Should show help embed with all commands

/carriers
→ Should list 4 carriers (FedEx, Spring, La Poste, UPS)

/price 2kg Japan
→ Should show shipping quotes sorted by price

/price 5kg Germany carriers:fedex,ups
→ Should show filtered results (only FedEx and UPS)
```

**Troubleshooting:**
- **Commands not appearing:** Wait 5-10 minutes (global sync) or use `DISCORD_DEV_GUILD_ID` for instant sync
- **Bot offline:** Check token is correct, check firewall
- **No results:** Check data files exist in `data/` directory

---

## 🚀 Step 4: Production Deployment (Contabo VPS)

### 4.1 Pre-Deployment Checklist

```bash
# 1. Ensure all tests pass
python3 -m pytest tests/ -v

# 2. Verify .env file exists
ls -la .env

# 3. Check SSH access to Contabo
ssh yoyaku-server "echo 'SSH OK'"

# 4. Verify pricing data files
ls -lh data/*.csv
# Should see: carriers.csv, services.csv, scopes.csv, bands.csv
```

### 4.2 Deploy to Contabo

```bash
cd ~/repos/pricing-engine

# Run deployment script (fully automated)
./deploy-contabo.sh

# Script will:
# 1. Run local tests
# 2. Create .env if missing
# 3. Backup existing deployment
# 4. Sync files via rsync
# 5. Install Python dependencies
# 6. Setup PM2 process manager
# 7. Start bot with auto-restart
# 8. Show status & logs
```

**Expected Output:**
```
🚀 Deploying Pricing Engine to Contabo...
✅ Current directory OK
🧪 Running tests locally...
✅ All tests passed
🔐 Testing SSH connection to Contabo...
✅ SSH connection OK
📁 Creating remote directory...
💾 Backing up existing deployment...
📤 Syncing files to Contabo...
✅ Files synced
📦 Installing Python dependencies...
✅ Dependencies installed
🔧 Setting up PM2...
📝 Creating PM2 config...
🔄 Restarting bot with PM2...
✅ Deployment complete!

📊 Bot Status:
┌────┬────────────────┬─────────────┬─────────┬─────────┬──────────┐
│ id │ name           │ mode        │ status  │ cpu     │ memory   │
├────┼────────────────┼─────────────┼─────────┼─────────┼──────────┤
│ 0  │ pricing-bot    │ fork        │ online  │ 0.2%    │ 45.2 MB  │
└────┴────────────────┴─────────────┴─────────┴─────────┴──────────┘

🚀 Bot is now running on Contabo!
```

### 4.3 Verify Production Deployment

```bash
# Check bot status
ssh yoyaku-server "pm2 status pricing-bot"

# View real-time logs
ssh yoyaku-server "pm2 logs pricing-bot"

# Check bot in Discord
# Bot should appear ONLINE in your server
# Commands should work globally (all servers)
```

### 4.4 Production Management Commands

```bash
# View logs
ssh yoyaku-server "pm2 logs pricing-bot --lines 50"

# Restart bot
ssh yoyaku-server "pm2 restart pricing-bot"

# Stop bot
ssh yoyaku-server "pm2 stop pricing-bot"

# Monitor resources (CPU, memory)
ssh yoyaku-server "pm2 monit"

# View error logs
ssh yoyaku-server "tail -f /opt/pricing-engine/logs/bot-error.log"

# View output logs
ssh yoyaku-server "tail -f /opt/pricing-engine/logs/bot-out.log"
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | ✅ Yes | - | Discord bot token from Developer Portal |
| `DISCORD_DEV_GUILD_ID` | ❌ No | None | Guild ID for instant command sync (testing only) |
| `DEBUG` | ❌ No | `false` | Enable debug logging |

### Bot Settings (config.py)

- **Command Prefix:** `!` (not used for slash commands)
- **Embed Color:** `0x3498db` (blue)
- **Max Offers:** `10` per query
- **Intents:** Message Content, Guilds

### PM2 Configuration

**File:** `/opt/pricing-engine/ecosystem.config.js`

```javascript
{
  name: 'pricing-bot',
  script: 'python3 -m src.bot.bot',
  cwd: '/opt/pricing-engine',
  autorestart: true,
  max_restarts: 10,
  min_uptime: '10s',
  restart_delay: 4000
}
```

---

## 📊 Bot Commands Reference

### `/price <weight> <destination> [carriers]`

Get shipping quotes for a destination.

**Parameters:**
- `weight` (required): Weight with or without unit (e.g., `2kg`, `5`, `10.5kg`)
- `destination` (required): Country name or ISO code (e.g., `Japan`, `DE`, `Allemagne`)
- `carriers` (optional): Filter by carriers (e.g., `fedex,spring`)

**Examples:**
```
/price 2kg Japan
→ Shows all carriers for 2kg to Japan

/price 5 Germany carriers:fedex
→ Shows only FedEx quotes for 5kg to Germany

/price 10.5kg US carriers:ups,fedex
→ Shows UPS and FedEx quotes for 10.5kg to USA
```

**Output:**
- 🥇 🥈 🥉 Top 3 offers with medal emojis
- 💰 Total price (EUR)
- 📄 Freight breakdown
- ➕/💸 Surcharges (if any)
- 📌 Service code
- 🚚 Carrier name

### `/carriers`

List all available shipping carriers.

**Output:**
- Carrier name and code
- Number of services per carrier
- Total carrier count

**Example:**
```
🚚 Available Carriers
Total: 4 carriers

**FedEx** (`FEDEX`)
2 service(s)

**Spring GDS** (`SPRING`)
2 service(s)

**La Poste** (`LAPOSTE`)
1 service(s)

**UPS** (`UPS`)
6 service(s)
```

### `/help`

Show bot usage guide with examples and supported countries.

**Output:**
- Command descriptions
- Usage examples
- Supported countries (200+)
- Weight formats
- Carrier filtering

---

## 🐛 Troubleshooting

### Bot Not Responding to Commands

**Check:**
1. Bot is online in Discord (green status)
2. Bot has correct permissions (Send Messages, Embed Links)
3. Commands are synced (`pm2 logs pricing-bot | grep "Commands synced"`)
4. No errors in logs (`pm2 logs pricing-bot --err`)

**Fix:**
```bash
# Restart bot to re-sync commands
ssh yoyaku-server "pm2 restart pricing-bot"

# Wait 5-10 minutes for global sync
# Or use DISCORD_DEV_GUILD_ID for instant sync
```

### "No Offers Found" Error

**Check:**
1. Country name is valid (use `/carriers` to check coverage)
2. Weight is within limits (0.1kg - 70kg)
3. Pricing data files exist (`ls /opt/pricing-engine/data/*.csv`)

**Fix:**
```bash
# Re-deploy data files
./deploy-contabo.sh
```

### High CPU/Memory Usage

**Check:**
```bash
ssh yoyaku-server "pm2 monit"
```

**Normal Usage:**
- CPU: 0.1% - 0.5% (idle), 1-5% (active queries)
- Memory: 40-60 MB

**If higher:**
- Check for memory leaks in logs
- Restart bot: `pm2 restart pricing-bot`

### Bot Crashes on Startup

**Check logs:**
```bash
ssh yoyaku-server "pm2 logs pricing-bot --err --lines 100"
```

**Common issues:**
- Missing .env file → Re-deploy
- Invalid bot token → Check `DISCORD_BOT_TOKEN`
- Missing dependencies → `pip install -r requirements.txt`

---

## 📈 Monitoring & Maintenance

### Daily Health Check

```bash
# Quick status check
ssh yoyaku-server "pm2 status pricing-bot && pm2 logs pricing-bot --lines 10"
```

**Expected:**
- Status: `online`
- Uptime: Days/weeks
- Restarts: 0 (or very low)
- No errors in recent logs

### Weekly Maintenance

1. **Update pricing data** (if CSVs changed)
```bash
cd ~/repos/pricing-engine
# Update data/*.csv files
./deploy-contabo.sh  # Re-deploy
```

2. **Review logs for errors**
```bash
ssh yoyaku-server "pm2 logs pricing-bot --err --lines 100 | grep -i error"
```

3. **Check bot uptime**
```bash
ssh yoyaku-server "pm2 info pricing-bot | grep uptime"
```

### Monthly Tasks

1. **Rotate logs** (if too large)
```bash
ssh yoyaku-server "pm2 flush pricing-bot"
```

2. **Update dependencies**
```bash
cd ~/repos/pricing-engine
pip install --upgrade -r requirements.txt
./deploy-contabo.sh
```

3. **Review Discord analytics** (Developer Portal)
   - Command usage statistics
   - Error rates
   - Active servers

---

## 🔐 Security Best Practices

### Token Security

1. ✅ **NEVER** commit `.env` to Git
2. ✅ Store token in `~/.credentials/yoyaku/api-keys/discord.env`
3. ✅ Use encrypted credentials for team sharing
4. ✅ Rotate token if compromised

### Bot Permissions

1. ✅ Grant **minimum required** permissions only
2. ✅ Never grant Admin permissions
3. ✅ Review permissions periodically

### Server Access

1. ✅ Use SSH keys (not passwords)
2. ✅ Restrict PM2 access to authorized users
3. ✅ Monitor access logs

---

## 📚 Additional Resources

- **Discord.py Documentation:** https://discordpy.readthedocs.io/
- **Discord Developer Portal:** https://discord.com/developers/applications
- **PM2 Documentation:** https://pm2.keymetrics.io/docs/usage/quick-start/
- **Pricing Engine Architecture:** `ARCHITECTURE.md`
- **UPS API Integration:** `docs/UPS-API-INTEGRATION-GUIDE.md`

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Discord application created
- [ ] Bot token obtained and saved
- [ ] Bot invited to Discord server
- [ ] `discord.env` created with token
- [ ] Local testing passed
- [ ] All unit tests pass

### Deployment
- [ ] SSH access to Contabo verified
- [ ] `deploy-contabo.sh` executed successfully
- [ ] Bot shows "online" status in PM2
- [ ] Bot appears online in Discord
- [ ] Commands work in Discord (`/help`, `/carriers`, `/price`)

### Post-Deployment
- [ ] Logs reviewed for errors
- [ ] Response times acceptable (<3s)
- [ ] Test multiple destinations (US, JP, DE, FR)
- [ ] Monitor CPU/memory usage
- [ ] Document any issues

---

**Deployment Date:** _________________
**Deployed By:** Benjamin Belaga
**Server:** Contabo VPS (95.111.255.235)
**Bot Version:** 1.0.0
**Status:** 🚀 PRODUCTION READY
