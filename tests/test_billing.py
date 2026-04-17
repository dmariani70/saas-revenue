"""
Tests for the marginal (progressive) tiered billing logic.
Tiers match the Contract sheet in saas_monthly_revenue.xlsx.
"""
import pytest
from app.services.billing_service import TierDef, calculate_billing, total_to_bill, DEFAULT_TIERS

TIERS = DEFAULT_TIERS  # [(1_000_001, 0.01), (5_000_001, 0.007), ...]


class TestCalculateBilling:
    def test_zero_txs(self):
        assert calculate_billing(0, TIERS) == 0.0

    def test_single_tx(self):
        # 1 tx at $0.01
        assert calculate_billing(1, TIERS) == 0.01

    def test_exactly_first_tier(self):
        # All 1_000_001 txs at $0.01
        expected = 1_000_001 * 0.01
        assert abs(calculate_billing(1_000_001, TIERS) - expected) < 0.01

    def test_crosses_first_tier(self):
        # 1_000_002 txs: first 1_000_001 @ 0.01, then 1 @ 0.007
        expected = 1_000_001 * 0.01 + 1 * 0.007
        result = calculate_billing(1_000_002, TIERS)
        assert abs(result - expected) < 0.0001

    def test_crosses_two_tiers(self):
        # 3_000_000 txs: first 1_000_001 @ 0.01, next 1_999_999 @ 0.007
        expected = 1_000_001 * 0.01 + 1_999_999 * 0.007
        result = calculate_billing(3_000_000, TIERS)
        assert abs(result - expected) < 0.01

    def test_small_volume_matches_excel(self):
        # From Billing sheet: 214 txs → $2.14
        result = calculate_billing(214, TIERS)
        assert abs(result - 2.14) < 0.001

    def test_marginal_not_flat(self):
        # With flat pricing 2M txs would be 2M * 0.007 = 14_000
        # With marginal it should be MORE (first 1M at higher rate)
        flat = 2_000_000 * 0.007
        marginal = calculate_billing(2_000_000, TIERS)
        assert marginal > flat

    def test_custom_tiers(self):
        tiers = [TierDef(100, 0.5), TierDef(200, 0.3)]
        # 150 txs: first 100 @ 0.5 + next 50 @ 0.3
        expected = 100 * 0.5 + 50 * 0.3
        assert abs(calculate_billing(150, tiers) - expected) < 0.0001


class TestTotalToBill:
    def test_below_minimum(self):
        # Very few txs → should return min fee
        result = total_to_bill(1, TIERS, min_fee=750.0)
        assert result == 750.0

    def test_above_minimum(self):
        # 1_000_001 txs @ 0.01 = $10_000.01 > $750
        result = total_to_bill(1_000_001, TIERS, min_fee=750.0)
        assert result > 750.0
        assert abs(result - 10_000.01) < 1.0

    def test_minimum_applied(self):
        # From Billing sheet: all small volumes show $750 as total_to_bill
        assert total_to_bill(214, TIERS, 750.0) == 750.0
        assert total_to_bill(1159, TIERS, 750.0) == 750.0

    def test_custom_minimum(self):
        result = total_to_bill(0, TIERS, min_fee=500.0)
        assert result == 500.0

    def test_exact_minimum_boundary(self):
        # Find txs that produce exactly $750 (= 75_000 txs at $0.01)
        result = total_to_bill(75_000, TIERS, min_fee=750.0)
        assert result == 750.0

    def test_just_above_minimum(self):
        result = total_to_bill(75_001, TIERS, min_fee=750.0)
        assert result > 750.0
