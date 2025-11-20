#!/usr/bin/env python3
"""
UPS ETL Pipeline
Extract rate tables from UPS Excel file and normalize to canonical schema.

Author: Benjamin Belaga
Date: 2025-11-20
"""

import pandas as pd
import sys
from pathlib import Path
from decimal import Decimal
from typing import List, Tuple, Dict
import csv

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.base_schema import (
    Carrier, Service, TariffScope, TariffScopeCountry, TariffBand, SurchargeRule
)


# ============================================================================
# UPS Zone → Country Mapping (Partial from Excel)
# ============================================================================

# Based on information available in Excel sheet 04_Expédition-Express Saver
# INCOMPLETE - Many zones don't have explicit country mappings in the Excel
UPS_ZONE_COUNTRIES_PARTIAL = {
    # WW (Worldwide) market zones with known countries
    "11": ["CN", "ID", "JP", "MY", "PH", "TW"],  # China, Indonesia, Japan, Malaysia, Philippines, Taiwan
    "12": ["VN"],  # Vietnam
    "13": ["KH", "LA"],  # Cambodia, Laos
    "703": ["GB"],  # United Kingdom

    # TB (Trade Bloc) and WW zones without explicit mappings in Excel
    # These will need to be populated with official UPS zone charts
    "3": [],  # TB Zone 3 - Unknown countries
    "4": [],  # TB Zone 4 - Unknown countries
    "5": [],  # TB Zone 5 - Unknown countries
    "6": [],  # WW Zone 6 - Unknown countries
    "7": [],  # WW Zone 7 - Unknown countries
    "8": [],  # WW Zone 8 - Unknown countries (both TB and WW have zone 8)
    "9": [],  # WW Zone 9 - Unknown countries
    "10": [],  # WW Zone 10 - Unknown countries
    "51": [],  # TB Zone 51 - Unknown countries
    "52": [],  # TB Zone 52 - Unknown countries
    "505": [],  # TB Zone 505 - Unknown countries
}


# ============================================================================
# Extract Express Saver Rates
# ============================================================================

def extract_express_saver_rates(excel_path: str) -> pd.DataFrame:
    """
    Extract UPS Express Saver rate tables from sheet 04.

    Structure:
    - Row 19: Marché (Market: TB, WW)
    - Row 20: Zones (3, 4, 5, 8, 51, 52, 505, 6, 7, 8, 9, 10, 11, 12, 13, 703...)
    - Row 21: Destination (partial country names)
    - Row 22: Headers (Type de tarif, kg)
    - Row 23+: Rates (weight in col 2, prices in cols 3+)
    """
    sheet_name = "04_Expédition-Express Saver"
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    # Extract zone info from header rows
    row_market = df.iloc[18]  # Row 19
    row_zones = df.iloc[19]   # Row 20
    row_dest = df.iloc[20]    # Row 21

    # Build zone mapping: col_idx → zone
    zone_map = {}
    for col_idx in range(3, len(row_zones)):
        zone = row_zones[col_idx]
        if pd.notna(zone):
            zone_map[col_idx] = str(int(zone))

    print(f"Found {len(zone_map)} zone columns in Express Saver sheet")

    # Extract rate rows (starting from row 23)
    rates = []
    for row_idx in range(22, len(df)):  # Row 23 onwards
        row = df.iloc[row_idx]

        # Column 0: Package type (Env, Doc, Pkg, Doc & Pkg)
        pkg_type = row[0]
        if pd.isna(pkg_type):
            break  # End of table

        # Column 2: Weight (kg)
        weight = row[2]
        if pd.isna(weight):
            continue

        try:
            weight_kg = float(weight)
        except (ValueError, TypeError):
            continue

        # Extract prices for each zone
        for col_idx, zone in zone_map.items():
            price = row[col_idx]
            if pd.notna(price) and price != "":
                try:
                    price_eur = float(price)
                    rates.append({
                        "service": "EXPRESS_SAVER",
                        "zone": zone,
                        "weight_kg": weight_kg,
                        "price_eur": price_eur,
                        "package_type": pkg_type
                    })
                except (ValueError, TypeError):
                    pass

    rates_df = pd.DataFrame(rates)
    print(f"Extracted {len(rates_df)} Express Saver rates")
    return rates_df


# ============================================================================
# Extract Standard Rates
# ============================================================================

