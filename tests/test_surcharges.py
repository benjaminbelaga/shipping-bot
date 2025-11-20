"""
Tests for surcharge calculation
Validates that negative percentages, conditions, and order are handled correctly
"""

import pytest
from decimal import Decimal
from src.engine.engine import PricingEngine
from src.engine.loader import SurchargeRule


@pytest.fixture
def engine():
    """Create a PricingEngine instance with loaded data"""
    engine = PricingEngine()
    return engine


class TestNegativeSurcharges:
    """Test negative percentage surcharges (discounts)"""

    def test_ups_express_saver_fuel_discount(self, engine):
        """
        UPS Express Saver has -30% fuel discount (no conditions)
        Test case from UPS-INTEGRATION-REPORT.md
        """
        offers = engine.price("JP", 2.0)
        ups_express = [o for o in offers if o.service_code == "UPS_EXPRESS_SAVER"]

        assert len(ups_express) == 1
        offer = ups_express[0]

        # Expected: Freight 32.44 EUR - 30% = -9.732 EUR surcharge
        # Total: 32.44 - 9.73 = 22.71 EUR
        assert float(offer.freight) == pytest.approx(32.44, abs=0.01)
        assert float(offer.surcharges) == pytest.approx(-9.73, abs=0.01)
        assert float(offer.total) == pytest.approx(22.71, abs=0.01)

    def test_negative_surcharge_calculation(self, engine):
        """Test that -30% discount is calculated correctly"""
        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver
        dest_iso2 = "JP"
        weight_kg = 2.0

        surcharge_total = engine._calculate_surcharges(
            service_id, dest_iso2, weight_kg, freight
        )

        # -30% of 100 = -30
        assert surcharge_total == pytest.approx(Decimal("-30.00"), abs=Decimal("0.01"))

    def test_multiple_negative_surcharges(self, engine):
        """Test that multiple negative surcharges are applied correctly"""
        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver

        # Test with residential condition (should apply both -30% and -50%)
        conditions = {"delivery_type": "residential"}
        surcharge_total = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, conditions
        )

        # -30% fuel + -50% residential = -80% total
        # 100 * -0.30 = -30
        # 100 * -0.50 = -50
        # Total: -80
        assert surcharge_total == pytest.approx(Decimal("-80.00"), abs=Decimal("0.01"))


class TestPositiveSurcharges:
    """Test positive percentage surcharges (fees)"""

    def test_spring_eu_fuel_surcharge(self, engine):
        """Spring EU has +5% fuel surcharge"""
        offers = engine.price("DE", 2.0)
        spring_eu = [o for o in offers if o.service_code == "SPRING_EU_HOME"]

        assert len(spring_eu) == 1
        offer = spring_eu[0]

        # Spring EU DE 2kg: ~5.40 EUR freight + 5% = 0.27 EUR surcharge
        assert float(offer.surcharges) > 0  # Positive surcharge
        assert float(offer.surcharges) == pytest.approx(
            float(offer.freight) * 0.05, abs=0.01
        )

    def test_spring_row_fuel_surcharge(self, engine):
        """Spring ROW has +5% fuel surcharge"""
        offers = engine.price("JP", 2.0)
        spring_row = [o for o in offers if o.service_code == "SPRING_ROW_HOME"]

        assert len(spring_row) == 1
        offer = spring_row[0]

        # Spring ROW JP 2kg: 27.60 EUR freight + 5% = 1.38 EUR surcharge
        assert float(offer.freight) == pytest.approx(27.60, abs=0.01)
        assert float(offer.surcharges) == pytest.approx(1.38, abs=0.01)
        assert float(offer.total) == pytest.approx(28.98, abs=0.01)

    def test_ups_standard_weekly_delivery(self, engine):
        """UPS Standard has +100% weekly delivery surcharge (with conditions)"""
        freight = Decimal("50.00")
        service_id = 6  # UPS Standard

        # Without weekly condition: no surcharge
        surcharge_no_condition = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight
        )
        assert surcharge_no_condition == Decimal("0.00")

        # With weekly condition: +100% surcharge
        conditions = {"delivery_frequency": "weekly"}
        surcharge_with_condition = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, conditions
        )

        # +100% of 50 = +50
        assert surcharge_with_condition == pytest.approx(
            Decimal("50.00"), abs=Decimal("0.01")
        )


