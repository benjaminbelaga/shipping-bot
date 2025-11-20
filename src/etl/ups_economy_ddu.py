"""
UPS Economy DDU Export ETL
Extracts pricing from YOYAKU UPS Economy DDU proposal Excel
Follows canonical data model defined in ARCHITECTURE.md

Input: Excel file with "DDU Export - Output" sheet
Structure:
    Row 0: Service name, Origin (FR)
    Row 7: "Ctry / Zone →" + ISO2 country codes (RS, AE, TW, etc.)
    Row 8: "Weight (up to) ↓" + zone codes
    Row 9+: Weight bands (0.1-20.0 kg) with prices per country
    Row ~55: "Price per kg." with per-kg rates
    Row ~56: "Minimum" with minimum charges

Output: Appends to normalized CSVs
- services.csv (UPS_ECONOMY_DDU_EXPORT_FR)
- tariff_scopes.csv (one scope per destination country)
- tariff_scope_countries.csv (scope→country mappings)
- tariff_bands.csv (FIXED bands 0.1-20kg + PERKG band >20kg)
"""

import pandas as pd
import csv
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from decimal import Decimal


# Configuration
DEFAULT_XLSX_PATH = "/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/PROPAL YOYAKU ECONOMY DDU (1).xlsx"
DEFAULT_SHEET_EXPORT = "DDU Export - Output"


