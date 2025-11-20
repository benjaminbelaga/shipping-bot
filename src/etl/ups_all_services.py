"""
UPS All Services ETL
Extracts ALL UPS pricing from YOYAKU proposal Excel:
- DDU Export FR (88 countries) ✅ Already extracted
- DDP Export DE (35 countries)
- DDU Import to NL (2 countries)
- DDP Import to NL (4 countries)

Follows canonical data model defined in ARCHITECTURE.md
"""

import pandas as pd
import csv
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from decimal import Decimal

DEFAULT_XLSX_PATH = "/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/PROPAL YOYAKU ECONOMY DDU (1).xlsx"

# Service definitions
SERVICES = [
    {
        "sheet": "DDU Export - Output",
        "code": "UPS_ECONOMY_DDU_EXPORT_FR",
        "label": "UPS Economy DDU Export FR",
        "direction": "EXPORT",
        "origin_iso2": "FR",
        "incoterm": "DDU",
        "service_type": "ECONOMY",
        "max_weight_kg": 70,
        "origin_row": 0,
        "origin_col": 1,
        "is_destination": False  # origin-based
    },
    {
        "sheet": "DDP Export - Output",
        "code": "UPS_EXPRESS_DDP_EXPORT_DE",
        "label": "UPS Express DDP Export DE",
        "direction": "EXPORT",
        "origin_iso2": "DE",
        "incoterm": "DDP",
        "service_type": "EXPRESS",
        "max_weight_kg": 70,
        "origin_row": 0,
        "origin_col": 1,
        "is_destination": False
    },
    {
        "sheet": "DDU Import - Output",
        "code": "UPS_ECONOMY_DDU_IMPORT_NL",
        "label": "UPS Economy DDU Import NL",
        "direction": "IMPORT",
        "origin_iso2": "NL",
        "incoterm": "DDU",
        "service_type": "ECONOMY",
        "max_weight_kg": 70,
        "origin_row": 0,
        "origin_col": 1,
        "is_destination": True  # destination-based
    },
    {
        "sheet": "DDP Import - Output",
        "code": "UPS_EXPRESS_DDP_IMPORT_NL",
        "label": "UPS Express DDP Import NL",
        "direction": "IMPORT",
        "origin_iso2": "NL",
        "incoterm": "DDP",
        "service_type": "EXPRESS",
        "max_weight_kg": 70,
        "origin_row": 0,
        "origin_col": 1,
        "is_destination": True
    }
]


def extract_raw_service(
    xlsx_path: str,
    service_def: Dict
) -> pd.DataFrame:
    """
    Extract raw pricing data from one service sheet

    Returns:
        DataFrame with columns:
        - origin_iso2, dest_iso2, band_type, min_weight_kg, max_weight_kg
        - price, price_per_kg, min_charge
    """
    sheet_name = service_def["sheet"]
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None)

    # Extract origin/destination (Row 0, Cell B1)
    location_iso2 = str(df.iloc[service_def["origin_row"], service_def["origin_col"]]).strip().upper()

    # For import services, location is destination; for export, it's origin
    if service_def["is_destination"]:
        dest_iso2_fixed = location_iso2
        origin_iso2_variable = True
    else:
        origin_iso2_fixed = location_iso2
        dest_iso2_variable = True

    # Find header row with "Ctry / Zone →"
    header_mask = df.iloc[:, 1].astype(str).str.contains("Ctry / Zone", na=False, case=False)
    if not header_mask.any():
        print(f"⚠️  Warning: No 'Ctry / Zone' header found in {sheet_name}")
        return pd.DataFrame()

    header_row_idx = df.index[header_mask].tolist()[0]

    # Extract country codes from header (columns 2+)
    # Handle both formats:
    # - Simple: "US", "GB", "FR"
    # - With zones: "CA 1", "CA 2", "AU 3" (extract first 2 chars)
    country_cols = []
    for col_idx in range(2, df.shape[1]):
        val = df.iloc[header_row_idx, col_idx]
        if pd.isna(val):
            continue

        code_str = str(val).strip().upper()

        # Extract ISO2 code (first 2 chars if alpha)
        if len(code_str) >= 2 and code_str[:2].isalpha():
            iso2_code = code_str[:2]
            country_cols.append((col_idx, iso2_code, code_str))  # (col, iso2, full_label)

    print(f"   Found {len(country_cols)} zones/countries in {sheet_name}")

    # Data starts after weight header
    weight_header_row_idx = header_row_idx + 1
    data_start = weight_header_row_idx + 1

    # Find "Price per kg." row (with fallback)
    price_per_kg_mask = df.iloc[:, 0].astype(str).str.contains("Price per kg", na=False, case=False)
    price_per_kg_matches = df.index[price_per_kg_mask].tolist()
    price_per_kg_row = price_per_kg_matches[0] if price_per_kg_matches else len(df) - 2

    # Extract FIXED bands
    records = []
    weight_col = 1  # Column with weights

    for row_idx in range(data_start, price_per_kg_row):
        w = df.iloc[row_idx, weight_col]
        try:
            weight_kg = float(str(w).strip())
        except (ValueError, TypeError):
            continue

        for col_idx, country_iso2, full_label in country_cols:
            price_val = df.iloc[row_idx, col_idx]
            if pd.isna(price_val):
                continue

            try:
                price = float(price_val)
            except (ValueError, TypeError):
                continue

            # Determine origin and destination based on service type
            if service_def["is_destination"]:
                # Import: countries are origins, fixed location is destination
                record_origin = country_iso2
                record_dest = dest_iso2_fixed
            else:
                # Export: fixed location is origin, countries are destinations
                record_origin = origin_iso2_fixed
                record_dest = country_iso2

            records.append({
                "service_code": service_def["code"],
                "origin_iso2": record_origin,
                "dest_iso2": record_dest,
                "zone_label": full_label,  # Keep zone info for debugging
                "band_type": "FIXED",
                "min_weight_kg": weight_kg,
                "max_weight_kg": weight_kg,
                "price": price,
                "price_per_kg": None,
                "min_charge": None,
            })

    return pd.DataFrame(records)