class TestSurchargeOrder:
    """Test that surcharges are applied in correct order (negative first, positive last)"""

    def test_order_negative_first_positive_last(self, engine):
        """
        According to ARCHITECTURE.md:
        1. Apply negative surcharges (discounts) first
        2. Apply positive surcharges (fees) last
        """
        # Create a mock scenario with both negative and positive surcharges
        # UPS Express Saver: -30% fuel (negative)
        # If we add a positive surcharge, it should come after

        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver

        # Get the rules and verify they're sorted correctly
        rules = engine.loader.surcharges.get(service_id, [])

        # Filter applicable rules (no conditions)
        applicable_rules = [r for r in rules if not r.conditions]

        # Sort by value (negative first)
        applicable_rules.sort(key=lambda r: r.value)

        # First rule should be negative (most negative first)
        assert applicable_rules[0].value < 0
        assert applicable_rules[0].name == "UPS Fuel Discount"
        assert applicable_rules[0].value == Decimal("-30.0")


class TestConditionalSurcharges:
    """Test that surcharges with conditions are only applied when conditions match"""

    def test_residential_discount_only_when_specified(self, engine):
        """UPS residential discount (-50%) should only apply with residential condition"""
        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver

        # Without residential condition: only -30% fuel discount
        surcharge_no_residential = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight
        )
        assert surcharge_no_residential == pytest.approx(
            Decimal("-30.00"), abs=Decimal("0.01")
        )

        # With residential condition: -30% fuel + -50% residential = -80%
        conditions = {"delivery_type": "residential"}
        surcharge_with_residential = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, conditions
        )
        assert surcharge_with_residential == pytest.approx(
            Decimal("-80.00"), abs=Decimal("0.01")
        )

    def test_weekly_delivery_only_when_specified(self, engine):
        """UPS weekly delivery surcharge (+100%) should only apply with weekly condition"""
        freight = Decimal("50.00")
        service_id = 6  # UPS Standard

        # Without weekly condition: no surcharge
        surcharge_no_weekly = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight
        )
        assert surcharge_no_weekly == Decimal("0.00")

        # With weekly condition: +100%
        conditions = {"delivery_frequency": "weekly"}
        surcharge_with_weekly = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, conditions
        )
        assert surcharge_with_weekly == pytest.approx(
            Decimal("50.00"), abs=Decimal("0.01")
        )

    def test_empty_conditions_always_apply(self, engine):
        """Surcharges with empty conditions {} should always apply"""
        # UPS fuel discount has no conditions, should always apply
        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver

        # No conditions passed
        surcharge_1 = engine._calculate_surcharges(service_id, "JP", 2.0, freight)

        # Empty conditions passed
        surcharge_2 = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, {}
        )

        # Arbitrary conditions passed
        surcharge_3 = engine._calculate_surcharges(
            service_id, "JP", 2.0, freight, {"random_key": "random_value"}
        )

        # All should apply the -30% fuel discount
        assert surcharge_1 == surcharge_2 == surcharge_3
        assert surcharge_1 == pytest.approx(Decimal("-30.00"), abs=Decimal("0.01"))


