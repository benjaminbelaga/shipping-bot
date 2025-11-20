"""
ETL La Poste Delivengo
Extrait les tarifs du PDF Odyssée et génère les tables normalisées
"""

import csv
import json
from pathlib import Path
from decimal import Decimal
import pdfplumber


# Mapping pays → ISO2
COUNTRY_MAPPING = {
    "ALLEMAGNE": "DE",
    "GRANDE-BRETAGNE": "GB",
    "ETATS-UNIS": "US",
    "ZONE 1": "ZONE1",  # Zone 1: Autriche, Belgique, Luxembourg, Pays-Bas, Suisse
    "ZONE 2": "ZONE2",  # Zone 2: autres destinations
}

# Pays dans ZONE 1 (à confirmer avec le contrat complet)
ZONE1_COUNTRIES = ["AT", "BE", "LU", "NL", "CH"]

# ZONE 2 = reste du monde (catch-all)


def extract_delivengo_raw():
    """Extrait le tableau brut du PDF → CSV intermédiaire"""

    pdf_path = Path("data/raw/LaPoste_odysseeD-1102072-1_0.pdf")
    csv_path = Path("data/intermediate/laposte_delivengo_raw.csv")

    print(f"📄 Extracting from {pdf_path.name}...")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[2]  # Page 3
        table = page.extract_table()

        if not table or len(table) < 2:
            raise ValueError("No table found on page 3")

        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "country_label", "country_iso2", "solution_type",
                "format", "price_per_kg", "fixed_amount"
            ])

            for row in table[1:]:  # Skip header
                if not row or not row[0]:
                    continue

                country_label = row[0].strip()
                solution = row[1].strip() if len(row) > 1 else ""
                fmt = row[2].strip() if len(row) > 2 else ""
                price_kg_str = row[3].strip() if len(row) > 3 else "0"
                fixed_str = row[4].strip() if len(row) > 4 else "0"

                # Normaliser le pays
                country_iso2 = COUNTRY_MAPPING.get(country_label, country_label)

                # Convertir prix
                price_kg = float(price_kg_str.replace(",", "."))
                fixed = float(fixed_str.replace(",", "."))

                writer.writerow([
                    country_label, country_iso2, solution,
                    fmt, price_kg, fixed
                ])

    print(f"✅ Raw data extracted to {csv_path}")
    return csv_path