def extract_raw(
    xlsx_path: str = DEFAULT_XLSX_PATH,
    sheet_name: str = DEFAULT_SHEET_EXPORT
) -> pd.DataFrame:
    """
    Extract raw pricing data from UPS Economy DDU Excel sheet

    Args:
        xlsx_path: Path to Excel file
        sheet_name: Sheet name to parse (default: "DDU Export - Output")

    Returns:
        DataFrame with columns:
        - origin_iso2: FR
        - dest_iso2: RS, AE, TW, etc.
        - band_type: FIXED or PERKG
        - min_weight_kg: minimum weight for band
        - max_weight_kg: maximum weight for band
        - price: fixed price (for FIXED bands)
        - price_per_kg: per-kg rate (for PERKG bands)
        - min_charge: minimum charge (for PERKG bands)

    Raises:
        FileNotFoundError: If Excel file not found
        ValueError: If sheet structure is invalid
    """
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(
            f"UPS Economy DDU Excel not found: {xlsx_path}\n"
            f"Please ensure the file exists at this location."
        )

    print(f"📥 Reading Excel: {xlsx_path}")
    print(f"📄 Sheet: {sheet_name}")

    try:
        # Read sheet without headers
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None)

        # 1. Extract origin and service metadata (Row 0)
        origin_iso2 = str(df.iloc[0, 1]).strip()  # Cell B1 = 'FR'
        service_name = str(df.iloc[0, 0])  # Cell A1 = 'Service: UPS® Economy DDU'

        print(f"✅ Origin: {origin_iso2}")
        print(f"✅ Service: {service_name}")

        # 2. Find header row with "Ctry / Zone →"
        header_mask = df.iloc[:, 1].astype(str).str.contains("Ctry / Zone", na=False, case=False)
        header_row_idx = df.index[header_mask].tolist()[0]
        print(f"✅ Header row found at index: {header_row_idx}")

        # 3. Weight header is next row ("Weight (up to) ↓")
        weight_header_row_idx = header_row_idx + 1

        # 4. Extract country codes from header row (columns 2+)
        country_cols = []
        for col_idx in range(2, df.shape[1]):
            val = df.iloc[header_row_idx, col_idx]
            if pd.isna(val):
                continue
            code = str(val).strip().upper()

            # Simple check: ISO2 codes are 2 uppercase letters
            if len(code) == 2 and code.isalpha():
                country_cols.append((col_idx, code))

        print(f"✅ Found {len(country_cols)} countries: {[c[1] for c in country_cols[:10]]}...")

        # 5. Data starts after weight header
        data_start = weight_header_row_idx + 1

        # 6. Find "Price per kg." and "Minimum" rows
        price_per_kg_mask = df.iloc[:, 0].astype(str).str.contains("Price per kg", na=False, case=False)
        minimum_mask = df.iloc[:, 0].astype(str).str.contains("Minimum", na=False, case=False)

        price_per_kg_matches = df.index[price_per_kg_mask].tolist()
        minimum_matches = df.index[minimum_mask].tolist()

        # If not found, assume data goes to end of sheet
        price_per_kg_row = price_per_kg_matches[0] if price_per_kg_matches else len(df) - 2
        minimum_row = minimum_matches[0] if minimum_matches else len(df) - 1

        print(f"✅ Price per kg row: {price_per_kg_row} {'(found)' if price_per_kg_matches else '(not found, using default)'}")
        print(f"✅ Minimum row: {minimum_row} {'(found)' if minimum_matches else '(not found, using default)'}")

        # 7. Weight column is column 1 (header "FR")
        weight_col = 1

        # 8. Extract FIXED bands (0.1 - 20.0 kg)
        records = []

        for row_idx in range(data_start, price_per_kg_row):
            w = df.iloc[row_idx, weight_col]

            # Parse weight
            try:
                weight_kg = float(str(w).strip())
            except (ValueError, TypeError):
                continue  # Skip invalid weight rows

            # Extract price for each country
            for col_idx, dest_iso2 in country_cols:
                price_val = df.iloc[row_idx, col_idx]

                if pd.isna(price_val):
                    continue  # Skip empty cells

                try:
                    price = float(price_val)
                except (ValueError, TypeError):
                    continue

                records.append({
                    "origin_iso2": origin_iso2,
                    "dest_iso2": dest_iso2,
                    "band_type": "FIXED",
                    "min_weight_kg": weight_kg,
                    "max_weight_kg": weight_kg,
                    "price": price,
                    "price_per_kg": None,
                    "min_charge": None,
                })

        print(f"✅ Extracted {len(records)} FIXED band records")

        # 9. Extract PERKG bands (>20 kg with per-kg + minimum)
        if records:
            last_band_weight = max(r["min_weight_kg"] for r in records)
        else:
            last_band_weight = 20.0

        perkg_count = 0
        for col_idx, dest_iso2 in country_cols:
            price_per_kg_val = df.iloc[price_per_kg_row, col_idx]
            minimum_val = df.iloc[minimum_row, col_idx]

            if pd.isna(price_per_kg_val) or pd.isna(minimum_val):
                continue  # Skip if either value missing

            try:
                price_per_kg = float(price_per_kg_val)
                min_charge = float(minimum_val)
            except (ValueError, TypeError):
                continue

            records.append({
                "origin_iso2": origin_iso2,
                "dest_iso2": dest_iso2,
                "band_type": "PERKG",
                "min_weight_kg": last_band_weight,
                "max_weight_kg": 99999.0,  # Effectively unlimited
                "price": None,
                "price_per_kg": price_per_kg,
                "min_charge": min_charge,
            })
            perkg_count += 1

        print(f"✅ Extracted {perkg_count} PERKG band records")

        # 10. Convert to DataFrame
        raw_df = pd.DataFrame(records)

        # Save intermediate CSV for debugging
        intermediate_dir = Path(__file__).parent.parent.parent / "data" / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)

        intermediate_csv = intermediate_dir / "ups_economy_ddu_raw.csv"
        raw_df.to_csv(intermediate_csv, index=False)
        print(f"💾 Saved intermediate CSV: {intermediate_csv}")

        return raw_df

    except Exception as e:
        raise ValueError(f"Failed to parse Excel: {e}")


