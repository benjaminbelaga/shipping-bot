"""
Country Resolver - Normalise les noms de pays vers ISO2
Gère les alias, accents, variations orthographiques
"""

import re
import unicodedata
import csv
from pathlib import Path
from typing import Optional, Dict


class CountryResolver:
    """Résolveur de pays intelligent avec alias et fuzzy matching"""

    # Mapping pays → ISO2
    COUNTRIES = {
        # ISO2 → nom standard
        "DE": "Allemagne",
        "AT": "Autriche",
        "BE": "Belgique",
        "BG": "Bulgarie",
        "HR": "Croatie",
        "DK": "Danemark",
        "ES": "Espagne",
        "EE": "Estonie",
        "FI": "Finlande",
        "FR": "France",
        "GR": "Grèce",
        "HU": "Hongrie",
        "IE": "Irlande",
        "IT": "Italie",
        "LV": "Lettonie",
        "LT": "Lituanie",
        "LU": "Luxembourg",
        "MT": "Malte",
        "NL": "Pays-Bas",
        "PL": "Pologne",
        "PT": "Portugal",
        "CZ": "République tchèque",
        "RO": "Roumanie",
        "GB": "Royaume-Uni",
        "SK": "Slovaquie",
        "SI": "Slovénie",
        "SE": "Suède",
        "CH": "Suisse",
        "NO": "Norvège",

        # Reste du monde
        "CA": "Canada",
        "US": "États-Unis",
        "MX": "Mexique",
        "BR": "Brésil",
        "AR": "Argentine",
        "CL": "Chili",

        "AU": "Australie",
        "NZ": "Nouvelle-Zélande",
        "CN": "Chine",
        "JP": "Japon",
        "KR": "Corée du Sud",
        "HK": "Hong Kong",
        "IN": "Inde",
        "ID": "Indonésie",
        "IL": "Israël",
        "MY": "Malaisie",
        "RU": "Russie",
        "SG": "Singapour",
        "TW": "Taïwan",
        "TH": "Thaïlande",
        "TR": "Turquie",
        "AE": "Émirats arabes unis",
        "ZA": "Afrique du Sud",
    }

    # Alias courants
    ALIASES = {
        # Variations françaises
        "allemagne": "DE",
        "autriche": "AT",
        "belgique": "BE",
        "danemark": "DK",
        "espagne": "ES",
        "finlande": "FI",
        "france": "FR",
        "grece": "GR",
        "hollande": "NL",
        "irlande": "IE",
        "italie": "IT",
        "luxembourg": "LU",
        "paysbas": "NL",
        "paysбas": "NL",
        "pologne": "PL",
        "portugal": "PT",
        "royaumeuni": "GB",
        "republichetche": "CZ",
        "reptcheque": "CZ",
        "roumanie": "RO",
        "suisse": "CH",
        "suede": "SE",
        "norvege": "NO",

        # Variations anglaises
        "germany": "DE",
        "austria": "AT",
        "belgium": "BE",
        "denmark": "DK",
        "spain": "ES",
        "finland": "FI",
        "france": "FR",
        "greece": "GR",
        "netherlands": "NL",
        "ireland": "IE",
        "italy": "IT",
        "poland": "PL",
        "portugal": "PT",
        "unitedkingdom": "GB",
        "uk": "GB",
        "gb": "GB",
        "czechrepublic": "CZ",
        "romania": "RO",
        "switzerland": "CH",
        "sweden": "SE",
        "norway": "NO",

        # Reste du monde
        "canada": "CA",
        "etatsunis": "US",
        "usa": "US",
        "us": "US",
        "unitedstates": "US",
        "mexique": "MX",
        "mexico": "MX",
        "bresil": "BR",
        "brazil": "BR",
        "argentine": "AR",
        "argentina": "AR",
        "chili": "CL",
        "chile": "CL",

        "australie": "AU",
        "australia": "AU",
        "nouvellezelande": "NZ",
        "newzealand": "NZ",
        "chine": "CN",
        "china": "CN",
        "japon": "JP",
        "japan": "JP",
        "coreedusud": "KR",
        "southkorea": "KR",
        "korea": "KR",
        "hongkong": "HK",
        "inde": "IN",
        "india": "IN",
        "indonesie": "ID",
        "indonesia": "ID",
        "israel": "IL",
        "malaisie": "MY",
        "malaysia": "MY",
        "russie": "RU",
        "russia": "RU",
        "singapour": "SG",
        "singapore": "SG",
        "taiwan": "TW",
        "thailande": "TH",
        "thailand": "TH",
        "turquie": "TR",
        "turkey": "TR",
        "emiratsarabesunis": "AE",
        "uae": "AE",
        "dubai": "AE",
        "afriquedusud": "ZA",
        "southafrica": "ZA",

        # Codes ISO
        "de": "DE",
        "at": "AT",
        "be": "BE",
        "dk": "DK",
        "es": "ES",
        "fi": "FI",
        "fr": "FR",
        "gr": "GR",
        "nl": "NL",
        "ie": "IE",
        "it": "IT",
        "pl": "PL",
        "pt": "PT",
        "cz": "CZ",
        "ro": "RO",
        "ch": "CH",
        "se": "SE",
        "no": "NO",
        "ca": "CA",
        "mx": "MX",
        "br": "BR",
        "ar": "AR",
        "cl": "CL",
        "au": "AU",
        "nz": "NZ",
        "cn": "CN",
        "jp": "JP",
        "kr": "KR",
        "hk": "HK",
        "in": "IN",
        "id": "ID",
        "il": "IL",
        "my": "MY",
        "ru": "RU",
        "sg": "SG",
        "tw": "TW",
        "th": "TH",
        "tr": "TR",
        "ae": "AE",
        "za": "ZA",
    }

    def __init__(self, aliases_csv: Optional[str] = None):
        """
        Initialize country resolver

        Args:
            aliases_csv: Path to country_aliases.csv. If None, uses default location.
        """
        if aliases_csv is None:
            # Default location relative to this file
            base_path = Path(__file__).parent.parent.parent
            aliases_csv = base_path / "data" / "normalized" / "country_aliases.csv"

        self.alias_map = self._build_alias_map(aliases_csv)

    def _build_alias_map(self, aliases_csv: Path) -> Dict[str, str]:
        """
        Build alias → ISO2 mapping from CSV file

        Loads all aliases from country_aliases.csv and normalizes them
        Falls back to hardcoded ALIASES if CSV not found
        """
        alias_map = {}

        # Try to load from CSV
        if Path(aliases_csv).exists():
            with open(aliases_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    alias = self.normalize_string(row['alias'])
                    iso2 = row['country_iso2']
                    alias_map[alias] = iso2
        else:
            # Fallback to hardcoded aliases
            alias_map = {**self.ALIASES}

        return alias_map

    @staticmethod
    def normalize_string(s: str) -> str:
        """
        Normalise une chaîne:
        - lowercase
        - enlever accents
        - enlever ponctuation/espaces
        - enlever caractères spéciaux
        """
        # Lowercase
        s = s.lower()

        # Enlever accents
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')

        # Enlever tout sauf lettres
        s = re.sub(r'[^a-z]', '', s)

        return s

    def resolve(self, country_name: str) -> Optional[str]:
        """
        Résout un nom de pays vers ISO2

        Examples:
            resolve("Australie") -> "AU"
            resolve("australie") -> "AU"
            resolve("australia") -> "AU"
            resolve("2kg Australie") -> "AU" (extrait le pays)
            resolve("au") -> "AU"
            resolve("??") -> None

        Matching strategy:
            1. Exact match (after normalization)
            2. Fuzzy match: find alias substring in query (min 4 chars to avoid false positives)
        """
        if not country_name:
            return None

        # Normaliser
        normalized = self.normalize_string(country_name)

        # Chercher dans les alias (exact match)
        if normalized in self.alias_map:
            return self.alias_map[normalized]

        # Fuzzy match: find country name within query string
        # Only match aliases >= 4 chars to avoid false positives (like "at" in "atlantis")
        matches = []
        for alias, iso2 in self.alias_map.items():
            if len(alias) >= 4 and alias in normalized:
                # Prioritize longer matches
                matches.append((len(alias), alias, iso2))

        if matches:
            # Return the longest match (most specific)
            matches.sort(reverse=True)
            return matches[0][2]

        return None

    def get_name(self, iso2: str) -> Optional[str]:
        """Retourne le nom français d'un pays depuis son ISO2"""
        return self.COUNTRIES.get(iso2)
