"""
Tests for country name resolution
Validates that country_aliases.csv correctly maps all variants to ISO2 codes
"""

import pytest
from src.engine.country_resolver import CountryResolver


@pytest.fixture
def resolver():
    """Create a CountryResolver instance"""
    return CountryResolver()


class TestBasicResolution:
    """Test basic ISO2 code resolution"""

    def test_iso2_uppercase(self, resolver):
        """ISO2 codes in uppercase should resolve directly"""
        assert resolver.resolve("FR") == "FR"
        assert resolver.resolve("US") == "US"
        assert resolver.resolve("GB") == "GB"
        assert resolver.resolve("JP") == "JP"
        assert resolver.resolve("DE") == "DE"

    def test_iso2_lowercase(self, resolver):
        """ISO2 codes in lowercase should normalize and resolve"""
        assert resolver.resolve("fr") == "FR"
        assert resolver.resolve("us") == "US"
        assert resolver.resolve("gb") == "GB"
        assert resolver.resolve("jp") == "JP"
        assert resolver.resolve("de") == "DE"


class TestEnglishNames:
    """Test English country name resolution"""

    def test_common_english_names(self, resolver):
        """Common English country names should resolve"""
        assert resolver.resolve("france") == "FR"
        assert resolver.resolve("germany") == "DE"
        assert resolver.resolve("united states") == "US"
        assert resolver.resolve("unitedstates") == "US"
        assert resolver.resolve("japan") == "JP"
        assert resolver.resolve("australia") == "AU"

    def test_english_case_insensitive(self, resolver):
        """English names should be case-insensitive"""
        assert resolver.resolve("France") == "FR"
        assert resolver.resolve("FRANCE") == "FR"
        assert resolver.resolve("Germany") == "DE"
        assert resolver.resolve("AUSTRALIA") == "AU"


class TestFrenchNames:
    """Test French country name resolution"""

    def test_common_french_names(self, resolver):
        """Common French country names should resolve"""
        assert resolver.resolve("allemagne") == "DE"
        assert resolver.resolve("etats-unis") == "US"
        assert resolver.resolve("etatsunis") == "US"
        assert resolver.resolve("japon") == "JP"
        assert resolver.resolve("australie") == "AU"
        assert resolver.resolve("royaume-uni") == "GB"
        assert resolver.resolve("royaumeuni") == "GB"

    def test_french_accents(self, resolver):
        """French names with accents should normalize"""
        # Note: CountryResolver should strip accents
        assert resolver.resolve("états-unis") == "US"
        assert resolver.resolve("Allemagne") == "DE"


class TestVariants:
    """Test country name variants and aliases"""

    def test_usa_variants(self, resolver):
        """USA has many common variants"""
        assert resolver.resolve("usa") == "US"
        assert resolver.resolve("US") == "US"
        assert resolver.resolve("united states") == "US"
        assert resolver.resolve("unitedstates") == "US"
        assert resolver.resolve("america") == "US"
        assert resolver.resolve("etatsunis") == "US"

    def test_uk_variants(self, resolver):
        """UK has many common variants"""
        assert resolver.resolve("uk") == "GB"
        assert resolver.resolve("gb") == "GB"
        assert resolver.resolve("united kingdom") == "GB"
        assert resolver.resolve("unitedkingdom") == "GB"
        assert resolver.resolve("great britain") == "GB"
        assert resolver.resolve("greatbritain") == "GB"
        assert resolver.resolve("england") == "GB"
        assert resolver.resolve("angleterre") == "GB"

    def test_germany_variants(self, resolver):
        """Germany has English, French, and German variants"""
        assert resolver.resolve("germany") == "DE"
        assert resolver.resolve("allemagne") == "DE"
        assert resolver.resolve("deutschland") == "DE"
        assert resolver.resolve("de") == "DE"

    def test_netherlands_variants(self, resolver):
        """Netherlands has multiple common names"""
        assert resolver.resolve("netherlands") == "NL"
        assert resolver.resolve("paysbas") == "NL"
        assert resolver.resolve("holland") == "NL"
        assert resolver.resolve("hollande") == "NL"
        assert resolver.resolve("nl") == "NL"


class TestAsianCountries:
    """Test Asian country resolution (critical for UPS/FedEx zones)"""

    def test_japan(self, resolver):
        """Japan (UPS Zone 11)"""
        assert resolver.resolve("japan") == "JP"
        assert resolver.resolve("japon") == "JP"
        assert resolver.resolve("jp") == "JP"

    def test_china(self, resolver):
        """China (UPS Zone 11)"""
        assert resolver.resolve("china") == "CN"
        assert resolver.resolve("chine") == "CN"
        assert resolver.resolve("cn") == "CN"

    def test_southeast_asia(self, resolver):
        """Southeast Asian countries (UPS Zones 11-13)"""
        assert resolver.resolve("vietnam") == "VN"
        assert resolver.resolve("viet") == "VN"
        assert resolver.resolve("cambodia") == "KH"
        assert resolver.resolve("cambodge") == "KH"
        assert resolver.resolve("laos") == "LA"
        assert resolver.resolve("malaysia") == "MY"
        assert resolver.resolve("malaisie") == "MY"
        assert resolver.resolve("philippines") == "PH"
        assert resolver.resolve("indonesia") == "ID"
        assert resolver.resolve("indonesie") == "ID"
        assert resolver.resolve("taiwan") == "TW"


