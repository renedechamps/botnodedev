from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

import models


MAX_GENESIS_BADGES = 200
GENESIS_BONUS_TCK = Decimal("300")


def apply_cri_floor(node: models.Node) -> None:
    """Apply the 'CRI Floor 1.0' logic for Genesis Nodes.

    Rule: If a node has a Genesis Badge, its reputation score cannot drop below 1.0
    for 180 days after its first settled transaction, unless explicitly slashed
    (strikes >= 3).

    This function should be called whenever reputation_score is updated.
    """
    if not node.has_genesis_badge or not node.first_settled_tx_at:
        return

    # Check if within 180 days window
    protection_period = timedelta(days=180)
    if datetime.utcnow() <= (node.first_settled_tx_at + protection_period):
        # Apply floor only if not banned (strikes < 3)
        if node.strikes < 3 and node.reputation_score < 1.0:
            node.reputation_score = 1.0


def check_and_award_genesis_badges(db: Session) -> None:
    """Evaluate eligible nodes and assign Genesis badges.

    This worker is invoked from settlement paths once a node records its
    first SETTLED transaction. It is designed to be **idempotent** and
    safe to call multiple times within the same process.

    Rules (summarized):
    - Only the first 200 nodes can receive a Genesis badge.
    - Eligibility: node has a non-null `first_settled_tx_at`, is linked
      via `signup_token`, and does not yet have `has_genesis_badge` set.
    - Ranking is determined by `first_settled_tx_at` (ascending).
    - Awarding a badge:
      - Set `has_genesis_badge = True`.
      - Set `genesis_rank` to the assigned rank (1..200).
      - Add 300 TCK to the node balance.
      - Insert a row into `genesis_badge_awards`.

    The caller is responsible for committing the transaction; this
    function will only `flush()` the session so that inserts/updates are
    visible within the current transaction.
    """

    print("[GenesisWorker] Checking for Genesis badges...")

    # 1) How many Genesis badges have already been awarded?
    current_count = (
        db.query(models.Node)
        .filter(models.Node.has_genesis_badge.is_(True))
        .count()
    )

    if current_count >= MAX_GENESIS_BADGES:
        # Nothing to do; cap already reached.
        print(
            f"[GenesisWorker] {current_count} badges already awarded; "
            "no slots remaining."
        )
        return

    slots_remaining = MAX_GENESIS_BADGES - current_count

    # 2) Find eligible nodes that do NOT yet have a Genesis badge.
    #    Conditions:
    #      - first_settled_tx_at IS NOT NULL
    #      - has_genesis_badge IS FALSE
    #      - signup_token IS NOT NULL (linked to early access)
    #    Ordered by first_settled_tx_at ASC to respect true arrival order.
    eligible_nodes = (
        db.query(models.Node)
        .filter(
            models.Node.first_settled_tx_at.isnot(None),
            models.Node.has_genesis_badge.is_(False),
            models.Node.signup_token.isnot(None),
        )
        .order_by(models.Node.first_settled_tx_at.asc())
        .limit(slots_remaining)
        .all()
    )

    if not eligible_nodes:
        print("[GenesisWorker] No eligible nodes found for Genesis badges.")
        return

    # 3) Award badges to the first N eligible nodes within the remaining slots.
    for idx, node in enumerate(eligible_nodes, start=1):
        rank = current_count + idx

        # Safety guard: should not happen due to LIMIT, but keep it robust.
        if rank > MAX_GENESIS_BADGES:
            break

        # Update Node state.
        node.has_genesis_badge = True
        node.genesis_rank = rank

        # Balance is a Numeric/Decimal; ensure we add a Decimal amount.
        node.balance = (node.balance or Decimal("0")) + GENESIS_BONUS_TCK
        
        # Apply CRI floor immediately upon getting badge
        apply_cri_floor(node)

        # Create log entry in GenesisBadgeAward table.
        award = models.GenesisBadgeAward(
            node_id=node.id,
            genesis_rank=rank,
            # awarded_at uses default timestamp
            # first_tx_id / badge_url can be filled later by other workers
        )
        db.add(award)

        print(
            f"[GenesisWorker] Awarded Genesis Badge #{rank} "
            f"to node {node.id}"
        )

    # Ensure all changes are pushed to the DB within the current
    # transaction. The outer caller is expected to commit.
    db.flush()
