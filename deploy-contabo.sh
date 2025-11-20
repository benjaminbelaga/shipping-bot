#!/bin/bash
# Deploy Pricing Engine Discord Bot to Contabo VPS
# Server: 95.111.255.235 (yoyaku-server)

set -e  # Exit on error

echo "🚀 Deploying Pricing Engine to Contabo..."

# Configuration
REMOTE_USER="root"
REMOTE_HOST="95.111.255.235"
REMOTE_PATH="/opt/pricing-engine"
LOCAL_PATH="$(pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if we're in the right directory
if [ ! -f "ARCHITECTURE.md" ]; then
    echo -e "${RED}❌ Error: Not in pricing-engine directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Current directory OK${NC}"

# Step 2: Run tests locally
echo -e "${YELLOW}🧪 Running tests locally...${NC}"
python3 -m pytest tests/ -v --tb=short || {
    echo -e "${RED}❌ Tests failed! Fix before deploying.${NC}"
    exit 1
}
echo -e "${GREEN}✅ All tests passed${NC}"

# Step 3: Check .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Edit .env and add your DISCORD_BOT_TOKEN${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

# Step 4: Verify SSH access
echo -e "${YELLOW}🔐 Testing SSH connection to Contabo...${NC}"
ssh -o ConnectTimeout=5 $REMOTE_USER@$REMOTE_HOST "echo 'SSH OK'" || {
    echo -e "${RED}❌ Cannot connect to Contabo. Check SSH config.${NC}"
    exit 1
}
echo -e "${GREEN}✅ SSH connection OK${NC}"

# Step 5: Create remote directory
echo -e "${YELLOW}📁 Creating remote directory...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_PATH"

# Step 6: Backup existing deployment (if exists)
echo -e "${YELLOW}💾 Backing up existing deployment...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "
    if [ -d $REMOTE_PATH/src ]; then
        timestamp=\$(date +%Y%m%d-%H%M%S)
        cp -r $REMOTE_PATH $REMOTE_PATH.backup-\$timestamp
        echo 'Backup created: $REMOTE_PATH.backup-\$timestamp'
    fi
"

# Step 7: Sync files to Contabo (excluding unnecessary files)
echo -e "${YELLOW}📤 Syncing files to Contabo...${NC}"
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude 'venv' \
    --exclude '.env.example' \
    --exclude 'deploy-contabo.sh' \
    --exclude '*.backup-*' \
    $LOCAL_PATH/ $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

echo -e "${GREEN}✅ Files synced${NC}"

# Step 8: Install dependencies on Contabo
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "
    cd $REMOTE_PATH
    python3 -m pip install -r requirements.txt
"
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 9: Setup PM2 (if not already installed)
echo -e "${YELLOW}🔧 Setting up PM2...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "
    which pm2 || npm install -g pm2
"

# Step 10: Create PM2 ecosystem file
echo -e "${YELLOW}📝 Creating PM2 config...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "
cat > $REMOTE_PATH/ecosystem.config.js <<'EOF'
module.exports = {
  apps: [{
    name: 'pricing-bot',
    script: 'python3',
    args: '-m src.bot.bot',
    cwd: '$REMOTE_PATH',
    interpreter: 'none',
    env_file: '.env',
    error_file: './logs/bot-error.log',
    out_file: './logs/bot-out.log',
    time: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000
  }]
};
EOF

    # Create logs directory
    mkdir -p $REMOTE_PATH/logs
"

# Step 11: Restart bot with PM2
echo -e "${YELLOW}🔄 Restarting bot with PM2...${NC}"
ssh $REMOTE_USER@$REMOTE_HOST "
    cd $REMOTE_PATH
    pm2 delete pricing-bot 2>/dev/null || true
    pm2 start ecosystem.config.js
    pm2 save
"

# Step 12: Show bot status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Bot Status:"
ssh $REMOTE_USER@$REMOTE_HOST "pm2 status pricing-bot"

echo ""
echo "📝 Logs:"
echo "   View logs: ssh $REMOTE_USER@$REMOTE_HOST 'pm2 logs pricing-bot'"
echo "   Error logs: $REMOTE_PATH/logs/bot-error.log"
echo "   Output logs: $REMOTE_PATH/logs/bot-out.log"

echo ""
echo "🎮 Management Commands:"
echo "   Restart: ssh $REMOTE_USER@$REMOTE_HOST 'pm2 restart pricing-bot'"
echo "   Stop: ssh $REMOTE_USER@$REMOTE_HOST 'pm2 stop pricing-bot'"
echo "   Monitor: ssh $REMOTE_USER@$REMOTE_HOST 'pm2 monit'"

echo ""
echo -e "${GREEN}🚀 Bot is now running on Contabo!${NC}"
