"""
ETL FedEx International
Extrait les tarifs FedEx IP Export depuis le PDF 91 pages
"""

import csv
import re
from pathlib import Path
from decimal import Decimal
import pdfplumber


# Mapping country → ISO2 (réutilise le mapping de Spring + additions)
COUNTRY_MAPPING = {
    # Europe
    "Albania": "AL",
    "Andorra": "AD",
    "Austria": "AT",
    "Belarus": "BY",
    "Belgium": "BE",
    "Bosnia-Herzegovina": "BA",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Iceland": "IS",
    "Ireland": "IE",
    "Italy": "IT",
    "Kosovo": "XK",
    "Latvia": "LV",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Macedonia": "MK",
    "Malta": "MT",
    "Moldova": "MD",
    "Monaco": "MC",
    "Montenegro": "ME",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Russia": "RU",
    "San Marino": "SM",
    "Serbia": "RS",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Turkey": "TR",
    "Ukraine": "UA",
    "United Kingdom": "GB",
    "United Kingdom (Great Britain)": "GB",
    "Vatican City": "VA",

    # Americas
    "Anguilla": "AI",
    "Antigua & Barbuda": "AG",
    "Argentina": "AR",
    "Aruba": "AW",
    "Bahama": "BS",
    "Barbados": "BB",
    "Belize": "BZ",
    "Bermuda": "BM",
    "Bolivia": "BO",
    "Bonaire Sint Eustatius and Saba": "BQ",
    "Brazil": "BR",
    "British Virgin Islands": "VG",
    "Canada": "CA",
    "Cayman Islands": "KY",
    "Chile": "CL",
    "Colombia": "CO",
    "Costa Rica": "CR",
    "Cuba": "CU",
    "Curacao": "CW",
    "Dominica": "DM",
    "Dominican Republic": "DO",
    "Ecuador": "EC",
    "El Salvador": "SV",
    "Falkland Islands": "FK",
    "French Guiana": "GF",
    "Greenland": "GL",
    "Grenada": "GD",
    "Guadeloupe": "GP",
    "Guatemala": "GT",
    "Guyana": "GY",
    "Haiti": "HT",
    "Honduras": "HN",
    "Jamaica": "JM",
    "Martinique": "MQ",
    "Mexico": "MX",
    "Montserrat": "MS",
    "Nicaragua": "NI",
    "Panama": "PA",
    "Paraguay": "PY",
    "Peru": "PE",
    "Puerto Rico": "PR",
    "Saint Kitts & Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Martin": "MF",
    "Saint Pierre & Miquelon": "PM",
    "Saint Vincent & The Grenadines": "VC",
    "Sint Maarten": "SX",
    "Suriname": "SR",
    "Trinidad & Tobago": "TT",
    "Turks & Caicos Islands": "TC",
    "United States": "US",
    "U.S.A. - REST OF COUNTRY": "US",
    "U.S. Virgin Islands": "VI",
    "Uruguay": "UY",
    "Venezuela": "VE",
    "Virgin Islands U.S.": "VI",

    # Asia/Pacific
    "Afghanistan": "AF",
    "American Samoa": "AS",
    "Australia": "AU",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Bhutan": "BT",
    "Brunei": "BN",
    "Cambodia": "KH",
    "China": "CN",
    "Cook Islands": "CK",
    "Fiji": "FJ",
    "French Polynesia": "PF",
    "Guam": "GU",
    "Hong Kong": "HK",
    "Hong Kong SAR, China": "HK",
    "India": "IN",
    "Indonesia": "ID",
    "Israel": "IL",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Korea South": "KR",
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Laos": "LA",
    "Lebanon": "LB",
    "Macao": "MO",
    "Malaysia": "MY",
    "Maldives": "MV",
    "Mongolia": "MN",
    "Myanmar": "MM",
    "Nepal": "NP",
    "New Caledonia": "NC",
    "New Zealand": "NZ",
    "Oman": "OM",
    "Pakistan": "PK",
    "Palau": "PW",
    "Papua New Guinea": "PG",
    "Philippines": "PH",
    "Qatar": "QA",
    "Samoa": "WS",
    "Saudi Arabia": "SA",
    "Singapore": "SG",
    "Solomon Islands": "SB",
    "Sri Lanka": "LK",
    "Syria": "SY",
    "Taiwan": "TW",
    "Tajikistan": "TJ",
    "Thailand": "TH",
    "Timor-Leste": "TL",
    "Tonga": "TO",
    "Turkmenistan": "TM",
    "U.A.E.": "AE",
    "Uzbekistan": "UZ",
    "Vanuatu": "VU",
    "Vietnam": "VN",
    "Yemen": "YE",

    # Africa
    "Algeria": "DZ",
    "Angola": "AO",
    "Benin": "BJ",
    "Botswana": "BW",
    "Burkina Faso": "BF",
    "Burundi": "BI",
    "Cameroon": "CM",
    "Cape Verde": "CV",
    "Central African Republic": "CF",
    "Chad": "TD",
    "Comoros": "KM",
    "Congo": "CG",
    "Congo The Democratic Republic Of The": "CD",
    "Cote d Ivoire": "CI",
    "Djibouti": "DJ",
    "Egypt": "EG",
    "Equatorial Guinea": "GQ",
    "Eritrea": "ER",
    "Ethiopia": "ET",
    "Gabon": "GA",
    "Gambia": "GM",
    "Ghana": "GH",
    "Guinea": "GN",
    "Guinea-Bissau": "GW",
    "Kenya": "KE",
    "Lesotho": "LS",
    "Liberia": "LR",
    "Libya": "LY",
    "Madagascar": "MG",
    "Malawi": "MW",
    "Mali": "ML",
    "Mauritania": "MR",
    "Mauritius": "MU",
    "Mayotte": "YT",
    "Morocco": "MA",
    "Mozambique": "MZ",
    "Namibia": "NA",
    "Niger": "NE",
    "Nigeria": "NG",
    "Reunion": "RE",
    "Rwanda": "RW",
    "Sao Tome & Principe": "ST",
    "Senegal": "SN",
    "Seychelles": "SC",
    "Sierra Leone": "SL",
    "Somalia": "SO",
    "South Africa": "ZA",
    "South Sudan": "SS",
    "Sudan": "SD",
    "Swaziland": "SZ",
    "Tanzania": "TZ",
    "Togo": "TG",
    "Tunisia": "TN",
    "Uganda": "UG",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
}


