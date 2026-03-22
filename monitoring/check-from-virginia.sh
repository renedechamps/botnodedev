#!/usr/bin/env bash
# BotNode Monitor — Run from Virginia, checks Stockholm + public endpoints
# ========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

log "=== Virginia monitor starting ==="

# 1. Public endpoints (web + API)
check_api_health
for url in "${WEB_URLS[@]}"; do
    check_http "$url"
done

# 2. Stockholm SSH reachability
check_ssh "$STOCKHOLM_IP" "Stockholm"

# 3. Stockholm Docker containers
if ! check_remote_containers "$STOCKHOLM_IP" "Stockholm" "${STOCKHOLM_CONTAINERS[@]}"; then
    log "REMEDIATE: Attempting to restart failed Stockholm containers..."
    for container in "${STOCKHOLM_CONTAINERS[@]}"; do
        status=$(ssh $SSH_OPTS "$SSH_USER@$STOCKHOLM_IP" "docker ps --filter name=$container --format '{{.Status}}'" 2>/dev/null)
        if [[ -z "$status" ]] || echo "$status" | grep -q "(unhealthy)"; then
            restart_container "$STOCKHOLM_IP" "$container" "Stockholm"
            sleep 5
        fi
    done
fi

# 4. Local Virginia containers
check_local_containers "Virginia" "${VIRGINIA_CONTAINERS[@]}"

# 5. PostgreSQL replication
check_replication_lag "localhost"

# Send alerts if any
flush_alerts "Virginia"

log "=== Virginia monitor complete ==="
