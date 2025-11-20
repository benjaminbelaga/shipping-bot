"""
ETL Spring Expéditions
Extrait les grilles Europe + Reste du monde et génère les tables normalisées
"""

import csv
import re
from pathlib import Path
import pdfplumber


# Mapping pays → ISO2
COUNTRY_MAPPING = {
    # Europe
    "Allemagne": "DE",
    "Autriche": "AT",
    "Belgique": "BE",
    "Bulgarie": "BG",
    "Croatie": "HR",
    "Danemark": "DK",
    "Espagne": "ES",
    "Estonie": "EE",
    "Finlande": "FI",
    "Grèce": "GR",
    "Hongrie": "HU",
    "Irlande": "IE",
    "Italie": "IT",
    "Lettonie": "LV",
    "Lituanie": "LT",
    "Luxembourg": "LU",
    "Malte": "MT",
    "Pays-Bas": "NL",
    "Pologne": "PL",
    "Portugal": "PT",
    "République tchèque": "CZ",
    "Roumanie": "RO",
    "Royaume-Uni": "GB",
    "Slovaquie": "SK",
    "Slovénie": "SI",
    "Suède": "SE",

    # Reste du monde
    "Canada": "CA",
    "États-Unis": "US",
    "Australie": "AU",
    "Chine": "CN",
    "Corée du Sud": "KR",
    "Hong Kong": "HK",
    "Inde": "IN",
    "Indonésie": "ID",
    "Israël": "IL",
    "Japon": "JP",
    "Malaisie": "MY",
    "Nouvelle-Zélande": "NZ",
    "Russie": "RU",
    "Singapour": "SG",
    "Taïwan": "TW",
    "Thaïlande": "TH",
    "Turquie": "TR",
    "Émirats arabes unis": "AE",
}


def parse_weight_header(header_row):
    """
    Parse les colonnes de poids (100g, 250g, 1Kg, etc.)
    Retourne liste de (col_index, weight_kg)
    """
    weights = []

    for i, cell in enumerate(header_row):
        if not cell or cell.startswith("Destination"):
            continue

        # Nettoyer (enlever espaces, normaliser)
        cell_clean = cell.strip().replace(" ", "")

        # Match 100g, 250g, 1Kg, 1.5Kg, etc.
        match_g = re.match(r"(\d+)g", cell_clean, re.IGNORECASE)
        match_kg = re.match(r"(\d+(?:\.\d+)?)K?g", cell_clean, re.IGNORECASE)

        if match_g:
            weight_kg = float(match_g.group(1)) / 1000.0
            weights.append((i, weight_kg))
        elif match_kg:
            weight_kg = float(match_kg.group(1))
            weights.append((i, weight_kg))

    return weights


def extract_spring_table(pdf_path, page_index, region_code, region_label):
    """
    Extrait un tableau Spring (Europe ou ROW)
    Returns: liste de dicts {country_label, country_iso2, region, weight_kg, price}
    """

    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        table = page.extract_table()

        if not table or len(table) < 3:
            raise ValueError(f"No table found on page {page_index + 1}")

        # Trouver la ligne d'en-tête (celle avec 100g, 250g, ...)
        header_row = None
        header_idx = None

        for i, row in enumerate(table):
            if any("100g" in str(cell) for cell in row if cell):
                header_row = row
                header_idx = i
                break

        if not header_row:
            raise ValueError("Could not find weight header row")

        # Parser les colonnes de poids
        weight_cols = parse_weight_header(header_row)

        print(f"  Found {len(weight_cols)} weight columns: {[w for _, w in weight_cols]}")

        # Parser les lignes pays (après l'en-tête)
        for row in table[header_idx + 1:]:
            if not row or not row[0]:
                continue

            country_label = row[0].strip()

            # Ignorer lignes vides ou notes
            if not country_label or country_label.startswith("*") or country_label.startswith("Surcharge"):
                continue

            # Normaliser le pays
            country_iso2 = COUNTRY_MAPPING.get(country_label)

            if not country_iso2:
                print(f"  ⚠️  Unknown country: {country_label}")
                continue

            # Extraire les prix pour chaque tranche de poids
            for col_idx, weight_kg in weight_cols:
                price_str = row[col_idx] if col_idx < len(row) else None

                if not price_str or price_str.strip() == "":
                    continue

                try:
                    price = float(price_str.replace(",", "."))

                    rows.append({
                        "region": region_code,
                        "region_label": region_label,
                        "country_label": country_label,
                        "country_iso2": country_iso2,
                        "weight_kg": weight_kg,
                        "price": price
                    })
                except ValueError:
                    print(f"  ⚠️  Invalid price: {price_str} for {country_label} @ {weight_kg}kg")

    return rows


def extract_spring_raw():
    """Extrait les deux tableaux Spring → CSV intermédiaire"""

    pdf_path = Path("data/raw/T2023 eCommerce - Spring Expéditions YOYAKU (1).pdf")
    csv_path = Path("data/intermediate/spring_raw.csv")

    print(f"📄 Extracting from {pdf_path.name}...")

    all_rows = []

    # Page 2: Europe
    print("\n  Processing Europe (page 2)...")
    europe_rows = extract_spring_table(pdf_path, page_index=1, region_code="EU", region_label="Europe")
    all_rows.extend(europe_rows)
    print(f"  ✅ {len(europe_rows)} rows extracted")

    # Page 3: Reste du monde
    print("\n  Processing Reste du monde (page 3)...")
    row_rows = extract_spring_table(pdf_path, page_index=2, region_code="ROW", region_label="Reste du monde")
    all_rows.extend(row_rows)
    print(f"  ✅ {len(row_rows)} rows extracted")

    # Écrire CSV
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "region", "region_label", "country_label", "country_iso2", "weight_kg", "price"
        ])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✅ Total {len(all_rows)} rows extracted to {csv_path}")
    return csv_path


