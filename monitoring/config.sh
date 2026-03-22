#!/usr/bin/env bash
# BotNode Cross-Region Monitoring — Configuration
# ================================================
# Shared config for both Stockholm and Virginia monitors.
# Telegram credentials are loaded from /etc/botnode/monitor.env on each server.

# --- Servers ---
VIRGINIA_IP="35.173.22.56"
STOCKHOLM_IP="16.16.245.200"
SSH_USER="ubuntu"
SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o BatchMode=yes"

# --- Endpoints ---
API_HEALTH_URL="https://botnode.io/health"
WEB_URLS=(
    "https://botnode.io"
    "https://agenticeconomy.dev"
    "https://renedechamps.com"
)

# --- Docker containers expected on Virginia ---
VIRGINIA_CONTAINERS=(
    "botnode_unified-api-1"
    "botnode_unified-db-1"
    "botnode_unified-task-runner-1"
    "botnode_unified-redis-1"
    "botnode_unified-pgbouncer-1"
)

# --- Docker containers expected on Stockholm ---
STOCKHOLM_CONTAINERS=(
    "botnode_unified-api-1"
    "botnode_unified-db-1"
    "botnode_unified-task-runner-1"
    "botnode_unified-redis-1"
)

# --- Thresholds ---
MAX_REPLICATION_LAG_BYTES=10485760  # 10MB — alert if replica is behind more than this
MAX_RESPONSE_TIME_MS=5000           # 5s — alert if HTTP response takes longer

# --- Telegram (loaded from env file) ---
TELEGRAM_ENV="/etc/botnode/monitor.env"
if [[ -f "$TELEGRAM_ENV" ]]; then
    source "$TELEGRAM_ENV"
fi
# Expected vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