class TestEuropeanCountries:
    """Test European country resolution (critical for Spring EU)"""

    def test_major_eu_countries(self, resolver):
        """Major EU countries covered by Spring"""
        assert resolver.resolve("france") == "FR"
        assert resolver.resolve("germany") == "DE"
        assert resolver.resolve("italy") == "IT"
        assert resolver.resolve("italie") == "IT"
        assert resolver.resolve("spain") == "ES"
        assert resolver.resolve("espagne") == "ES"
        assert resolver.resolve("portugal") == "PT"

    def test_northern_europe(self, resolver):
        """Northern European countries"""
        assert resolver.resolve("sweden") == "SE"
        assert resolver.resolve("suede") == "SE"
        assert resolver.resolve("finland") == "FI"
        assert resolver.resolve("finlande") == "FI"
        assert resolver.resolve("denmark") == "DK"
        assert resolver.resolve("danemark") == "DK"
        assert resolver.resolve("norway") == "NO"
        assert resolver.resolve("norvege") == "NO"

    def test_benelux(self, resolver):
        """Benelux countries"""
        assert resolver.resolve("belgium") == "BE"
        assert resolver.resolve("belgique") == "BE"
        assert resolver.resolve("netherlands") == "NL"
        assert resolver.resolve("luxembourg") == "LU"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_unknown_country(self, resolver):
        """Unknown countries should return None"""
        assert resolver.resolve("atlantis") is None
        assert resolver.resolve("xxxx") is None
        assert resolver.resolve("unknown") is None

    def test_empty_string(self, resolver):
        """Empty string should return None"""
        assert resolver.resolve("") is None

    def test_whitespace(self, resolver):
        """Whitespace should be handled"""
        assert resolver.resolve("  france  ") == "FR"
        assert resolver.resolve(" germany ") == "DE"

    def test_special_characters(self, resolver):
        """Special characters should be normalized"""
        # Hyphens, apostrophes should be stripped
        assert resolver.resolve("etats-unis") == "US"
        assert resolver.resolve("royaume-uni") == "GB"


class TestGetName:
    """Test reverse lookup: ISO2 → English name"""

    def test_get_name_basic(self, resolver):
        """get_name() should return French country names"""
        assert resolver.get_name("FR") == "France"
        assert resolver.get_name("DE") == "Allemagne"
        assert resolver.get_name("US") == "États-Unis"  # Correct French with accent
        assert resolver.get_name("GB") == "Royaume-Uni"
        assert resolver.get_name("JP") == "Japon"

    def test_get_name_unknown(self, resolver):
        """get_name() should handle unknown ISO2 codes"""
        assert resolver.get_name("XX") is None
        assert resolver.get_name("ZZ") is None


class TestCarrierCriticalCountries:
    """Test countries critical for carrier integrations"""

    def test_fedex_zone_coverage(self, resolver):
        """Countries with FedEx zones should resolve"""
        # Zone A-H: Europe
        assert resolver.resolve("france") == "FR"
        assert resolver.resolve("germany") == "DE"
        assert resolver.resolve("italy") == "IT"
        assert resolver.resolve("spain") == "ES"
        assert resolver.resolve("belgium") == "BE"

        # Zone I: Asia-Pacific
        assert resolver.resolve("japan") == "JP"
        assert resolver.resolve("australia") == "AU"
        assert resolver.resolve("singapore") == "SG"

        # Zone S-U: Americas
        assert resolver.resolve("usa") == "US"
        assert resolver.resolve("canada") == "CA"
        assert resolver.resolve("brazil") == "BR"
        assert resolver.resolve("bresil") == "BR"

    def test_ups_mapped_zones(self, resolver):
        """Countries currently mapped in UPS zones should resolve"""
        # UPS Zone 11
        assert resolver.resolve("china") == "CN"
        assert resolver.resolve("indonesia") == "ID"
        assert resolver.resolve("japan") == "JP"
        assert resolver.resolve("malaysia") == "MY"
        assert resolver.resolve("philippines") == "PH"
        assert resolver.resolve("taiwan") == "TW"

        # UPS Zone 12
        assert resolver.resolve("vietnam") == "VN"

        # UPS Zone 13
        assert resolver.resolve("cambodia") == "KH"
        assert resolver.resolve("laos") == "LA"

        # UPS Zone 703
        assert resolver.resolve("uk") == "GB"

    def test_spring_eu_countries(self, resolver):
        """Countries covered by Spring EU should resolve"""
        eu_countries = [
            ("austria", "AT"), ("belgium", "BE"), ("germany", "DE"),
            ("denmark", "DK"), ("finland", "FI"), ("greece", "GR"),
            ("hungary", "HU"), ("ireland", "IE"), ("italy", "IT"),
            ("luxembourg", "LU"), ("poland", "PL"), ("portugal", "PT"),
            ("russia", "RU"), ("sweden", "SE"), ("turkey", "TR")
        ]

        for name, code in eu_countries:
            assert resolver.resolve(name) == code

    def test_spring_row_countries(self, resolver):
        """Countries covered by Spring ROW should resolve"""
        row_countries = [
            ("australia", "AU"), ("canada", "CA"), ("china", "CN"),
            ("hong kong", "HK"), ("indonesia", "ID"), ("israel", "IL"),
            ("india", "IN"), ("japan", "JP"), ("south korea", "KR"),
            ("malaysia", "MY"), ("singapore", "SG"), ("thailand", "TH"),
            ("taiwan", "TW"), ("usa", "US")
        ]

        for name, code in row_countries:
            assert resolver.resolve(name) == code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