def extract_all_services(xlsx_path: str = DEFAULT_XLSX_PATH) -> pd.DataFrame:
    """
    Extract all UPS services from Excel

    For services with multiple zones per country (e.g., CA 1, CA 2),
    we take the MINIMUM price per (service, origin, dest, weight) combination.

    Returns:
        Combined DataFrame with all services
    """
    print("\n📦 Extracting UPS services from Excel...")
    print(f"📄 File: {xlsx_path}\n")

    all_records = []

    for service_def in SERVICES:
        print(f"🔍 Processing: {service_def['label']}")
        df = extract_raw_service(xlsx_path, service_def)

        if not df.empty:
            all_records.append(df)
            print(f"   ✅ Extracted {len(df)} pricing bands (with zones)")
        else:
            print(f"   ⚠️  No data extracted")

    if not all_records:
        raise ValueError("No data extracted from any service!")

    combined_df = pd.concat(all_records, ignore_index=True)

    # Handle multiple zones: take MIN price per (service, origin, dest, weight)
    print(f"\n📊 Deduplicating zones (taking minimum price per country)...")
    original_count = len(combined_df)

    combined_df = combined_df.groupby(
        ['service_code', 'origin_iso2', 'dest_iso2', 'min_weight_kg', 'max_weight_kg', 'band_type'],
        as_index=False
    ).agg({
        'price': 'min',  # Take minimum price across zones
        'price_per_kg': 'first',
        'min_charge': 'first',
        'zone_label': lambda x: ', '.join(sorted(set(x)))  # Keep all zone labels for reference
    })

    deduplicated_count = len(combined_df)
    zones_removed = original_count - deduplicated_count

    if zones_removed > 0:
        print(f"   ✅ Removed {zones_removed} duplicate zones (kept minimum prices)")

    # Save intermediate CSV
    intermediate_dir = Path(__file__).parent.parent.parent / "data" / "intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    intermediate_csv = intermediate_dir / "ups_all_services_raw.csv"
    combined_df.to_csv(intermediate_csv, index=False)

    print(f"\n✅ Total unique pricing bands: {len(combined_df)}")
    print(f"💾 Saved to: {intermediate_csv}")

    return combined_df