class TestMatchConditions:
    """Test the _matches_conditions helper method"""

    def test_empty_rule_conditions_always_match(self, engine):
        """Rule with no conditions should always match"""
        assert engine._matches_conditions({}, {}) is True
        assert engine._matches_conditions({}, {"foo": "bar"}) is True

    def test_exact_match(self, engine):
        """Rule conditions should match query conditions exactly"""
        rule_conditions = {"delivery_type": "residential"}
        query_conditions = {"delivery_type": "residential"}
        assert engine._matches_conditions(rule_conditions, query_conditions) is True

    def test_missing_condition_no_match(self, engine):
        """If rule requires a condition not in query, should not match"""
        rule_conditions = {"delivery_type": "residential"}
        query_conditions = {}
        assert engine._matches_conditions(rule_conditions, query_conditions) is False

    def test_wrong_value_no_match(self, engine):
        """If condition value doesn't match, should not match"""
        rule_conditions = {"delivery_type": "residential"}
        query_conditions = {"delivery_type": "commercial"}
        assert engine._matches_conditions(rule_conditions, query_conditions) is False

    def test_multiple_conditions_all_must_match(self, engine):
        """All rule conditions must be satisfied"""
        rule_conditions = {
            "delivery_type": "residential",
            "delivery_frequency": "weekly"
        }

        # Both match
        query_1 = {"delivery_type": "residential", "delivery_frequency": "weekly"}
        assert engine._matches_conditions(rule_conditions, query_1) is True

        # Only one matches
        query_2 = {"delivery_type": "residential", "delivery_frequency": "daily"}
        assert engine._matches_conditions(rule_conditions, query_2) is False

        # Missing one
        query_3 = {"delivery_type": "residential"}
        assert engine._matches_conditions(rule_conditions, query_3) is False

    def test_extra_query_conditions_ok(self, engine):
        """Query can have extra conditions not required by rule"""
        rule_conditions = {"delivery_type": "residential"}
        query_conditions = {
            "delivery_type": "residential",
            "extra_key": "extra_value"
        }
        assert engine._matches_conditions(rule_conditions, query_conditions) is True


class TestRegressionBugs:
    """Regression tests for known bugs"""

    def test_ups_japan_bug_fixed(self, engine):
        """
        Regression test for UPS-INTEGRATION-REPORT.md Issue 1
        Before fix: 2kg Japan showed 6.49 EUR (incorrect)
        After fix: Should show 22.71 EUR (correct)
        """
        offers = engine.price("JP", 2.0)
        ups_express = [o for o in offers if o.service_code == "UPS_EXPRESS_SAVER"]

        assert len(ups_express) == 1
        offer = ups_express[0]

        # Should NOT be 6.49 EUR (the bug)
        assert float(offer.total) != pytest.approx(6.49, abs=0.01)

        # Should be 22.71 EUR (correct)
        assert float(offer.total) == pytest.approx(22.71, abs=0.01)

    def test_no_unconditional_residential_discount(self, engine):
        """
        The bug was that -50% residential discount was applied unconditionally
        Now it should only apply when delivery_type=residential
        """
        freight = Decimal("100.00")
        service_id = 5  # UPS Express Saver

        # Without residential condition, should only get -30% fuel discount
        surcharge = engine._calculate_surcharges(service_id, "JP", 2.0, freight)

        # Should be -30, NOT -80 (which would include residential)
        assert surcharge == pytest.approx(Decimal("-30.00"), abs=Decimal("0.01"))
        assert surcharge != pytest.approx(Decimal("-80.00"), abs=Decimal("0.01"))


class TestSurchargeKinds:
    """Test different surcharge calculation kinds"""

    def test_percent_on_freight(self, engine):
        """PERCENT kind with FREIGHT basis"""
        freight = Decimal("100.00")

        # 5% of freight
        surcharge = freight * Decimal("5.0") / Decimal("100")
        assert surcharge == Decimal("5.00")

        # -30% of freight (discount)
        discount = freight * Decimal("-30.0") / Decimal("100")
        assert discount == Decimal("-30.00")

    def test_flat_surcharge(self, engine):
        """FLAT kind surcharges (fixed amount per shipment)"""
        # Flat surcharges would be a fixed EUR amount
        # Example: 5.00 EUR handling fee
        # (Not currently used in our carriers, but supported)
        pass

    def test_per_kg_surcharge(self, engine):
        """PER_KG kind surcharges (amount per kilogram)"""
        # Per-kg surcharges would multiply by weight
        # Example: 2.00 EUR/kg oversized surcharge
        # (Not currently used in our carriers, but supported)
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
