from dataclasses import dataclass


@dataclass
class TierDef:
    upper_bound: int
    fee_per_tx: float


@dataclass
class TierBreakdown:
    tier_number: int
    lower_bound: int
    upper_bound: int | None  # None = unlimited (beyond last tier)
    fee_per_tx: float
    txs_applied: int
    subtotal: float


def calculate_billing(total_txs: int, tiers: list[TierDef]) -> float:
    """
    Marginal (progressive) tiered billing.

    Example with tiers [(1_000_001, 0.01), (5_000_001, 0.007)]:
      - First 1_000_001 txs billed at 0.01
      - Txs from 1_000_002 to 5_000_001 billed at 0.007
    """
    sorted_tiers = sorted(tiers, key=lambda t: t.upper_bound)
    remaining = total_txs
    prev_bound = 0
    total = 0.0

    for tier in sorted_tiers:
        if remaining <= 0:
            break
        band_size = tier.upper_bound - prev_bound
        applied = min(remaining, band_size)
        total += applied * tier.fee_per_tx
        remaining -= applied
        prev_bound = tier.upper_bound

    # Any txs beyond the last tier use the last tier's rate
    if remaining > 0 and sorted_tiers:
        total += remaining * sorted_tiers[-1].fee_per_tx

    return round(total, 6)


def total_to_bill(total_txs: int, tiers: list[TierDef], min_fee: float = 750.0) -> float:
    """Returns max(calculated_billing, min_monthly_fee)."""
    calculated = calculate_billing(total_txs, tiers)
    return round(max(calculated, min_fee), 4)


def calculate_billing_breakdown(
    total_txs: int, tiers: list[TierDef], min_fee: float = 750.0
) -> dict:
    """Returns a tier-by-tier breakdown plus totals."""
    sorted_tiers = sorted(tiers, key=lambda t: t.upper_bound)
    remaining = total_txs
    prev_bound = 0
    breakdown: list[TierBreakdown] = []

    for i, tier in enumerate(sorted_tiers, start=1):
        if remaining <= 0:
            breakdown.append(TierBreakdown(
                tier_number=i,
                lower_bound=prev_bound + 1,
                upper_bound=tier.upper_bound,
                fee_per_tx=tier.fee_per_tx,
                txs_applied=0,
                subtotal=0.0,
            ))
            prev_bound = tier.upper_bound
            continue
        band_size = tier.upper_bound - prev_bound
        applied = min(remaining, band_size)
        subtotal = round(applied * tier.fee_per_tx, 6)
        breakdown.append(TierBreakdown(
            tier_number=i,
            lower_bound=prev_bound + 1,
            upper_bound=tier.upper_bound,
            fee_per_tx=tier.fee_per_tx,
            txs_applied=applied,
            subtotal=subtotal,
        ))
        remaining -= applied
        prev_bound = tier.upper_bound

    # Overflow beyond last tier
    if remaining > 0 and sorted_tiers:
        last = sorted_tiers[-1]
        subtotal = round(remaining * last.fee_per_tx, 6)
        breakdown.append(TierBreakdown(
            tier_number=len(sorted_tiers) + 1,
            lower_bound=prev_bound + 1,
            upper_bound=None,
            fee_per_tx=last.fee_per_tx,
            txs_applied=remaining,
            subtotal=subtotal,
        ))

    calculated = round(sum(b.subtotal for b in breakdown), 6)
    total = round(max(calculated, min_fee), 4)
    return {
        "tiers": breakdown,
        "calculated": calculated,
        "min_fee": min_fee,
        "total": total,
        "min_fee_applied": total > calculated,
    }


# Default contract tiers from the Excel (Contract sheet)
DEFAULT_TIERS = [
    TierDef(upper_bound=1_000_001, fee_per_tx=0.01),
    TierDef(upper_bound=5_000_001, fee_per_tx=0.007),
    TierDef(upper_bound=20_000_001, fee_per_tx=0.0039),
    TierDef(upper_bound=100_000_001, fee_per_tx=0.002),
]