def normalize_spring():
    """Convertit le CSV brut → tables normalisées"""

    raw_csv = Path("data/intermediate/spring_raw.csv")
    norm_dir = Path("data/normalized")

    print(f"\n🔄 Normalizing {raw_csv.name}...")

    # ========================================================================
    # 1. CARRIERS (append si existe déjà)
    # ========================================================================
    carriers_path = norm_dir / "carriers.csv"

    with carriers_path.open("r", encoding="utf-8") as f:
        existing_carriers = [row[1] for row in csv.reader(f)][1:]  # Skip header, get codes

    if "SPRING" not in existing_carriers:
        with carriers_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([2, "SPRING", "Spring Expéditions", "EUR"])
        print("✅ carriers.csv (added SPRING)")
    else:
        print("✅ carriers.csv (SPRING exists)")

    # ========================================================================
    # 2. SERVICES
    # ========================================================================
    services_path = norm_dir / "services.csv"

    with services_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Service 1: Spring Europe
        writer.writerow([
            2, 2, "SPRING_EU_HOME", "Spring Europe domicile", "EXPORT",
            "FR", "DAP", "PARCEL", 20.0, 5000, "2025-01-01", ""
        ])

        # Service 2: Spring Reste du monde
        writer.writerow([
            3, 2, "SPRING_ROW_HOME", "Spring Reste du monde domicile", "EXPORT",
            "FR", "DAP", "PARCEL", 20.0, 5000, "2025-01-01", ""
        ])

    print("✅ services.csv (added 2 services)")

    # ========================================================================
    # 3. TARIFF SCOPES + SCOPE COUNTRIES
    # ========================================================================
    scopes_path = norm_dir / "tariff_scopes.csv"
    scope_countries_path = norm_dir / "tariff_scope_countries.csv"

    # Lire existing scopes pour avoir le prochain scope_id
    with scopes_path.open("r", encoding="utf-8") as f:
        existing_scopes = list(csv.DictReader(f))
        scope_id = len(existing_scopes) + 1

    scopes = []
    scope_countries = []

    # Lire le CSV brut pour extraire les pays uniques par région
    with raw_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        countries_by_region = {}
        for row in reader:
            region = row["region"]
            iso2 = row["country_iso2"]

            if region not in countries_by_region:
                countries_by_region[region] = set()

            countries_by_region[region].add(iso2)

    # Créer un scope par pays
    for region, countries in countries_by_region.items():
        service_id = 2 if region == "EU" else 3

        for iso2 in sorted(countries):
            scope_code = f"SPRING_{region}_{iso2}"
            description = f"Spring {region} - {iso2}"

            scopes.append({
                "scope_id": scope_id,
                "service_id": service_id,
                "code": scope_code,
                "description": description,
                "is_catch_all": False
            })

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

    print(f"✅ tariff_scopes.csv (added {len(scopes)} scopes)")

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

    # Relire le CSV brut pour créer les bands
    with raw_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Grouper par scope
        bands_by_scope = {}

        for row in reader:
            region = row["region"]
            iso2 = row["country_iso2"]
            scope_code = f"SPRING_{region}_{iso2}"

            # Trouver le scope_id
            scope = next(s for s in scopes if s["code"] == scope_code)
            scope_key = scope["scope_id"]

            if scope_key not in bands_by_scope:
                bands_by_scope[scope_key] = []

            bands_by_scope[scope_key].append({
                "weight_kg": float(row["weight_kg"]),
                "price": float(row["price"])
            })

    # Créer les bands avec min/max weight
    for scope_key, weight_prices in bands_by_scope.items():
        # Trier par poids
        weight_prices.sort(key=lambda x: x["weight_kg"])

        for i, wp in enumerate(weight_prices):
            # min_weight = poids précédent (ou 0 si premier)
            min_weight = weight_prices[i-1]["weight_kg"] if i > 0 else 0.0
            max_weight = wp["weight_kg"]

            bands.append({
                "band_id": band_id,
                "scope_id": scope_key,
                "min_weight_kg": min_weight,
                "max_weight_kg": max_weight,
                "base_amount": wp["price"],
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
    # 5. SURCHARGE RULES (Spring fuel 5%)
    # ========================================================================
    surcharges_path = norm_dir / "surcharge_rules.csv"

    # Lire existing
    with surcharges_path.open("r", encoding="utf-8") as f:
        existing_surcharges = list(csv.DictReader(f))
        surcharge_id = len(existing_surcharges) + 1

    surcharges = [
        {
            "surcharge_id": surcharge_id,
            "service_id": 2,
            "name": "SPRING_EU_FUEL",
            "kind": "PERCENT",
            "basis": "FREIGHT",
            "value": 5.0,
            "conditions": "{}"
        },
        {
            "surcharge_id": surcharge_id + 1,
            "service_id": 3,
            "name": "SPRING_ROW_FUEL",
            "kind": "PERCENT",
            "basis": "FREIGHT",
            "value": 5.0,
            "conditions": "{}"
        }
    ]

    with surcharges_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "surcharge_id", "service_id", "name", "kind", "basis", "value", "conditions"
        ])
        writer.writerows(surcharges)

    print(f"✅ surcharge_rules.csv (added {len(surcharges)} surcharges)")


def main():
    """Pipeline ETL complet"""
    print("=" * 60)
    print("ETL SPRING EXPÉDITIONS")
    print("=" * 60)

    # Étape 1: Extraction PDF → CSV brut
    extract_spring_raw()

    # Étape 2: Normalisation
    normalize_spring()

    print("\n" + "=" * 60)
    print("✅ ETL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
