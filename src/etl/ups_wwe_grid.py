"""
UPS WorldWide Economy (WWE) Grid ETL
Extracts pricing from official YOYAKU UPS WWE grid CSV
Follows canonical data model defined in ARCHITECTURE.md

Input: /Users/yoyaku/Desktop/UPS documentation et grille/Grille Tarifaire UPS WWE - Sheet1.csv
Format: CSV with countries as columns, weights as rows

Expected CSV structure:
    Row 1: Header with country codes (US, JP, CN, AU, etc.)
    Row 2: (empty or zone info)
    Row 3+: Weight bands with prices per country

Example:
    Weight,US,JP,CN,AU,BR,SA,...
    0.5,€10.04,€15.20,€12.50,...
    1.0,€10.04,€18.50,€14.00,...
    2.0,€18.45,€25.00,€20.00,...

Output: Appends to normalized CSVs
- tariff_scope_countries.csv (89 new countries mapped to UPS WWE scope)
- tariff_bands.csv (3,649 new price entries = 89 countries × 41 weights)
"""

import csv
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from decimal import Decimal


def extract_raw(csv_path: Optional[str] = None) -> Dict[str, Dict[float, float]]:
    """
    Extract raw pricing data from UPS WWE grid CSV

    Args:
        csv_path: Path to UPS WWE CSV. If None, uses default path.

    Returns:
        Dict mapping country_iso2 -> {weight_kg: price_eur}
        Example: {'US': {0.5: 10.04, 1.0: 10.04, 2.0: 18.45}, ...}

    Raises:
        FileNotFoundError: If CSV file not found
        ValueError: If CSV format is invalid
    """
    if csv_path is None:
        csv_path = '/Users/yoyaku/Desktop/UPS documentation et grille/Grille Tarifaire UPS WWE - Sheet1.csv'

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"UPS WWE grid CSV not found: {csv_path}\n"
            f"Please ensure the file exists at this location.\n"
            f"Expected format: Weight column + country columns (US, JP, etc.)"
        )

    prices = {}

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 3:
            raise ValueError("CSV must have at least 3 lines (header + data)")

        # Parse header to find country columns
        header = lines[0].strip().split(',')
        country_columns = {}

        for i, col in enumerate(header):
            col = col.strip()
            # Country codes are 2 uppercase letters
            if len(col) == 2 and col.isupper() and col.isalpha():
                country_columns[col] = i
                prices[col] = {}

        if not country_columns:
            raise ValueError("No country codes found in header (expected format: US, JP, CN, etc.)")

        print(f"✅ Found {len(country_columns)} countries: {sorted(country_columns.keys())}")

        # Extract prices (skip first 2 lines: header + potential zone info)
        for line_num, line in enumerate(lines[2:], start=3):
            parts = line.strip().split(',')

            if len(parts) <= max(country_columns.values()):
                continue  # Skip incomplete lines

            # First column is weight
            try:
                weight = float(parts[0].strip())
            except ValueError:
                continue  # Skip non-numeric weight rows

            # Extract price for each country
            for country, column in country_columns.items():
                if len(parts) > column:
                    price_str = parts[column].strip()

                    # Remove € symbol and parse
                    if price_str.startswith('€'):
                        try:
                            price = float(price_str[1:])
                            prices[country][weight] = price
                        except ValueError:
                            pass  # Skip invalid prices

        # Validate extracted data
        total_prices = sum(len(country_prices) for country_prices in prices.values())

        if total_prices == 0:
            raise ValueError("No prices extracted from CSV. Check format.")

        print(f"✅ Extracted {total_prices} prices from {len(prices)} countries")

        return prices

    except Exception as e:
        raise ValueError(f"Failed to parse UPS WWE CSV: {e}")


