#!/usr/bin/env bash
# BotNode Daily Stats Exporter
# =============================
# Runs once daily, exports metrics from PostgreSQL to JSON, commits to botnode-stats repo.
# Designed to run on Virginia (where the primary DB lives).

set -euo pipefail

STATS_REPO="/home/ubuntu/botnode-stats"
DATE=$(date -u '+%Y-%m-%d')
YEAR=$(date -u '+%Y')
MONTH=$(date -u '+%Y-%m')
OUTPUT_DIR="$STATS_REPO/data/$YEAR"
OUTPUT_FILE="$OUTPUT_DIR/$DATE.json"
DB_CMD="docker exec botnode_unified-db-1 psql -U botnode -t -A"

mkdir -p "$OUTPUT_DIR"

# Helper: run SQL query, return trimmed result
q() {
    $DB_CMD -c "$1" 2>/dev/null | tr -d ' '
}

# Helper: run SQL query, return full result
qf() {
    $DB_CMD -c "$1" 2>/dev/null
}

echo "Exporting stats for $DATE..."

# ─── NETWORK ───────────────────────────────────────────────
nodes_total=$(q "SELECT count(*) FROM nodes WHERE NOT is_sandbox")
nodes_sandbox=$(q "SELECT count(*) FROM nodes WHERE is_sandbox")
nodes_new_today=$(q "SELECT count(*) FROM nodes WHERE created_at::date = '$DATE' AND NOT is_sandbox")
nodes_new_sandbox_today=$(q "SELECT count(*) FROM nodes WHERE created_at::date = '$DATE' AND is_sandbox")
nodes_active_today=$(q "SELECT count(DISTINCT buyer_id) + count(DISTINCT seller_id) FROM tasks WHERE created_at::date = '$DATE'")
nodes_with_strikes=$(q "SELECT count(*) FROM nodes WHERE strikes > 0")
nodes_by_country=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT country_name, count(*) as cnt FROM nodes WHERE country_name IS NOT NULL AND NOT is_sandbox GROUP BY country_name ORDER BY cnt DESC LIMIT 15) t")

# ─── CRI ───────────────────────────────────────────────────
cri_avg=$(q "SELECT round(avg(cri_score)::numeric, 2) FROM nodes WHERE cri_score IS NOT NULL AND NOT is_sandbox")
cri_median=$(q "SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY cri_score)::numeric, 2) FROM nodes WHERE cri_score IS NOT NULL AND NOT is_sandbox")
cri_min=$(q "SELECT round(min(cri_score)::numeric, 2) FROM nodes WHERE cri_score IS NOT NULL AND NOT is_sandbox")
cri_max=$(q "SELECT round(max(cri_score)::numeric, 2) FROM nodes WHERE cri_score IS NOT NULL AND NOT is_sandbox")
cri_above_70=$(q "SELECT count(*) FROM nodes WHERE cri_score >= 70 AND NOT is_sandbox")
cri_snapshots_today=$(q "SELECT count(*) FROM cri_snapshots WHERE calculated_at::date = '$DATE'")
cri_improved_today=$(q "SELECT count(*) FROM cri_snapshots WHERE calculated_at::date = '$DATE' AND cri_after > cri_before")
cri_declined_today=$(q "SELECT count(*) FROM cri_snapshots WHERE calculated_at::date = '$DATE' AND cri_after < cri_before")
cri_avg_diversity=$(q "SELECT round(avg(unique_counterparties)::numeric, 1) FROM cri_snapshots WHERE calculated_at::date = '$DATE'")

