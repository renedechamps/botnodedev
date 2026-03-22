#!/usr/bin/env bash
# BotNode Monitoring — Setup script
# ==================================
# Run on each server to install cron + log file + Telegram config.
#
# Usage:
#   ./setup.sh stockholm   # on Stockholm server
#   ./setup.sh virginia    # on Virginia server
#
# To configure Telegram alerts:
#   1. Message @BotFather on Telegram → /newbot → follow prompts → copy token
#   2. Message your new bot, then visit:
#      https://api.telegram.org/bot<TOKEN>/getUpdates
#      to find your chat_id
#   3. Run:
#      sudo mkdir -p /etc/botnode
#      echo 'TELEGRAM_BOT_TOKEN=your_token' | sudo tee /etc/botnode/monitor.env
#      echo 'TELEGRAM_CHAT_ID=your_chat_id' | sudo tee -a /etc/botnode/monitor.env

set -euo pipefail

REGION="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$REGION" != "stockholm" && "$REGION" != "virginia" ]]; then
    echo "Usage: $0 <stockholm|virginia>"
    exit 1
fi

# Create log file
sudo touch /var/log/botnode-monitor.log
sudo chown ubuntu:ubuntu /var/log/botnode-monitor.log

# Create Telegram env dir
sudo mkdir -p /etc/botnode
if [[ ! -f /etc/botnode/monitor.env ]]; then
    echo "# Add Telegram credentials here:" | sudo tee /etc/botnode/monitor.env
    echo "# TELEGRAM_BOT_TOKEN=your_bot_token" | sudo tee -a /etc/botnode/monitor.env
    echo "# TELEGRAM_CHAT_ID=your_chat_id" | sudo tee -a /etc/botnode/monitor.env
    echo "Created /etc/botnode/monitor.env — edit with your Telegram credentials"
fi

# Make scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Install cron — run every hour at :47 (offset to avoid crowded minutes)
CRON_SCRIPT="$SCRIPT_DIR/check-from-${REGION}.sh"
CRON_LINE="47 * * * * $CRON_SCRIPT >> /var/log/botnode-monitor.log 2>&1"

( (crontab -l 2>/dev/null || true) | grep -v "check-from-" || true ; echo "$CRON_LINE") | crontab -

echo ""
echo "Setup complete for $REGION:"
echo "  Script:  $CRON_SCRIPT"
echo "  Cron:    every hour at :47"
echo "  Log:     /var/log/botnode-monitor.log"
echo "  Telegram: edit /etc/botnode/monitor.env"
echo ""
echo "Test with: $CRON_SCRIPT"
