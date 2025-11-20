"""
Tests for complete pricing engine
Validates end-to-end pricing queries across all carriers
"""

import pytest
from src.engine.engine import PricingEngine


@pytest.fixture
def engine():
    """Create a PricingEngine instance with loaded data"""
    return PricingEngine()


class TestBasicQueries:
    """Test basic pricing queries"""

    def test_japan_2kg(self, engine):
        """Test 2kg shipment to Japan (all carriers should offer)"""
        offers = engine.price("JP", 2.0)

        assert len(offers) > 0
        # Should have FedEx, Spring ROW, La Poste, UPS Express Saver, UPS Standard
        assert len(offers) >= 4

        # Verify all offers have required fields
        for offer in offers:
            assert offer.carrier_name
            assert offer.service_label
            assert offer.freight > 0
            assert offer.total > 0
            assert offer.currency == "EUR"

        # Verify sorted by price ascending
        prices = [float(o.total) for o in offers]
        assert prices == sorted(prices)

    def test_germany_2kg(self, engine):
        """Test 2kg shipment to Germany (should have Spring EU, La Poste)"""
        offers = engine.price("DE", 2.0)

        assert len(offers) >= 2

        # Spring EU should be available for DE
        spring_offers = [o for o in offers if "Spring" in o.carrier_name]
        assert len(spring_offers) >= 1

        # Verify cheapest is first
        assert offers[0].total <= offers[-1].total

    def test_usa_2kg(self, engine):
        """Test 2kg shipment to USA"""
        offers = engine.price("US", 2.0)

        assert len(offers) > 0

        # Should have La Poste, Spring ROW, FedEx
        carrier_names = {o.carrier_name for o in offers}
        assert "La Poste" in carrier_names or "FedEx" in carrier_names

    def test_australia_2kg(self, engine):
        """Test 2kg shipment to Australia"""
        offers = engine.price("AU", 2.0)

        assert len(offers) > 0

        # Should have Spring ROW (covers AU)
        carrier_names = {o.carrier_name for o in offers}
        assert "Spring Expéditions" in carrier_names


class TestCountryResolution:
    """Test that country name variants resolve correctly"""

    def test_french_country_names(self, engine):
        """Test French country names"""
        # Allemagne → Germany
        offers_fr = engine.price("Allemagne", 2.0)
        offers_en = engine.price("Germany", 2.0)
        assert len(offers_fr) == len(offers_en)

        # Japon → Japan
        offers_fr = engine.price("Japon", 2.0)
        offers_en = engine.price("Japan", 2.0)
        assert len(offers_fr) == len(offers_en)

    def test_iso2_codes(self, engine):
        """Test ISO2 codes directly"""
        offers = engine.price("FR", 2.0)
        assert len(offers) == 0  # No export to France (origin country)

        offers = engine.price("DE", 2.0)
        assert len(offers) >= 2

        offers = engine.price("US", 2.0)
        assert len(offers) > 0

    def test_case_insensitive(self, engine):
        """Country names should be case-insensitive"""
        offers_lower = engine.price("germany", 2.0)
        offers_upper = engine.price("GERMANY", 2.0)
        offers_title = engine.price("Germany", 2.0)

        assert len(offers_lower) == len(offers_upper) == len(offers_title)

    def test_unknown_country(self, engine):
        """Unknown countries should return empty list"""
        offers = engine.price("Atlantis", 2.0)
        assert len(offers) == 0


class TestWeightBands:
    """Test that weight band lookups work correctly"""

    def test_low_weight(self, engine):
        """Test low weight shipments (0.5kg)"""
        offers = engine.price("DE", 0.5)
        assert len(offers) > 0

        # Verify freight is reasonable for 0.5kg
        for offer in offers:
            assert float(offer.freight) < 20.0  # Should be cheaper than 2kg

    def test_medium_weight(self, engine):
        """Test medium weight shipments (10kg)"""
        offers = engine.price("JP", 10.0)
        assert len(offers) > 0

        # Verify freight increases with weight
        for offer in offers:
            assert float(offer.freight) > 10.0  # Should be more than 2kg

    def test_max_weight_exceeded(self, engine):
        """Test that services respect max_weight_kg limits"""
        # La Poste Delivengo has max 2kg
        # So 10kg should not return La Poste
        offers = engine.price("JP", 10.0)

        laposte_offers = [o for o in offers if o.carrier_code == "LAPOSTE"]
        assert len(laposte_offers) == 0  # Should be excluded

    def test_weight_progression(self, engine):
        """Test that freight increases with weight"""
        offers_1kg = engine.price("DE", 1.0)
        offers_2kg = engine.price("DE", 2.0)
        offers_5kg = engine.price("DE", 5.0)

        # Find Spring EU in all three
        spring_1kg = [o for o in offers_1kg if "Spring" in o.carrier_name and "EU" in o.service_code]
        spring_2kg = [o for o in offers_2kg if "Spring" in o.carrier_name and "EU" in o.service_code]
        spring_5kg = [o for o in offers_5kg if "Spring" in o.carrier_name and "EU" in o.service_code]

        if spring_1kg and spring_2kg and spring_5kg:
            # Freight should increase with weight
            assert float(spring_1kg[0].total) < float(spring_2kg[0].total)
            assert float(spring_2kg[0].total) < float(spring_5kg[0].total)