def normalize_to_canonical(
    raw_df: Optional[pd.DataFrame] = None,
    carrier_id: int = 4,  # UPS
    service_code: str = "UPS_ECONOMY_DDU_EXPORT_FR"
) -> None:
    """
    Normalize UPS Economy DDU raw data to canonical CSV files

    Args:
        raw_df: DataFrame from extract_raw() (or loads from intermediate CSV)
        carrier_id: UPS carrier ID (default 4)
        service_code: Service code (default UPS_ECONOMY_DDU_EXPORT_FR)

    Appends to:
        - data/normalized/services.csv
        - data/normalized/tariff_scopes.csv
        - data/normalized/tariff_scope_countries.csv
        - data/normalized/tariff_bands.csv
    """
    # Load raw data if not provided
    if raw_df is None:
        intermediate_csv = Path(__file__).parent.parent.parent / "data" / "intermediate" / "ups_economy_ddu_raw.csv"
        raw_df = pd.read_csv(intermediate_csv)

    print("\n" + "=" * 60)
    print("🔄 NORMALIZING TO CANONICAL MODEL")
    print("=" * 60)

    normalized_dir = Path(__file__).parent.parent.parent / "data" / "normalized"

    carriers_file = normalized_dir / "carriers.csv"
    services_file = normalized_dir / "services.csv"
    scopes_file = normalized_dir / "tariff_scopes.csv"
    scope_countries_file = normalized_dir / "tariff_scope_countries.csv"
    bands_file = normalized_dir / "tariff_bands.csv"

    # 1. Get next available IDs
    def get_max_id(csv_file: Path, id_column: str) -> int:
        """Get max ID from CSV file"""
        if not csv_file.exists():
            return 0
        df = pd.read_csv(csv_file)
        if df.empty:
            return 0
        return int(df[id_column].max())

    next_service_id = get_max_id(services_file, 'service_id') + 1
    next_scope_id = get_max_id(scopes_file, 'scope_id') + 1
    next_band_id = get_max_id(bands_file, 'band_id') + 1

    print(f"📊 Next IDs: service={next_service_id}, scope={next_scope_id}, band={next_band_id}")

    # 2. Create service entry (if not exists)
    service_id = next_service_id

    services_data = [{
        'service_id': service_id,
        'carrier_id': carrier_id,
        'code': service_code,
        'label': 'UPS Economy DDU Export FR',
        'direction': 'EXPORT',
        'origin_iso2': 'FR',
        'incoterm': 'DDU',
        'service_type': 'ECONOMY',
        'max_weight_kg': 70,
        'volumetric_divisor': 5000,
        'active_from': '2022-04-10',
        'active_to': ''
    }]

    # Check if service already exists
    if services_file.exists():
        existing_services = pd.read_csv(services_file)
        if service_code in existing_services['code'].values:
            service_id = int(existing_services[existing_services['code'] == service_code]['service_id'].iloc[0])
            print(f"✅ Service already exists: {service_code} (ID={service_id})")
            services_data = []  # Don't append
        else:
            print(f"✅ Creating new service: {service_code} (ID={service_id})")
    else:
        print(f"✅ Creating new service: {service_code} (ID={service_id})")

    # 3. Create scopes, mappings, and bands per country
    scopes_data = []
    scope_countries_data = []
    bands_data = []

    for dest_iso2, group in raw_df.groupby('dest_iso2'):
        scope_id = next_scope_id
        next_scope_id += 1

        scope_code = f"UPS_ECO_DDU_FR_{dest_iso2}"
        scope_desc = f"UPS Economy DDU Export FR→{dest_iso2}"

        scopes_data.append({
            'scope_id': scope_id,
            'service_id': service_id,
            'code': scope_code,
            'description': scope_desc,
            'is_catch_all': False
        })

        scope_countries_data.append({
            'scope_id': scope_id,
            'country_iso2': dest_iso2
        })

        # FIXED bands (one per weight)
        fixed_rows = group[group['band_type'] == 'FIXED']
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

        # PERKG band (one per country)
        perkg_rows = group[group['band_type'] == 'PERKG']
        if not perkg_rows.empty:
            row = perkg_rows.iloc[0]
            bands_data.append({
                'band_id': next_band_id,
                'scope_id': scope_id,
                'min_weight_kg': row['min_weight_kg'],
                'max_weight_kg': row['max_weight_kg'],
                'base_amount': round(row['min_charge'], 2),
                'amount_per_kg': round(row['price_per_kg'], 2),
                'is_min_charge': True
            })
            next_band_id += 1

    print(f"✅ Generated {len(scopes_data)} scopes")
    print(f"✅ Generated {len(scope_countries_data)} country mappings")
    print(f"✅ Generated {len(bands_data)} tariff bands")

    # 4. Append to CSV files
    def append_csv(file_path: Path, data: List[Dict], fieldnames: List[str]):
        """Append data to CSV file"""
        if not data:
            return

        file_exists = file_path.exists()

        with open(file_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for row in data:
                writer.writerow(row)

    # Append services
    if services_data:
        append_csv(services_file, services_data, [
            'service_id', 'carrier_id', 'code', 'label', 'direction', 'origin_iso2',
            'incoterm', 'service_type', 'max_weight_kg', 'volumetric_divisor',
            'active_from', 'active_to'
        ])
        print(f"💾 Appended {len(services_data)} service(s) to services.csv")

    # Append scopes
    append_csv(scopes_file, scopes_data, [
        'scope_id', 'service_id', 'code', 'description', 'is_catch_all'
    ])
    print(f"💾 Appended {len(scopes_data)} scopes to tariff_scopes.csv")

    # Append scope countries
    append_csv(scope_countries_file, scope_countries_data, [
        'scope_id', 'country_iso2'
    ])
    print(f"💾 Appended {len(scope_countries_data)} mappings to tariff_scope_countries.csv")

    # Append bands
    append_csv(bands_file, bands_data, [
        'band_id', 'scope_id', 'min_weight_kg', 'max_weight_kg', 'base_amount', 'amount_per_kg', 'is_min_charge'
    ])
    print(f"💾 Appended {len(bands_data)} bands to tariff_bands.csv")


def run_etl(xlsx_path: Optional[str] = None) -> None:
    """
    Run complete UPS Economy DDU ETL pipeline

    Args:
        xlsx_path: Path to Excel file (optional, uses default if None)

    Pipeline:
        1. Extract raw prices from Excel
        2. Normalize to canonical model
        3. Append to CSV files
    """
    print("=" * 60)
    print("UPS ECONOMY DDU ETL - Canonical Data Model")
    print("=" * 60)

    try:
        # Step 1: Extract
        print("\n📥 STEP 1: Extracting raw data from Excel...")
        raw_df = extract_raw(xlsx_path or DEFAULT_XLSX_PATH)

        # Step 2: Normalize
        print("\n🔄 STEP 2: Normalizing to canonical model...")
        normalize_to_canonical(raw_df)

        print("\n" + "=" * 60)
        print("✅ UPS ECONOMY DDU ETL COMPLETE")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Countries: {raw_df['dest_iso2'].nunique()}")
        print(f"   - Fixed bands: {len(raw_df[raw_df['band_type'] == 'FIXED'])}")
        print(f"   - Per-kg bands: {len(raw_df[raw_df['band_type'] == 'PERKG'])}")
        print(f"   - Service: UPS Economy DDU Export FR")
        print(f"\n🧪 Next step: Test pricing")
        print(f"   python3 -c \"from src.engine.engine import PricingEngine; e = PricingEngine(); print(e.price('US', 2.0))\"")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 To proceed:")
        print(f"   1. Ensure Excel file exists at: {DEFAULT_XLSX_PATH}")
        print(f"   2. Or provide custom path:")
        print(f"      python -m src.etl.ups_economy_ddu /path/to/excel.xlsx")

    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Check Excel format:")
        print("   - Sheet: 'DDU Export - Output'")
        print("   - Row 0: Origin (FR)")
        print("   - Row 7: 'Ctry / Zone →' + country codes")
        print("   - Row 8: 'Weight (up to) ↓'")
        print("   - Rows 9+: Weight bands with prices")


if __name__ == "__main__":
    import sys

    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_etl(xlsx_path)