def extract_zone_chart():
    """Extrait la zone chart FedEx (pages 22-26) pour le service IP"""

    pdf_path = Path("data/raw/FEDEX Courtesy-Net-Rates-15358183-English (2).pdf")
    csv_path = Path("data/intermediate/fedex_zone_chart.csv")

    print("📄 Extracting FedEx zone chart...")

    zone_mappings = []

    with pdfplumber.open(pdf_path) as pdf:
        # Pages 22-26 (indices 21-25)
        for page_idx in range(21, 26):
            page = pdf.pages[page_idx]
            table = page.extract_table()

            if not table or len(table) < 2:
                continue

            # Header: ['Country/Territory', 'IPE', 'IP', 'IE', 'RE', 'IPF', 'IEF', 'REF']
            # On veut la colonne 'IP' (index 2)

            for row in table[1:]:  # Skip header
                if not row or not row[0]:
                    continue

                country = row[0].strip()
                zone_ip = row[2].strip() if len(row) > 2 else ""

                if not zone_ip or len(zone_ip) > 2:
                    continue

                # Normaliser le pays
                iso2 = COUNTRY_MAPPING.get(country)

                if not iso2:
                    print(f"  ⚠️  Unknown country: {country}")
                    continue

                zone_mappings.append({
                    "country_label": country,
                    "country_iso2": iso2,
                    "zone": zone_ip
                })

    # Écrire CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["country_label", "country_iso2", "zone"])
        writer.writeheader()
        writer.writerows(zone_mappings)

    print(f"✅ Zone chart extracted: {len(zone_mappings)} countries")
    return csv_path