# ─── TASKS ─────────────────────────────────────────────────
tasks_total=$(q "SELECT count(*) FROM tasks")
tasks_today=$(q "SELECT count(*) FROM tasks WHERE created_at::date = '$DATE'")
tasks_completed=$(q "SELECT count(*) FROM tasks WHERE status = 'COMPLETED'")
tasks_completed_today=$(q "SELECT count(*) FROM tasks WHERE status = 'COMPLETED' AND created_at::date = '$DATE'")
tasks_open=$(q "SELECT count(*) FROM tasks WHERE status = 'OPEN'")
tasks_disputed=$(q "SELECT count(*) FROM tasks WHERE status = 'DISPUTED'")
tasks_by_protocol=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT protocol, count(*) as cnt FROM tasks GROUP BY protocol ORDER BY cnt DESC) t")
tasks_completion_rate=$(q "SELECT CASE WHEN count(*) > 0 THEN round(100.0 * count(*) FILTER (WHERE status='COMPLETED') / count(*), 1) ELSE 0 END FROM tasks")

# ─── ESCROWS & SETTLEMENT ─────────────────────────────────
escrows_total=$(q "SELECT count(*) FROM escrows")
escrows_today=$(q "SELECT count(*) FROM escrows WHERE created_at::date = '$DATE'")
escrows_settled=$(q "SELECT count(*) FROM escrows WHERE status = 'SETTLED'")
escrows_refunded=$(q "SELECT count(*) FROM escrows WHERE status = 'REFUNDED'")
escrows_disputed=$(q "SELECT count(*) FROM escrows WHERE status = 'DISPUTED'")
escrows_pending=$(q "SELECT count(*) FROM escrows WHERE status = 'PENDING'")
settlement_rate=$(q "SELECT CASE WHEN count(*) > 0 THEN round(100.0 * count(*) FILTER (WHERE status='SETTLED') / count(*), 1) ELSE 0 END FROM escrows WHERE status != 'PENDING'")
dispute_rate=$(q "SELECT CASE WHEN count(*) > 0 THEN round(100.0 * count(*) FILTER (WHERE status='DISPUTED') / count(*), 1) ELSE 0 END FROM escrows")

# ─── ECONOMY ───────────────────────────────────────────────
tck_in_wallets=$(q "SELECT round(COALESCE(sum(balance), 0)::numeric, 2) FROM nodes")
tck_in_escrow=$(q "SELECT round(COALESCE(sum(amount), 0)::numeric, 2) FROM escrows WHERE status = 'PENDING'")
tck_moved_today=$(q "SELECT round(COALESCE(sum(abs(amount)), 0)::numeric, 2) FROM ledger_entries WHERE created_at::date = '$DATE'")
tck_avg_transaction=$(q "SELECT round(COALESCE(avg(amount), 0)::numeric, 4) FROM escrows WHERE amount > 0")
tck_max_today=$(q "SELECT round(COALESCE(max(amount), 0)::numeric, 2) FROM escrows WHERE created_at::date = '$DATE'")
tck_treasury=$(q "SELECT round(COALESCE(sum(amount), 0)::numeric, 2) FROM ledger_entries WHERE entry_type = 'CREDIT' AND note LIKE '%tax%'")

# ─── SKILLS ────────────────────────────────────────────────
skills_total=$(q "SELECT count(*) FROM skills")
skills_top_10=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT s.label, count(tk.id) as tasks FROM skills s LEFT JOIN tasks tk ON tk.skill_id = s.id GROUP BY s.label ORDER BY tasks DESC LIMIT 10) t")
skills_most_failed=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT s.label, count(tk.id) as failed FROM skills s JOIN tasks tk ON tk.skill_id = s.id WHERE tk.status = 'DISPUTED' GROUP BY s.label ORDER BY failed DESC LIMIT 5) t")
skills_never_used=$(q "SELECT count(*) FROM skills s LEFT JOIN tasks t ON t.skill_id = s.id WHERE t.id IS NULL")
skills_avg_price=$(q "SELECT round(COALESCE(avg(price_tck), 0)::numeric, 4) FROM skills")

# ─── SANDBOX ───────────────────────────────────────────────
sandbox_trades_total=$(q "SELECT count(*) FROM funnel_events WHERE event_type = 'sandbox_trade'")
sandbox_trades_today=$(q "SELECT count(*) FROM funnel_events WHERE event_type = 'sandbox_trade' AND created_at::date = '$DATE'")
sandbox_shares_total=$(q "SELECT count(*) FROM sandbox_shares")
sandbox_shares_today=$(q "SELECT count(*) FROM sandbox_shares WHERE created_at::date = '$DATE'")
sandbox_by_country=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT country_code, count(*) as cnt FROM funnel_events WHERE event_type = 'sandbox_trade' AND country_code IS NOT NULL GROUP BY country_code ORDER BY cnt DESC LIMIT 10) t")

