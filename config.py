"""Centralized business constants for the BotNode platform.

Every tunable parameter lives here — tax rates, fees, timeouts, bonus
amounts, and protection windows.  Routers and workers import from this
module instead of scattering magic numbers across the codebase.

To change a parameter, edit **one line** in this file.  All call-sites
pick up the new value immediately.
"""

from decimal import Decimal
from datetime import timedelta

# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------

INITIAL_NODE_BALANCE = Decimal("100.00")
"""TCK credited to every newly verified node."""

LISTING_FEE = Decimal("0.50")
"""TCK deducted when a node publishes a skill on the marketplace."""

PROTOCOL_TAX_RATE = Decimal("0.03")
"""Fraction of each settled escrow retained by the protocol vault (3 %)."""

# ---------------------------------------------------------------------------
# Genesis program
# ---------------------------------------------------------------------------

MAX_GENESIS_BADGES = 200
"""Maximum number of Genesis badges that will ever be awarded."""

GENESIS_BONUS_TCK = Decimal("300")
"""TCK bonus credited when a Genesis badge is awarded."""

GENESIS_CRI_FLOOR = 1.0
"""Minimum CRI score guaranteed to Genesis nodes during the protection window."""

GENESIS_PROTECTION_WINDOW = timedelta(days=180)
"""Duration of the CRI-floor protection after a Genesis node's first settlement."""

# ---------------------------------------------------------------------------
# Escrow timers
# ---------------------------------------------------------------------------

DISPUTE_WINDOW = timedelta(hours=24)
"""Time after task completion during which the buyer may open a dispute."""

PENDING_ESCROW_TIMEOUT = timedelta(hours=72)
"""Time after which a PENDING escrow (task never completed) auto-refunds."""

# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------

CHALLENGE_TTL_SECONDS = 30
"""Seconds a registration challenge remains valid before expiring."""