def extract_rate_tables():
    """Extrait les tables de tarifs FedEx IP Export (0.5-70.5kg)"""

    pdf_path = Path("data/raw/FEDEX Courtesy-Net-Rates-15358183-English (2).pdf")
    csv_path = Path("data/intermediate/fedex_ip_rates.csv")

    print("\n📄 Extracting FedEx IP Export rate tables...")

    rates = []

    with pdfplumber.open(pdf_path) as pdf:
        # Configuration des pages à extraire
        pages_config = [
            # (page_idx, zone_row_idx, data_start_idx)
            (13, 1, 2),   # Page 14: 0.5-24.0 kg, zones A-T
            (9, 1, 2),    # Page 10: 24.0-57.0 kg, zones A-S
            (10, 1, 2),   # Page 11: 57.5-70.5 kg, zones A-S
            (11, 1, 2),   # Page 12: 14.0-47.0 kg, zones T-X
            (12, 1, 2),   # Page 13: 47.5-70.5 kg, zones T-X
        ]

        for page_idx, zone_row, data_start in pages_config:
            page = pdf.pages[page_idx]
            table = page.extract_table()

            if not table or len(table) < data_start + 1:
                continue

            # Extraire les zones (row 1)
            zones = [z for z in table[zone_row][1:] if z and len(z) <= 2]

            print(f"  Page {page_idx+1}: {len(zones)} zones ({', '.join(zones)})")

            # Extraire les données
            for row in table[data_start:]:
                if not row or not row[0]:
                    continue

                try:
                    weight_kg = float(row[0])
                except ValueError:
                    continue

                # Prix par zone
                for i, zone in enumerate(zones):
                    col_idx = i + 1

                    if col_idx >= len(row):
                        continue

                    price_str = row[col_idx]

                    if not price_str or price_str.strip() == "":
                        continue

                    try:
                        price = float(price_str.replace(",", "."))

                        # Éviter les doublons (certains poids apparaissent sur plusieurs pages)
                        key = (weight_kg, zone)
                        if not any(r["weight_kg"] == weight_kg and r["zone"] == zone for r in rates):
                            rates.append({
                                "weight_kg": weight_kg,
                                "zone": zone,
                                "price": price
                            })
                    except ValueError:
                        pass

    # Trier par zone puis poids
    rates.sort(key=lambda r: (r["zone"], r["weight_kg"]))

    # Écrire CSV
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["weight_kg", "zone", "price"])
        writer.writeheader()
        writer.writerows(rates)

    print(f"✅ Rate tables extracted: {len(rates)} rates")
    return csv_path