def extract_standard_rates(excel_path: str) -> pd.DataFrame:
    """
    Extract UPS Standard rate tables from sheet 06.

    Similar structure to Express Saver but with different zones.
    """
    sheet_name = "06_Expédition-Standard mono-col"
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    # Extract zone info
    row_market = df.iloc[18]  # Row 19
    row_zones = df.iloc[19]   # Row 20

    zone_map = {}
    for col_idx in range(3, len(row_zones)):
        zone = row_zones[col_idx]
        if pd.notna(zone):
            # Handle "4 (Corse)" format
            zone_str = str(zone).split()[0]  # Take first part
            try:
                zone_map[col_idx] = str(int(float(zone_str)))
            except (ValueError, TypeError):
                pass

    print(f"Found {len(zone_map)} zone columns in Standard sheet")

    # Extract rates
    rates = []
    for row_idx in range(22, len(df)):  # Row 23 onwards
        row = df.iloc[row_idx]

        pkg_type = row[0]
        if pd.isna(pkg_type):
            break

        weight = row[2]
        if pd.isna(weight):
            continue

        try:
            weight_kg = float(weight)
        except (ValueError, TypeError):
            continue

        for col_idx, zone in zone_map.items():
            price = row[col_idx]
            if pd.notna(price) and price != "":
                try:
                    price_eur = float(price)
                    rates.append({
                        "service": "STANDARD",
                        "zone": zone,
                        "weight_kg": weight_kg,
                        "price_eur": price_eur,
                        "package_type": pkg_type
                    })
                except (ValueError, TypeError):
                    pass

    rates_df = pd.DataFrame(rates)
    print(f"Extracted {len(rates_df)} Standard rates")
    return rates_df


# ============================================================================
# Normalize to Canonical Schema
# ============================================================================