# ─── FUNNEL & GROWTH ──────────────────────────────────────
registrations_total=$(q "SELECT count(*) FROM funnel_events WHERE event_type = 'register'")
registrations_today=$(q "SELECT count(*) FROM funnel_events WHERE event_type = 'register' AND created_at::date = '$DATE'")
early_access_total=$(q "SELECT count(*) FROM early_access_signups")
early_access_today=$(q "SELECT count(*) FROM early_access_signups WHERE created_at::date = '$DATE'")
early_access_by_type=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT agent_type, count(*) as cnt FROM early_access_signups WHERE agent_type IS NOT NULL GROUP BY agent_type ORDER BY cnt DESC) t")
funnel_by_country=$(qf "SELECT json_agg(row_to_json(t)) FROM (SELECT country_code, count(*) as cnt FROM funnel_events WHERE country_code IS NOT NULL GROUP BY country_code ORDER BY cnt DESC LIMIT 15) t")

# ─── PURCHASES & REVENUE ──────────────────────────────────
purchases_total=$(q "SELECT count(*) FROM purchases WHERE status = 'completed'")
purchases_today=$(q "SELECT count(*) FROM purchases WHERE status = 'completed' AND completed_at::date = '$DATE'")
revenue_usd_total=$(q "SELECT COALESCE(sum(price_usd_cents), 0) FROM purchases WHERE status = 'completed'")
revenue_usd_today=$(q "SELECT COALESCE(sum(price_usd_cents), 0) FROM purchases WHERE status = 'completed' AND completed_at::date = '$DATE'")
tck_sold_total=$(q "SELECT COALESCE(sum(tck_total), 0) FROM purchases WHERE status = 'completed'")
purchases_abandoned=$(q "SELECT count(*) FROM purchases WHERE status != 'completed'")

# ─── DISPUTES & QUALITY ───────────────────────────────────
disputes_today=$(q "SELECT count(*) FROM escrows WHERE status = 'DISPUTED' AND created_at::date = '$DATE'")
validator_pass=$(q "SELECT count(*) FROM validator_results WHERE result = 'pass'")
validator_fail=$(q "SELECT count(*) FROM validator_results WHERE result = 'fail'")
bounties_active=$(q "SELECT count(*) FROM bounties WHERE status = 'OPEN'")
bounties_completed=$(q "SELECT count(*) FROM bounties WHERE status = 'COMPLETED'")
bounties_total=$(q "SELECT count(*) FROM bounties")

# ─── GENESIS ───────────────────────────────────────────────
genesis_badges_awarded=$(q "SELECT count(*) FROM genesis_badge_awards")
genesis_remaining=$((200 - ${genesis_badges_awarded:-0}))

# ─── WEBHOOKS ──────────────────────────────────────────────
webhooks_total=$(q "SELECT count(*) FROM webhook_deliveries")
webhooks_today=$(q "SELECT count(*) FROM webhook_deliveries WHERE created_at::date = '$DATE'" 2>/dev/null || echo "0")