def normalize_delivengo():
    """Convertit le CSV brut → tables normalisées"""

    raw_csv = Path("data/intermediate/laposte_delivengo_raw.csv")
    norm_dir = Path("data/normalized")
    norm_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔄 Normalizing {raw_csv.name}...")

    # ========================================================================
    # 1. CARRIERS
    # ========================================================================
    carriers_path = norm_dir / "carriers.csv"
    carriers_exists = carriers_path.exists()

    with carriers_path.open("a" if carriers_exists else "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not carriers_exists:
            writer.writerow(["carrier_id", "code", "name", "currency"])
            writer.writerow([1, "LAPOSTE", "La Poste", "EUR"])

    print("✅ carriers.csv")

    # ========================================================================
    # 2. SERVICES
    # ========================================================================
    services_path = norm_dir / "services.csv"
    services_exists = services_path.exists()

    with services_path.open("a" if services_exists else "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not services_exists:
            writer.writerow([
                "service_id", "carrier_id", "code", "label", "direction",
                "origin_iso2", "incoterm", "service_type", "max_weight_kg",
                "volumetric_divisor", "active_from", "active_to"
            ])

        # Service unique: Delivengo Profil 2025
        writer.writerow([
            1,                          # service_id
            1,                          # carrier_id (LAPOSTE)
            "DELIVENGO_2025",           # code
            "Delivengo Profil 2025",    # label
            "EXPORT",                   # direction
            "FR",                       # origin_iso2
            "DAP",                      # incoterm
            "MAIL",                     # service_type
            2.0,                        # max_weight_kg
            5000,                       # volumetric_divisor
            "2025-01-01",               # active_from
            ""                          # active_to
        ])

    print("✅ services.csv")

    # ========================================================================
    # 3. TARIFF SCOPES + TARIFF SCOPE COUNTRIES
    # ========================================================================
    scopes_path = norm_dir / "tariff_scopes.csv"
    scope_countries_path = norm_dir / "tariff_scope_countries.csv"

    scopes = []
    scope_countries = []
    scope_id = 1

    # Lire le CSV brut
    with raw_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            iso2 = row["country_iso2"]
            fmt = row["format"]

            # Code scope = DELIVENGO_{ISO2}_{FORMAT}
            scope_code = f"DELIVENGO_{iso2}_{fmt.replace(' ', '_').upper()}"
            description = f"Delivengo {row['country_label']} - {fmt}"

            # Vérifier si ce scope existe déjà
            if not any(s["code"] == scope_code for s in scopes):
                is_catch_all = iso2 == "ZONE2"

                scopes.append({
                    "scope_id": scope_id,
                    "service_id": 1,
                    "code": scope_code,
                    "description": description,
                    "is_catch_all": is_catch_all
                })

                # Mapping pays
                if iso2 == "ZONE1":
                    for country in ZONE1_COUNTRIES:
                        scope_countries.append({
                            "scope_id": scope_id,
                            "country_iso2": country
                        })
                elif iso2 == "ZONE2":
                    # Catch-all: pas de pays spécifiques
                    pass
                else:
                    scope_countries.append({
                        "scope_id": scope_id,
                        "country_iso2": iso2
                    })

                scope_id += 1

    # Écrire scopes
    with scopes_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scope_id", "service_id", "code", "description", "is_catch_all"
        ])
        writer.writeheader()
        writer.writerows(scopes)

    print(f"✅ tariff_scopes.csv ({len(scopes)} scopes)")

    # Écrire scope_countries
    with scope_countries_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scope_id", "country_iso2"])
        writer.writeheader()
        writer.writerows(scope_countries)

    print(f"✅ tariff_scope_countries.csv ({len(scope_countries)} mappings)")

    # ========================================================================
    # 4. TARIFF BANDS
    # ========================================================================
    bands_path = norm_dir / "tariff_bands.csv"
    bands = []
    band_id = 1

    # Relire le CSV brut pour créer les bands
    with raw_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            iso2 = row["country_iso2"]
            fmt = row["format"]
            scope_code = f"DELIVENGO_{iso2}_{fmt.replace(' ', '_').upper()}"

            # Trouver le scope_id
            scope = next(s for s in scopes if s["code"] == scope_code)

            # Formule Delivengo: Prix = fixed_amount + price_per_kg * poids
            bands.append({
                "band_id": band_id,
                "scope_id": scope["scope_id"],
                "min_weight_kg": 0.0,
                "max_weight_kg": 2.0,
                "base_amount": row["fixed_amount"],
                "amount_per_kg": row["price_per_kg"],
                "is_min_charge": False
            })

            band_id += 1

    with bands_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "band_id", "scope_id", "min_weight_kg", "max_weight_kg",
            "base_amount", "amount_per_kg", "is_min_charge"
        ])
        writer.writeheader()
        writer.writerows(bands)

    print(f"✅ tariff_bands.csv ({len(bands)} bands)")

    # ========================================================================
    # 5. SURCHARGE RULES (aucune pour Delivengo pour l'instant)
    # ========================================================================
    surcharges_path = norm_dir / "surcharge_rules.csv"
    if not surcharges_path.exists():
        with surcharges_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "surcharge_id", "service_id", "name", "kind",
                "basis", "value", "conditions"
            ])
        print("✅ surcharge_rules.csv (empty)")


def main():
    """Pipeline ETL complet"""
    print("=" * 60)
    print("ETL LA POSTE DELIVENGO")
    print("=" * 60)

    # Étape 1: Extraction PDF → CSV brut
    extract_delivengo_raw()

    # Étape 2: Normalisation CSV brut → tables canoniques
    normalize_delivengo()

    print("\n" + "=" * 60)
    print("✅ ETL COMPLETE")
    print("=" * 60)
    print("\nNormalized files:")
    print("  - data/normalized/carriers.csv")
    print("  - data/normalized/services.csv")
    print("  - data/normalized/tariff_scopes.csv")
    print("  - data/normalized/tariff_scope_countries.csv")
    print("  - data/normalized/tariff_bands.csv")
    print("  - data/normalized/surcharge_rules.csv")


if __name__ == "__main__":
    main()
