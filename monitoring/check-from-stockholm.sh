#!/usr/bin/env bash
# BotNode Monitor — Run from Stockholm, checks Virginia + public endpoints
# ========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

log "=== Stockholm monitor starting ==="

# 1. Public endpoints (web + API)
check_api_health
for url in "${WEB_URLS[@]}"; do
    check_http "$url"
done

# 2. Virginia SSH reachability
check_ssh "$VIRGINIA_IP" "Virginia"

# 3. Virginia Docker containers
if ! check_remote_containers "$VIRGINIA_IP" "Virginia" "${VIRGINIA_CONTAINERS[@]}"; then
    log "REMEDIATE: Attempting to restart failed Virginia containers..."
    for container in "${VIRGINIA_CONTAINERS[@]}"; do
        status=$(ssh $SSH_OPTS "$SSH_USER@$VIRGINIA_IP" "docker ps --filter name=$container --format '{{.Status}}'" 2>/dev/null)
        if [[ -z "$status" ]] || echo "$status" | grep -q "(unhealthy)"; then
            restart_container "$VIRGINIA_IP" "$container" "Virginia"
            sleep 5
        fi
    done
fi

# 4. PostgreSQL replication (check from primary on Virginia)
check_replication_lag "$VIRGINIA_IP"

# 5. Local Stockholm containers
check_local_containers "Stockholm" "${STOCKHOLM_CONTAINERS[@]}"

# Send alerts if any
flush_alerts "Stockholm"

log "=== Stockholm monitor complete ==="