def normalize_fedex():
    """Normalise les données FedEx vers le schéma canonique"""

    zone_chart_csv = Path("data/intermediate/fedex_zone_chart.csv")
    rates_csv = Path("data/intermediate/fedex_ip_rates.csv")
    norm_dir = Path("data/normalized")

    print(f"\n🔄 Normalizing FedEx data...")

    # ========================================================================
    # 1. CARRIERS (append)
    # ========================================================================
    carriers_path = norm_dir / "carriers.csv"

    with carriers_path.open("r", encoding="utf-8") as f:
        existing_carriers = [row[1] for row in csv.reader(f)][1:]

    if "FEDEX" not in existing_carriers:
        with carriers_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([3, "FEDEX", "FedEx", "EUR"])
        print("✅ carriers.csv (added FEDEX)")
    else:
        print("✅ carriers.csv (FEDEX exists)")

    # ========================================================================
    # 2. SERVICES
    # ========================================================================
    services_path = norm_dir / "services.csv"

    with services_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            4, 3, "FDX_IP_EXPORT", "FedEx International Priority Export", "EXPORT",
            "FR", "DAP", "EXPRESS", 70.5, 5000, "2025-01-01", ""
        ])

    print("✅ services.csv (added FDX_IP_EXPORT)")

    # ========================================================================
    # 3. TARIFF SCOPES + SCOPE COUNTRIES
    # ========================================================================
    scopes_path = norm_dir / "tariff_scopes.csv"
    scope_countries_path = norm_dir / "tariff_scope_countries.csv"

    # Lire existing scopes
    with scopes_path.open("r", encoding="utf-8") as f:
        existing_scopes = list(csv.DictReader(f))
        scope_id = len(existing_scopes) + 1

    scopes = []
    scope_countries = []

    # Charger la zone chart
    zone_map = {}  # zone -> [iso2, iso2, ...]

    with zone_chart_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            zone = row["zone"]
            iso2 = row["country_iso2"]

            if zone not in zone_map:
                zone_map[zone] = []

            zone_map[zone].append(iso2)

    # Créer un scope par zone
    for zone, countries in sorted(zone_map.items()):
        scope_code = f"FDX_IP_ZONE_{zone}"
        description = f"FedEx IP Export - Zone {zone}"

        scopes.append({
            "scope_id": scope_id,
            "service_id": 4,
            "code": scope_code,
            "description": description,
            "is_catch_all": False
        })

        for iso2 in countries:
            scope_countries.append({
                "scope_id": scope_id,
                "country_iso2": iso2
            })

        scope_id += 1

    # Append scopes
    with scopes_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scope_id", "service_id", "code", "description", "is_catch_all"
        ])
        writer.writerows(scopes)

    print(f"✅ tariff_scopes.csv (added {len(scopes)} zones)")

    # Append scope_countries
    with scope_countries_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scope_id", "country_iso2"])
        writer.writerows(scope_countries)

    print(f"✅ tariff_scope_countries.csv (added {len(scope_countries)} mappings)")

    # ========================================================================
    # 4. TARIFF BANDS
    # ========================================================================
    bands_path = norm_dir / "tariff_bands.csv"

    # Lire existing bands
    with bands_path.open("r", encoding="utf-8") as f:
        existing_bands = list(csv.DictReader(f))
        band_id = len(existing_bands) + 1

    bands = []

    # Charger les rates
    with rates_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            zone = row["zone"]
            weight_kg = float(row["weight_kg"])
            price = float(row["price"])

            # Trouver le scope_id
            scope_code = f"FDX_IP_ZONE_{zone}"
            scope = next((s for s in scopes if s["code"] == scope_code), None)

            if not scope:
                continue

            # FedEx: prix fixe par pallier de poids
            bands.append({
                "band_id": band_id,
                "scope_id": scope["scope_id"],
                "min_weight_kg": weight_kg,
                "max_weight_kg": weight_kg,  # min = max pour FedEx
                "base_amount": price,
                "amount_per_kg": 0,
                "is_min_charge": False
            })

            band_id += 1

    # Append bands
    with bands_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "band_id", "scope_id", "min_weight_kg", "max_weight_kg",
            "base_amount", "amount_per_kg", "is_min_charge"
        ])
        writer.writerows(bands)

    print(f"✅ tariff_bands.csv (added {len(bands)} bands)")

    # ========================================================================
    # 5. SURCHARGE RULES (none for now)
    # ========================================================================
    print("✅ No surcharges for FedEx (net rates)")


def main():
    """Pipeline ETL complet"""
    print("=" * 70)
    print("ETL FEDEX INTERNATIONAL PRIORITY EXPORT")
    print("=" * 70)

    # Étape 1: Zone chart
    extract_zone_chart()

    # Étape 2: Rate tables
    extract_rate_tables()

    # Étape 3: Normalisation
    normalize_fedex()

    print("\n" + "=" * 70)
    print("✅ ETL COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