def normalize_to_canonical():
    """
    Extract UPS data and normalize to canonical schema.
    Appends to existing normalized CSV files.
    """
    excel_path = PROJECT_ROOT / "data" / "raw" / "PROPOSITION TARIFAIRE YOYAKU 2023.xlsx"
    intermediate_dir = PROJECT_ROOT / "data" / "intermediate"
    normalized_dir = PROJECT_ROOT / "data" / "normalized"

    intermediate_dir.mkdir(exist_ok=True, parents=True)
    normalized_dir.mkdir(exist_ok=True, parents=True)

    print("=" * 80)
    print("UPS ETL PIPELINE")
    print("=" * 80)

    # Step 1: Extract rates
    print("\n[1] Extracting Express Saver rates...")
    express_saver_df = extract_express_saver_rates(str(excel_path))

    print("\n[2] Extracting Standard rates...")
    standard_df = extract_standard_rates(str(excel_path))

    # Combine
    all_rates_df = pd.concat([express_saver_df, standard_df], ignore_index=True)

    # Save intermediate
    intermediate_file = intermediate_dir / "ups_rates.csv"
    all_rates_df.to_csv(intermediate_file, index=False)
    print(f"\n✅ Saved intermediate: {intermediate_file}")
    print(f"   Total rates: {len(all_rates_df)}")

    # Step 2: Normalize
    print("\n[3] Normalizing to canonical schema...")

    # Read existing data to get next IDs
    carriers_file = normalized_dir / "carriers.csv"
    services_file = normalized_dir / "services.csv"
    scopes_file = normalized_dir / "tariff_scopes.csv"
    scope_countries_file = normalized_dir / "tariff_scope_countries.csv"
    bands_file = normalized_dir / "tariff_bands.csv"
    surcharges_file = normalized_dir / "surcharge_rules.csv"

    # Determine next IDs
    next_carrier_id = 1
    next_service_id = 1
    next_scope_id = 1
    next_band_id = 1
    next_surcharge_id = 1

    if carriers_file.exists():
        existing = pd.read_csv(carriers_file)
        if len(existing) > 0:
            next_carrier_id = existing['carrier_id'].max() + 1

    if services_file.exists():
        existing = pd.read_csv(services_file)
        if len(existing) > 0:
            next_service_id = existing['service_id'].max() + 1

    if scopes_file.exists():
        existing = pd.read_csv(scopes_file)
        if len(existing) > 0:
            next_scope_id = existing['scope_id'].max() + 1

    if bands_file.exists():
        existing = pd.read_csv(bands_file)
        if len(existing) > 0:
            next_band_id = existing['band_id'].max() + 1

    if surcharges_file.exists():
        existing = pd.read_csv(surcharges_file)
        if len(existing) > 0:
            next_surcharge_id = existing['surcharge_id'].max() + 1

    # Create Carrier
    carrier_id = next_carrier_id
    carrier_code = "UPS"
    carrier_name = "UPS"
    carrier_currency = "EUR"

    # Create Services
    service_express_id = next_service_id
    service_standard_id = next_service_id + 1

    services = [
        {
            'service_id': service_express_id,
            'carrier_id': carrier_id,
            'code': "UPS_EXPRESS_SAVER",
            'label': "UPS Express Saver",
            'direction': "EXPORT",
            'origin_iso2': "FR",
            'incoterm': "DAP",
            'service_type': "EXPRESS",
            'max_weight_kg': 70.0,
            'volumetric_divisor': 5000,
            'active_from': "2023-04-22",
            'active_to': ""
        },
        {
            'service_id': service_standard_id,
            'carrier_id': carrier_id,
            'code': "UPS_STANDARD",
            'label': "UPS Standard",
            'direction': "EXPORT",
            'origin_iso2': "FR",
            'incoterm': "DAP",
            'service_type': "GROUND",
            'max_weight_kg': 70.0,
            'volumetric_divisor': 5000,
            'active_from': "2023-04-22",
            'active_to': ""
        }
    ]

    service_map = {
        "EXPRESS_SAVER": service_express_id,
        "STANDARD": service_standard_id
    }

    # Create Scopes (one per service+zone combination)
    zones = sorted(all_rates_df['zone'].unique(), key=lambda x: int(x) if x.isdigit() else 999)
    scopes = []
    scope_map = {}  # (service, zone) → scope_id

    scope_id_counter = next_scope_id
    for service_name, service_id in service_map.items():
        for zone in zones:
            scope_id = scope_id_counter
            scope_code = f"UPS_{service_name}_ZONE_{zone}"
            scope_desc = f"UPS {service_name.replace('_', ' ').title()} - Zone {zone}"

            scopes.append({
                'scope_id': scope_id,
                'service_id': service_id,
                'code': scope_code,
                'description': scope_desc,
                'is_catch_all': False
            })

            scope_map[(service_name, zone)] = scope_id
            scope_id_counter += 1

    # Create Scope Countries (based on partial mapping)
    scope_countries = []
    for service_name, service_id in service_map.items():
        for zone, countries in UPS_ZONE_COUNTRIES_PARTIAL.items():
            if (service_name, zone) in scope_map and countries:
                scope_id = scope_map[(service_name, zone)]
                for country_iso2 in countries:
                    scope_countries.append({
                        'scope_id': scope_id,
                        'country_iso2': country_iso2
                    })

    print(f"   WARNING: Only {len(scope_countries)} country mappings available")
    print(f"   Most UPS zones don't have country mappings in the Excel file")
    print(f"   You'll need to provide official UPS zone charts to complete the mapping")

    # Create Tariff Bands
    bands = []
    band_id = next_band_id

    for _, row in all_rates_df.iterrows():
        service_name = row['service']
        zone = row['zone']
        scope_id = scope_map[(service_name, zone)]
        weight_kg = float(row['weight_kg'])
        price_eur = float(row['price_eur'])

        # UPS uses fixed price per weight band (not linear formula)
        bands.append({
            'band_id': band_id,
            'scope_id': scope_id,
            'min_weight_kg': weight_kg,
            'max_weight_kg': weight_kg,  # Fixed price for this exact weight
            'base_amount': price_eur,
            'amount_per_kg': 0.0,  # Fixed price
            'is_min_charge': False
        })

        band_id += 1

    # Create Surcharge Rules (from spec)
    # Note: These are documented surcharges but not implemented in pricing logic yet
    surcharges = [
        {
            'surcharge_id': next_surcharge_id,
            'service_id': service_map["EXPRESS_SAVER"],
            'name': "UPS Fuel Discount",
            'kind': "PERCENT",
            'basis': "FREIGHT",
            'value': -30.0,  # -30% (discount)
            'conditions': "{}"
        },
        {
            'surcharge_id': next_surcharge_id + 1,
            'service_id': service_map["EXPRESS_SAVER"],
            'name': "UPS Residential Discount",
            'kind': "PERCENT",
            'basis': "FREIGHT",
            'value': -50.0,  # -50% (discount)
            'conditions': '{"delivery_type": "residential"}'
        },
        {
            'surcharge_id': next_surcharge_id + 2,
            'service_id': service_map["STANDARD"],
            'name': "UPS Weekly Delivery Surcharge",
            'kind': "PERCENT",
            'basis': "FREIGHT",
            'value': 100.0,  # +100%
            'conditions': '{"delivery_frequency": "weekly"}'
        }
    ]

    # Write to CSVs (append mode)
    print("\n[4] Writing normalized data...")

    # Carriers
    with open(carriers_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if carriers_file.stat().st_size == 0:  # Empty file, write header
            writer.writerow(['carrier_id', 'code', 'name', 'currency'])
        writer.writerow([carrier_id, carrier_code, carrier_name, carrier_currency])
    print(f"   ✅ Appended to {carriers_file.name}")

    # Services
    with open(services_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if services_file.stat().st_size == 0:
            writer.writerow(['service_id', 'carrier_id', 'code', 'label', 'direction', 'origin_iso2', 'incoterm', 'service_type', 'max_weight_kg', 'volumetric_divisor', 'active_from', 'active_to'])
        for svc in services:
            writer.writerow([
                svc['service_id'], svc['carrier_id'], svc['code'], svc['label'],
                svc['direction'], svc['origin_iso2'], svc['incoterm'], svc['service_type'],
                svc['max_weight_kg'], svc['volumetric_divisor'], svc['active_from'], svc['active_to']
            ])
    print(f"   ✅ Appended to {services_file.name}")

    # Scopes
    with open(scopes_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if scopes_file.stat().st_size == 0:
            writer.writerow(['scope_id', 'service_id', 'code', 'description', 'is_catch_all'])
        for scope in scopes:
            writer.writerow([scope['scope_id'], scope['service_id'], scope['code'], scope['description'], scope['is_catch_all']])
    print(f"   ✅ Appended to {scopes_file.name} ({len(scopes)} scopes)")

    # Scope Countries
    with open(scope_countries_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if scope_countries_file.stat().st_size == 0:
            writer.writerow(['scope_id', 'country_iso2'])
        for sc in scope_countries:
            writer.writerow([sc['scope_id'], sc['country_iso2']])
    print(f"   ⚠️  Appended to {scope_countries_file.name} ({len(scope_countries)} mappings - INCOMPLETE)")

    # Bands
    with open(bands_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if bands_file.stat().st_size == 0:
            writer.writerow(['band_id', 'scope_id', 'min_weight_kg', 'max_weight_kg', 'base_amount', 'amount_per_kg', 'is_min_charge'])
        for band in bands:
            writer.writerow([
                band['band_id'], band['scope_id'],
                band['min_weight_kg'], band['max_weight_kg'],
                band['base_amount'], band['amount_per_kg'], band['is_min_charge']
            ])
    print(f"   ✅ Appended to {bands_file.name} ({len(bands)} bands)")

    # Surcharges
    with open(surcharges_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if surcharges_file.stat().st_size == 0:
            writer.writerow(['surcharge_id', 'service_id', 'name', 'kind', 'basis', 'value', 'conditions'])
        for surcharge in surcharges:
            writer.writerow([
                surcharge['surcharge_id'], surcharge['service_id'],
                surcharge['name'], surcharge['kind'],
                surcharge['basis'], surcharge['value'], surcharge['conditions']
            ])
    print(f"   ✅ Appended to {surcharges_file.name} ({len(surcharges)} rules)")

    print("\n" + "=" * 80)
    print("✅ UPS ETL COMPLETE")
    print("=" * 80)
    print(f"Carrier: UPS")
    print(f"Services: {len(services)} (Express Saver, Standard)")
    print(f"Zones: {len(scopes)}")
    print(f"Country Mappings: {len(scope_countries)} ⚠️ INCOMPLETE")
    print(f"Tariff Bands: {len(bands)}")
    print(f"Surcharges: {len(surcharges)}")
    print()
    print("⚠️  NOTE: Most zones don't have country mappings.")
    print("   You'll need official UPS zone charts to complete the mapping.")
    print()


if __name__ == "__main__":
    normalize_to_canonical()