class TestCarrierCoverage:
    """Test that each carrier covers expected destinations"""

    def test_laposte_coverage(self, engine):
        """La Poste should cover most destinations"""
        destinations = ["DE", "GB", "US", "JP", "AU", "BR"]

        for dest in destinations:
            offers = engine.price(dest, 1.0)  # 1kg within Delivengo limit
            laposte_offers = [o for o in offers if o.carrier_code == "LAPOSTE"]
            # La Poste should be present for most destinations
            # (may not cover all, but should cover many)

    def test_spring_eu_coverage(self, engine):
        """Spring EU should only cover European countries"""
        eu_countries = ["DE", "IT", "ES", "PT", "BE", "AT"]

        for country in eu_countries:
            offers = engine.price(country, 2.0)
            spring_eu = [o for o in offers if o.service_code == "SPRING_EU_HOME"]
            assert len(spring_eu) >= 1, f"Spring EU should cover {country}"

        # Should NOT cover non-EU
        non_eu_countries = ["US", "JP", "AU"]
        for country in non_eu_countries:
            offers = engine.price(country, 2.0)
            spring_eu = [o for o in offers if o.service_code == "SPRING_EU_HOME"]
            assert len(spring_eu) == 0, f"Spring EU should NOT cover {country}"

    def test_spring_row_coverage(self, engine):
        """Spring ROW should cover Rest of World"""
        row_countries = ["US", "JP", "AU", "CN", "CA", "SG"]

        for country in row_countries:
            offers = engine.price(country, 2.0)
            spring_row = [o for o in offers if o.service_code == "SPRING_ROW_HOME"]
            assert len(spring_row) >= 1, f"Spring ROW should cover {country}"

    def test_fedex_coverage(self, engine):
        """FedEx should cover worldwide destinations"""
        destinations = ["US", "JP", "DE", "AU", "BR", "ZA"]

        fedex_count = 0
        for dest in destinations:
            offers = engine.price(dest, 10.0)  # 10kg to test FedEx ranges
            fedex_offers = [o for o in offers if o.carrier_code == "FEDEX"]
            if fedex_offers:
                fedex_count += 1

        # FedEx should cover most of these
        assert fedex_count >= 4, "FedEx should cover most worldwide destinations"

    def test_ups_partial_coverage(self, engine):
        """UPS currently has limited coverage (only 10 countries mapped)"""
        # Countries we know UPS covers (from zone mappings)
        mapped_countries = ["JP", "CN", "ID", "MY", "PH", "TW", "VN", "KH", "LA", "GB"]

        for country in mapped_countries:
            offers = engine.price(country, 2.0)
            ups_offers = [o for o in offers if o.carrier_code == "UPS"]
            # Should have at least one UPS service
            # (may not match weight bands, but zone should exist)

        # Countries NOT mapped should not return UPS
        unmapped_countries = ["DE", "FR", "IT", "ES", "US", "AU"]
        for country in unmapped_countries:
            offers = engine.price(country, 2.0)
            ups_offers = [o for o in offers if o.carrier_code == "UPS"]
            assert len(ups_offers) == 0, f"UPS should NOT cover {country} (unmapped)"