def normalize_to_canonical(
    raw_df: Optional[pd.DataFrame] = None,
    carrier_id: int = 4  # UPS
) -> None:
    """Normalize to canonical CSVs"""

    if raw_df is None:
        raw_df = extract_all_services()

    normalized_dir = Path(__file__).parent.parent.parent / "data" / "normalized"

    services_file = normalized_dir / "services.csv"
    scopes_file = normalized_dir / "tariff_scopes.csv"
    scope_countries_file = normalized_dir / "tariff_scope_countries.csv"
    bands_file = normalized_dir / "tariff_bands.csv"

    # Get next available IDs
    def get_max_id(csv_file: Path, id_column: str) -> int:
        if not csv_file.exists():
            return 0
        df = pd.read_csv(csv_file)
        if df.empty:
            return 0
        return int(df[id_column].max())

    next_service_id = get_max_id(services_file, 'service_id') + 1
    next_scope_id = get_max_id(scopes_file, 'scope_id') + 1
    next_band_id = get_max_id(bands_file, 'band_id') + 1

    print("\n📋 Normalizing to canonical CSVs...")

    # Track service_code -> service_id mapping
    service_code_to_id = {}
    services_data = []
    scopes_data = []
    scope_countries_data = []
    bands_data = []

    # Group by service
    for service_code, service_group in raw_df.groupby('service_code'):
        # Find service definition
        service_def = next(s for s in SERVICES if s['code'] == service_code)

        # Create service entry
        service_id = next_service_id
        service_code_to_id[service_code] = service_id
        next_service_id += 1

        services_data.append({
            'service_id': service_id,
            'carrier_id': carrier_id,
            'code': service_def['code'],
            'label': service_def['label'],
            'direction': service_def['direction'],
            'origin_iso2': service_def['origin_iso2'],
            'incoterm': service_def['incoterm'],
            'service_type': service_def['service_type'],
            'max_weight_kg': service_def['max_weight_kg'],
            'volumetric_divisor': 5000,
            'active_from': '2022-04-10',
            'active_to': ''
        })

        print(f"\n🔧 Service: {service_def['label']} (ID: {service_id})")

        # For EXPORT services: group by destination country
        # For IMPORT services: group by origin country
        if service_def['direction'] == 'EXPORT':
            country_col = 'dest_iso2'
        else:
            country_col = 'origin_iso2'

        # Create scopes per country
        for country_iso2, country_group in service_group.groupby(country_col):
            scope_id = next_scope_id
            next_scope_id += 1

            scopes_data.append({
                'scope_id': scope_id,
                'service_id': service_id,
                'code': f"{service_code}_{country_iso2}",
                'description': f"{service_def['label']} → {country_iso2}",
                'is_catch_all': False
            })

            scope_countries_data.append({
                'scope_id': scope_id,
                'country_iso2': country_iso2
            })

            # FIXED bands
            fixed_rows = country_group[country_group['band_type'] == 'FIXED']
            for _, row in fixed_rows.iterrows():
                bands_data.append({
                    'band_id': next_band_id,
                    'scope_id': scope_id,
                    'min_weight_kg': row['min_weight_kg'],
                    'max_weight_kg': row['max_weight_kg'],
                    'base_amount': round(row['price'], 2),
                    'amount_per_kg': 0.00,
                    'is_min_charge': False
                })
                next_band_id += 1

        country_count = service_group[country_col].nunique()
        band_count = len(service_group)
        print(f"   ✅ {country_count} countries, {band_count} bands")

    # Append to CSVs
    def append_csv(file_path: Path, data: List[Dict], fieldnames: List[str]):
        file_exists = file_path.exists()

        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for row in data:
                writer.writerow(row)

    print("\n💾 Writing to normalized CSVs...")

    append_csv(services_file, services_data, [
        'service_id', 'carrier_id', 'code', 'label', 'direction', 'origin_iso2',
        'incoterm', 'service_type', 'max_weight_kg', 'volumetric_divisor',
        'active_from', 'active_to'
    ])
    print(f"   ✅ services.csv: +{len(services_data)} services")

    append_csv(scopes_file, scopes_data, [
        'scope_id', 'service_id', 'code', 'description', 'is_catch_all'
    ])
    print(f"   ✅ tariff_scopes.csv: +{len(scopes_data)} scopes")

    append_csv(scope_countries_file, scope_countries_data, [
        'scope_id', 'country_iso2'
    ])
    print(f"   ✅ tariff_scope_countries.csv: +{len(scope_countries_data)} mappings")

    append_csv(bands_file, bands_data, [
        'band_id', 'scope_id', 'min_weight_kg', 'max_weight_kg',
        'base_amount', 'amount_per_kg', 'is_min_charge'
    ])
    print(f"   ✅ tariff_bands.csv: +{len(bands_data)} bands")

    print("\n✅ Normalization complete!")


def main():
    """Main entry point"""
    print("="*70)
    print("UPS All Services ETL")
    print("="*70)

    # Extract
    raw_df = extract_all_services()

    # Normalize
    normalize_to_canonical(raw_df)

    print("\n" + "="*70)
    print("✅ ETL Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