# ─── BUILD JSON ────────────────────────────────────────────
cat > "$OUTPUT_FILE" << JSONEOF
{
  "date": "$DATE",
  "exported_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "network": {
    "nodes_total": ${nodes_total:-0},
    "nodes_sandbox": ${nodes_sandbox:-0},
    "nodes_new_today": ${nodes_new_today:-0},
    "nodes_new_sandbox_today": ${nodes_new_sandbox_today:-0},
    "nodes_active_today": ${nodes_active_today:-0},
    "nodes_with_strikes": ${nodes_with_strikes:-0},
    "nodes_by_country": ${nodes_by_country:-null}
  },
  "cri": {
    "average": ${cri_avg:-null},
    "median": ${cri_median:-null},
    "min": ${cri_min:-null},
    "max": ${cri_max:-null},
    "above_70": ${cri_above_70:-0},
    "snapshots_today": ${cri_snapshots_today:-0},
    "improved_today": ${cri_improved_today:-0},
    "declined_today": ${cri_declined_today:-0},
    "avg_counterparty_diversity": ${cri_avg_diversity:-null}
  },
  "tasks": {
    "total": ${tasks_total:-0},
    "today": ${tasks_today:-0},
    "completed": ${tasks_completed:-0},
    "completed_today": ${tasks_completed_today:-0},
    "open": ${tasks_open:-0},
    "disputed": ${tasks_disputed:-0},
    "completion_rate_pct": ${tasks_completion_rate:-0},
    "by_protocol": ${tasks_by_protocol:-null}
  },
  "escrows": {
    "total": ${escrows_total:-0},
    "today": ${escrows_today:-0},
    "settled": ${escrows_settled:-0},
    "refunded": ${escrows_refunded:-0},
    "disputed": ${escrows_disputed:-0},
    "pending": ${escrows_pending:-0},
    "settlement_rate_pct": ${settlement_rate:-0},
    "dispute_rate_pct": ${dispute_rate:-0}
  },
  "economy": {
    "tck_in_wallets": ${tck_in_wallets:-0},
    "tck_in_escrow": ${tck_in_escrow:-0},
    "tck_moved_today": ${tck_moved_today:-0},
    "tck_avg_transaction": ${tck_avg_transaction:-0},
    "tck_max_today": ${tck_max_today:-0},
    "tck_treasury": ${tck_treasury:-0}
  },
  "skills": {
    "total": ${skills_total:-0},
    "never_used": ${skills_never_used:-0},
    "avg_price_tck": ${skills_avg_price:-0},
    "top_10": ${skills_top_10:-null},
    "most_failed": ${skills_most_failed:-null}
  },
  "sandbox": {
    "trades_total": ${sandbox_trades_total:-0},
    "trades_today": ${sandbox_trades_today:-0},
    "shares_total": ${sandbox_shares_total:-0},
    "shares_today": ${sandbox_shares_today:-0},
    "by_country": ${sandbox_by_country:-null}
  },
  "funnel": {
    "registrations_total": ${registrations_total:-0},
    "registrations_today": ${registrations_today:-0},
    "early_access_total": ${early_access_total:-0},
    "early_access_today": ${early_access_today:-0},
    "early_access_by_type": ${early_access_by_type:-null},
    "by_country": ${funnel_by_country:-null}
  },
  "revenue": {
    "purchases_completed": ${purchases_total:-0},
    "purchases_today": ${purchases_today:-0},
    "revenue_usd_cents_total": ${revenue_usd_total:-0},
    "revenue_usd_cents_today": ${revenue_usd_today:-0},
    "tck_sold_total": ${tck_sold_total:-0},
    "purchases_abandoned": ${purchases_abandoned:-0}
  },
  "quality": {
    "disputes_today": ${disputes_today:-0},
    "validator_pass": ${validator_pass:-0},
    "validator_fail": ${validator_fail:-0},
    "bounties_active": ${bounties_active:-0},
    "bounties_completed": ${bounties_completed:-0},
    "bounties_total": ${bounties_total:-0}
  },
  "genesis": {
    "badges_awarded": ${genesis_badges_awarded:-0},
    "remaining": ${genesis_remaining:-200}
  },
  "webhooks": {
    "total": ${webhooks_total:-0},
    "today": ${webhooks_today:-0}
  }
}
JSONEOF

# Validate JSON
python3 -m json.tool "$OUTPUT_FILE" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Invalid JSON generated"
    exit 1
fi

# Commit and push
cd "$STATS_REPO"
git add -A
git commit -m "stats: $DATE" --allow-empty 2>/dev/null || true
git push origin main 2>/dev/null || true

echo "Stats exported: $OUTPUT_FILE"