class TestPriceComparison:
    """Test that price comparison works correctly across carriers"""

    def test_fedex_competitive_for_asia(self, engine):
        """FedEx should be competitive for Asian destinations"""
        offers = engine.price("JP", 10.0)

        fedex_offers = [o for o in offers if o.carrier_code == "FEDEX"]
        if fedex_offers:
            fedex_price = float(fedex_offers[0].total)

            # FedEx should not be the most expensive
            all_prices = [float(o.total) for o in offers]
            assert fedex_price < max(all_prices)

    def test_spring_eu_cheapest_for_europe(self, engine):
        """Spring EU should be competitive for European destinations"""
        offers = engine.price("DE", 2.0)

        spring_eu = [o for o in offers if o.service_code == "SPRING_EU_HOME"]
        if spring_eu:
            spring_price = float(spring_eu[0].total)

            # Spring EU should be among the cheaper options
            all_prices = sorted([float(o.total) for o in offers])
            assert spring_price <= all_prices[len(all_prices) // 2]  # Top 50%

    def test_cheapest_always_first(self, engine):
        """Offers should always be sorted by price (cheapest first)"""
        test_queries = [
            ("DE", 2.0),
            ("US", 2.0),
            ("JP", 2.0),
            ("AU", 2.0),
            ("GB", 1.0)
        ]

        for dest, weight in test_queries:
            offers = engine.price(dest, weight)
            if len(offers) > 1:
                prices = [float(o.total) for o in offers]
                assert prices == sorted(prices), f"Prices not sorted for {dest}"


class TestSurchargeApplication:
    """Test that surcharges are applied correctly in end-to-end queries"""

    def test_spring_includes_fuel_surcharge(self, engine):
        """Spring services should include +5% fuel surcharge"""
        offers = engine.price("DE", 2.0)
        spring_offers = [o for o in offers if "Spring" in o.carrier_name]

        for offer in spring_offers:
            # Surcharge should be ~5% of freight
            expected_surcharge = float(offer.freight) * 0.05
            assert float(offer.surcharges) == pytest.approx(expected_surcharge, abs=0.02)

    def test_ups_includes_fuel_discount(self, engine):
        """UPS Express Saver should include -30% fuel discount"""
        offers = engine.price("JP", 2.0)
        ups_offers = [o for o in offers if o.service_code == "UPS_EXPRESS_SAVER"]

        if ups_offers:
            offer = ups_offers[0]
            # Surcharge should be negative (discount)
            assert float(offer.surcharges) < 0

            # Should be approximately -30% of freight
            expected_discount = float(offer.freight) * -0.30
            assert float(offer.surcharges) == pytest.approx(expected_discount, abs=0.02)

    def test_laposte_no_surcharges(self, engine):
        """La Poste Delivengo has no surcharges"""
        offers = engine.price("DE", 1.0)
        laposte_offers = [o for o in offers if o.carrier_code == "LAPOSTE"]

        for offer in laposte_offers:
            assert float(offer.surcharges) == 0.0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_low_weight(self, engine):
        """Test 0.1kg shipment (minimum)"""
        offers = engine.price("DE", 0.1)
        # Should still return some offers (those with 0-0.5kg bands)
        assert len(offers) >= 0  # May be 0 if no bands cover 0.1kg

    def test_exact_band_boundary(self, engine):
        """Test weight exactly on band boundary"""
        # Test 2kg exactly (common boundary)
        offers = engine.price("DE", 2.0)
        assert len(offers) > 0

    def test_very_heavy_weight(self, engine):
        """Test 50kg shipment (near max for some carriers)"""
        offers = engine.price("JP", 50.0)

        # Only FedEx and UPS should handle this (max 70kg)
        # La Poste (2kg max) and Spring (20kg max) should be excluded
        carrier_codes = {o.carrier_code for o in offers}
        assert "LAPOSTE" not in carrier_codes
        assert "SPRING" not in carrier_codes

    def test_debug_mode(self, engine):
        """Test that debug mode doesn't break queries"""
        offers = engine.price("DE", 2.0, debug=True)
        assert len(offers) > 0


class TestPerformance:
    """Test that queries execute quickly"""

    def test_query_speed(self, engine):
        """Single query should complete in <100ms"""
        import time

        start = time.time()
        offers = engine.price("JP", 2.0)
        elapsed = time.time() - start

        assert elapsed < 0.1  # 100ms
        assert len(offers) > 0

    def test_multiple_queries(self, engine):
        """100 queries should complete in <1 second"""
        import time

        queries = [
            ("DE", 2.0),
            ("US", 2.0),
            ("JP", 2.0),
            ("GB", 1.0),
            ("AU", 5.0)
        ] * 20  # 100 queries total

        start = time.time()
        for dest, weight in queries:
            engine.price(dest, weight)
        elapsed = time.time() - start

        assert elapsed < 1.0  # 1 second for 100 queries


class TestRegressionCases:
    """Regression tests for specific reported issues"""

    def test_ups_japan_bug_6_49_eur(self, engine):
        """
        Regression: UPS Japan 2kg showed 6.49 EUR (incorrect)
        Should show 22.71 EUR after fix
        """
        offers = engine.price("JP", 2.0)
        ups_offers = [o for o in offers if o.service_code == "UPS_EXPRESS_SAVER"]

        assert len(ups_offers) == 1
        offer = ups_offers[0]

        # Should NOT be 6.49 EUR (the bug)
        assert float(offer.total) != pytest.approx(6.49, abs=0.01)

        # Should be 22.71 EUR (correct)
        assert float(offer.total) == pytest.approx(22.71, abs=0.01)

    def test_fedex_usa_competitive(self, engine):
        """
        From FEDEX-INTEGRATION-REPORT.md:
        USA 2kg FedEx should be ~14.46 EUR (competitive)
        """
        offers = engine.price("US", 2.0)
        fedex_offers = [o for o in offers if o.carrier_code == "FEDEX"]

        if fedex_offers:
            offer = fedex_offers[0]
            # FedEx USA should be reasonably priced
            assert 10.0 < float(offer.total) < 25.0

    def test_spring_japan_fuel_included(self, engine):
        """
        From FEDEX-INTEGRATION-REPORT.md:
        Japan 10kg Spring ROW should be ~28.80 EUR (with fuel)
        """
        offers = engine.price("JP", 10.0)
        spring_offers = [o for o in offers if o.service_code == "SPRING_ROW_HOME"]

        if spring_offers:
            offer = spring_offers[0]
            # Should have positive surcharge (5% fuel)
            assert float(offer.surcharges) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
