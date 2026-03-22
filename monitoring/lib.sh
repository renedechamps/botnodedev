#!/usr/bin/env bash
# BotNode Monitoring — Shared functions
# ======================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

LOG_FILE="/var/log/botnode-monitor.log"
ALERT_BUFFER=""
HAS_ERRORS=false

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || echo "$msg" >&2
    echo "$msg"
}

alert() {
    local msg="$1"
    ALERT_BUFFER="${ALERT_BUFFER}${msg}\n"
    HAS_ERRORS=true
    log "ALERT: $msg"
}

ok() {
    log "OK: $1"
}

send_telegram() {
    local message="$1"
    if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
        log "WARN: Telegram not configured — alert not sent"
        return 1
    fi
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=Markdown" \
        --max-time 10 > /dev/null 2>&1
}

flush_alerts() {
    local origin="$1"
    if [[ "$HAS_ERRORS" == true ]]; then
        local header="*BotNode Alert* — from ${origin}\n$(date '+%Y-%m-%d %H:%M UTC')\n\n"
        local full_msg="${header}${ALERT_BUFFER}"
        send_telegram "$(echo -e "$full_msg")"
        log "Alerts sent via Telegram"
    else
        log "All checks passed from ${origin}"
    fi
}

check_http() {
    local url="$1"
    local label="${2:-$url}"
    local response
    response=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" --max-time "$((MAX_RESPONSE_TIME_MS / 1000))" "$url" 2>&1)
    local code=$(echo "$response" | awk '{print $1}')
    local time_s=$(echo "$response" | awk '{print $2}')

    if [[ "$code" -ge 200 && "$code" -lt 400 ]]; then
        ok "$label — HTTP $code (${time_s}s)"
        return 0
    else
        alert "$label — HTTP $code (expected 2xx/3xx)"
        return 1
    fi
}

check_api_health() {
    local response
    response=$(curl -s --max-time 10 "$API_HEALTH_URL" 2>&1)
    local code=$?
    if [[ $code -ne 0 ]]; then
        alert "API health endpoint unreachable"
        return 1
    fi

    local status
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    if [[ "$status" == "healthy" || "$status" == "ok" ]]; then
        ok "API health — status: healthy"
        return 0
    else
        alert "API health — status: $status (response: $response)"
        return 1
    fi
}

check_ssh() {
    local host="$1"
    local label="$2"
    if ssh $SSH_OPTS "$SSH_USER@$host" "echo ok" > /dev/null 2>&1; then
        ok "$label SSH — reachable"
        return 0
    else
        alert "$label SSH — unreachable"
        return 1
    fi
}

check_remote_containers() {
    local host="$1"
    local label="$2"
    shift 2
    local expected=("$@")

    local running
    running=$(ssh $SSH_OPTS "$SSH_USER@$host" "docker ps --format '{{.Names}}:{{.Status}}'" 2>&1)
    if [[ $? -ne 0 ]]; then
        alert "$label — could not list Docker containers"
        return 1
    fi

    local all_ok=true
    for container in "${expected[@]}"; do
        local status
        status=$(echo "$running" | grep "^${container}:" | head -1)
        if [[ -z "$status" ]]; then
            alert "$label — container \`$container\` not running"
            all_ok=false
        elif echo "$status" | grep -q "(unhealthy)"; then
            alert "$label — container \`$container\` unhealthy"
            all_ok=false
        else
            ok "$label — $container running"
        fi
    done
    $all_ok
}

check_local_containers() {
    local label="$1"
    shift
    local expected=("$@")

    local all_ok=true
    for container in "${expected[@]}"; do
        local status
        status=$(docker ps --filter "name=$container" --format '{{.Names}}:{{.Status}}' 2>/dev/null | head -1)
        if [[ -z "$status" ]]; then
            alert "$label — container \`$container\` not running"
            all_ok=false
        elif echo "$status" | grep -q "(unhealthy)"; then
            alert "$label — container \`$container\` unhealthy"
            all_ok=false
        else
            ok "$label — $container running"
        fi
    done
    $all_ok
}

restart_container() {
    local host="$1"
    local container="$2"
    local label="$3"
    log "REMEDIATE: Attempting restart of $container on $label"

    local result
    if [[ "$host" == "local" ]]; then
        result=$(docker restart "$container" 2>&1)
    else
        result=$(ssh $SSH_OPTS "$SSH_USER@$host" "docker restart $container" 2>&1)
    fi

    if [[ $? -eq 0 ]]; then
        log "REMEDIATE: $container restarted successfully on $label"
        return 0
    else
        alert "$label — failed to restart \`$container\`: $result"
        return 1
    fi
}

check_replication_lag() {
    local primary_host="$1"
    local lag
    lag=$(ssh $SSH_OPTS "$SSH_USER@$primary_host" \
        "docker exec botnode_unified-db-1 psql -U botnode -t -c \"SELECT COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn), -1) FROM pg_stat_replication LIMIT 1;\"" 2>&1)

    lag=$(echo "$lag" | tr -d ' ')
    if [[ "$lag" == "-1" || -z "$lag" ]]; then
        alert "Replication — no active replica connected to primary"
        return 1
    elif [[ "$lag" =~ ^[0-9]+$ && "$lag" -gt "$MAX_REPLICATION_LAG_BYTES" ]]; then
        local lag_mb=$((lag / 1048576))
        alert "Replication lag: ${lag_mb}MB (threshold: $((MAX_REPLICATION_LAG_BYTES / 1048576))MB)"
        return 1
    else
        ok "Replication lag: ${lag} bytes"
        return 0
    fi
}