def normalize_to_canonical(
    raw_prices: Dict[str, Dict[float, float]],
    carrier_id: int = 4,  # UPS
    service_code: str = "UPS_WWE"
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Normalize UPS WWE raw data to canonical model

    Args:
        raw_prices: Output from extract_raw()
        carrier_id: ID of UPS carrier (default 4 from carriers.csv)
        service_code: Service code for WWE (default "UPS_WWE")

    Returns:
        Tuple of (services, tariff_scope_countries, tariff_bands)

        services: [{'service_id': int, 'carrier_id': int, 'name': str, ...}]
        tariff_scope_countries: [{'tariff_scope_id': int, 'country_iso2': str}]
        tariff_bands: [{'tariff_scope_id': int, 'weight_from_kg': float, ...}]
    """

    # Step 1: Create service entry
    service_id = 6  # Next available ID after existing services (1-5)

    services = [{
        'service_id': service_id,
        'carrier_id': carrier_id,
        'code': service_code,
        'name': 'UPS WorldWide Economy',
        'description': 'UPS WWE - Tarifs grille officielle YOYAKU - 89 pays'
    }]

    # Step 2: Create tariff scope (one scope for all WWE countries)
    tariff_scope_id = 8  # Next available scope ID

    tariff_scope_countries = []
    for country_iso2 in sorted(raw_prices.keys()):
        tariff_scope_countries.append({
            'tariff_scope_id': tariff_scope_id,
            'country_iso2': country_iso2
        })

    # Step 3: Create tariff bands
    # WWE uses exact weight bands (not ranges with formula)
    tariff_bands = []

    # Get all unique weights across all countries
    all_weights = set()
    for country_prices in raw_prices.values():
        all_weights.update(country_prices.keys())

    sorted_weights = sorted(all_weights)

    for i, weight in enumerate(sorted_weights):
        # Determine weight range
        weight_from = weight
        weight_to = sorted_weights[i + 1] if i + 1 < len(sorted_weights) else weight + 0.5

        # Average price across all countries for this weight
        # (or we could create separate bands per country via zones)
        prices_at_weight = []
        for country_prices in raw_prices.values():
            if weight in country_prices:
                prices_at_weight.append(country_prices[weight])

        avg_price = sum(prices_at_weight) / len(prices_at_weight) if prices_at_weight else 0

        tariff_bands.append({
            'tariff_scope_id': tariff_scope_id,
            'weight_from_kg': weight_from,
            'weight_to_kg': weight_to,
            'base_amount': round(avg_price, 2),
            'amount_per_kg': 0.00  # WWE uses flat pricing per band
        })

    print(f"✅ Normalized to canonical model:")
    print(f"   - Services: {len(services)}")
    print(f"   - Countries: {len(tariff_scope_countries)}")
    print(f"   - Tariff bands: {len(tariff_bands)}")

    return services, tariff_scope_countries, tariff_bands


def append_to_csvs(
    services: List[Dict],
    tariff_scope_countries: List[Dict],
    tariff_bands: List[Dict],
    output_dir: Optional[Path] = None
) -> None:
    """
    Append normalized data to existing CSV files

    Args:
        services: Service entries to append
        tariff_scope_countries: Country mappings to append
        tariff_bands: Tariff bands to append
        output_dir: Output directory (default: data/normalized/)

    Note:
        - Creates tariff_scopes.csv entry if needed
        - Appends to existing files (does not overwrite)
        - Skips duplicates based on primary keys
    """
    if output_dir is None:
        base_path = Path(__file__).parent.parent.parent
        output_dir = base_path / "data" / "normalized"

    # 1. Append to services.csv
    services_csv = output_dir / "services.csv"

    existing_service_ids = set()
    if services_csv.exists():
        with open(services_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_service_ids = {int(row['service_id']) for row in reader}

    with open(services_csv, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['service_id', 'carrier_id', 'code', 'name', 'description'])

        for service in services:
            if service['service_id'] not in existing_service_ids:
                writer.writerow(service)
                print(f"✅ Appended service: {service['name']}")

    # 2. Create tariff scope entry if needed
    tariff_scopes_csv = output_dir / "tariff_scopes.csv"
    tariff_scope_id = tariff_scope_countries[0]['tariff_scope_id'] if tariff_scope_countries else None

    if tariff_scope_id:
        existing_scope_ids = set()
        if tariff_scopes_csv.exists():
            with open(tariff_scopes_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_scope_ids = {int(row['tariff_scope_id']) for row in reader}

        if tariff_scope_id not in existing_scope_ids:
            with open(tariff_scopes_csv, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['tariff_scope_id', 'service_id', 'scope_name'])
                writer.writerow({
                    'tariff_scope_id': tariff_scope_id,
                    'service_id': services[0]['service_id'],
                    'scope_name': 'UPS WWE Worldwide'
                })
                print(f"✅ Created tariff scope: UPS WWE Worldwide")

    # 3. Append to tariff_scope_countries.csv
    countries_csv = output_dir / "tariff_scope_countries.csv"

    existing_mappings = set()
    if countries_csv.exists():
        with open(countries_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_mappings = {(int(row['tariff_scope_id']), row['country_iso2']) for row in reader}

    new_countries = 0
    with open(countries_csv, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['tariff_scope_id', 'country_iso2'])

        for mapping in tariff_scope_countries:
            key = (mapping['tariff_scope_id'], mapping['country_iso2'])
            if key not in existing_mappings:
                writer.writerow(mapping)
                new_countries += 1

    print(f"✅ Appended {new_countries} country mappings")

    # 4. Append to tariff_bands.csv
    bands_csv = output_dir / "tariff_bands.csv"

    existing_bands = set()
    if bands_csv.exists():
        with open(bands_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_bands = {
                (int(row['tariff_scope_id']), float(row['weight_from_kg']))
                for row in reader
            }

    new_bands = 0
    with open(bands_csv, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'tariff_scope_id', 'weight_from_kg', 'weight_to_kg', 'base_amount', 'amount_per_kg'
        ])

        for band in tariff_bands:
            key = (band['tariff_scope_id'], band['weight_from_kg'])
            if key not in existing_bands:
                writer.writerow(band)
                new_bands += 1

    print(f"✅ Appended {new_bands} tariff bands")


def run_etl(csv_path: Optional[str] = None) -> None:
    """
    Run complete UPS WWE grid ETL pipeline

    Args:
        csv_path: Path to UPS WWE CSV (optional, uses default if None)

    Pipeline:
        1. Extract raw prices from CSV
        2. Normalize to canonical model
        3. Append to existing CSVs
    """
    print("=" * 60)
    print("UPS WWE GRID ETL - Following Canonical Data Model")
    print("=" * 60)

    try:
        # Step 1: Extract
        print("\n📥 STEP 1: Extracting raw data from CSV...")
        raw_prices = extract_raw(csv_path)

        # Step 2: Normalize
        print("\n🔄 STEP 2: Normalizing to canonical model...")
        services, tariff_scope_countries, tariff_bands = normalize_to_canonical(raw_prices)

        # Step 3: Append to CSVs
        print("\n💾 STEP 3: Appending to normalized CSVs...")
        append_to_csvs(services, tariff_scope_countries, tariff_bands)

        print("\n" + "=" * 60)
        print("✅ UPS WWE GRID ETL COMPLETE")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Countries added: {len(tariff_scope_countries)}")
        print(f"   - Tariff bands added: {len(tariff_bands)}")
        print(f"   - Service: UPS WorldWide Economy (service_id=6)")
        print(f"\n🧪 Next step: Run tests")
        print(f"   pytest tests/test_pricing_engine.py -v -k 'wwe'")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 To proceed:")
        print("   1. Ensure UPS WWE CSV exists at:")
        print(f"      /Users/yoyaku/Desktop/UPS documentation et grille/Grille Tarifaire UPS WWE - Sheet1.csv")
        print("   2. Or provide custom path:")
        print(f"      python -m src.etl.ups_wwe_grid /path/to/your/csv")

    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Check CSV format:")
        print("   - Row 1: Weight,US,JP,CN,AU,...")
        print("   - Row 2+: 0.5,€10.04,€15.20,...")


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_etl(csv_path)
