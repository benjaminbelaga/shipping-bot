"""
FedEx V2 ETL - From Clean CSV Extracts
Builds complete FedEx database from user-provided CSV files extracted from PDF

Input files:
- fedex_export_zone_chart.csv (193 countries × 7 services)
- fedex_ipe_export_rates.csv (861 IPE pricing rows)

Output:
- services.csv (FedEx services)
- tariff_scopes.csv (zones per service)
- tariff_scope_countries.csv (country mappings)
- tariff_bands.csv (pricing bands)
"""

import csv
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Service definitions (IPE, IP, IE, RE, IPF, IEF, REF)
FEDEX_SERVICES = {
    'IPE': {
        'code': 'FDX_IPE_EXPORT',
        'label': 'FedEx International Priority Express Export',
        'service_type': 'EXPRESS',
        'max_weight_kg': 70.0
    },
    'IP': {
        'code': 'FDX_IP_EXPORT',
        'label': 'FedEx International Priority Export',
        'service_type': 'EXPRESS',
        'max_weight_kg': 70.0
    },
    'IE': {
        'code': 'FDX_IE_EXPORT',
        'label': 'FedEx International Economy Export',
        'service_type': 'ECONOMY',
        'max_weight_kg': 70.0
    },
    'RE': {
        'code': 'FDX_RE_EXPORT',
        'label': 'FedEx Regional Economy Export',
        'service_type': 'ECONOMY',
        'max_weight_kg': 70.0
    },
    'IPF': {
        'code': 'FDX_IPF_EXPORT',
        'label': 'FedEx International Priority Freight Export',
        'service_type': 'EXPRESS',
        'max_weight_kg': 1000.0
    },
    'IEF': {
        'code': 'FDX_IEF_EXPORT',
        'label': 'FedEx International Economy Freight Export',
        'service_type': 'ECONOMY',
        'max_weight_kg': 1000.0
    },
    'REF': {
        'code': 'FDX_REF_EXPORT',
        'label': 'FedEx Regional Economy Freight Export',
        'service_type': 'ECONOMY',
        'max_weight_kg': 1000.0
    }
}

# FedEx is carrier_id=1
FEDEX_CARRIER_ID = 1

# Base service_id for FedEx services (will auto-increment)
# Check existing services.csv for next available ID
SERVICE_ID_BASE = 4  # Adjust based on existing data


class FedExV2ETL:
    def __init__(self, zone_chart_path: str, ipe_rates_path: str, output_dir: str):
        """
        Args:
            zone_chart_path: Path to fedex_export_zone_chart.csv
            ipe_rates_path: Path to fedex_ipe_export_rates.csv
            output_dir: Path to data/normalized/
        """
        self.zone_chart_path = Path(zone_chart_path)
        self.ipe_rates_path = Path(ipe_rates_path)
        self.output_dir = Path(output_dir)

        # Data structures
        self.services = {}  # service_code -> service_id
        self.scopes = {}    # (service_code, zone) -> scope_id
        self.scope_countries = defaultdict(list)  # scope_id -> [country_iso2]
        self.bands = []

        # Counters for IDs
        self.next_service_id = SERVICE_ID_BASE
        self.next_scope_id = 1
        self.next_band_id = 1

        # Load existing data to avoid conflicts
        self._load_existing_data()

    def _load_existing_data(self):
        """Load existing services and scopes to get next IDs"""
        services_file = self.output_dir / 'services.csv'
        scopes_file = self.output_dir / 'tariff_scopes.csv'
        bands_file = self.output_dir / 'tariff_bands.csv'

        if services_file.exists():
            with open(services_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    service_id = int(row['service_id'])
                    if service_id >= self.next_service_id:
                        self.next_service_id = service_id + 1
                    # Store existing FedEx services
                    if row['code'].startswith('FDX_'):
                        self.services[row['code']] = service_id

        if scopes_file.exists():
            with open(scopes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scope_id = int(row['scope_id'])
                    if scope_id >= self.next_scope_id:
                        self.next_scope_id = scope_id + 1

        if bands_file.exists():
            with open(bands_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    band_id = int(row['band_id'])
                    if band_id >= self.next_band_id:
                        self.next_band_id = band_id + 1

        logger.info(f"📊 Next IDs: service={self.next_service_id}, scope={self.next_scope_id}, band={self.next_band_id}")

    def process_zone_chart(self):
        """Process zone chart to create services, scopes, and country mappings"""
        logger.info(f"📖 Reading zone chart: {self.zone_chart_path}")

        with open(self.zone_chart_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        logger.info(f"✅ Loaded {len(rows)} zone chart entries")

        # Group by (product, zone) to create scopes
        scope_data = defaultdict(lambda: {'countries': set(), 'page': None})

        for row in rows:
            product = row['product']
            zone = row['zone']
            country_iso2 = row['country_iso2']

            if not country_iso2:
                logger.warning(f"⚠️ Missing ISO2 for: {row['country_name']}")
                continue

            key = (product, zone)
            scope_data[key]['countries'].add(country_iso2)
            if not scope_data[key]['page']:
                scope_data[key]['page'] = row['page_number']

        # Create services if not existing
        for product_code, service_info in FEDEX_SERVICES.items():
            service_code = service_info['code']
            if service_code not in self.services:
                self.services[service_code] = self.next_service_id
                self.next_service_id += 1
                logger.info(f"✅ Created service: {service_code} (ID={self.services[service_code]})")

        # Create scopes
        for (product, zone), data in scope_data.items():
            service_code = FEDEX_SERVICES[product]['code']
            service_id = self.services[service_code]

            scope_code = f"FDX_{product}_ZONE_{zone}"
            scope_id = self.next_scope_id
            self.next_scope_id += 1

            self.scopes[(service_code, zone)] = scope_id
            self.scope_countries[scope_id] = list(data['countries'])

            logger.debug(f"✅ Scope {scope_id}: {scope_code} ({len(data['countries'])} countries)")

        logger.info(f"✅ Created {len(self.scopes)} scopes for {len(self.services)} services")

    def process_ipe_rates(self, package_type='Package'):
        """
        Process IPE export rates to create tariff bands

        Args:
            package_type: 'Package', 'Pak', or 'Envelope' (default: Package)
        """
        logger.info(f"📖 Reading IPE rates: {self.ipe_rates_path} (type={package_type})")

        with open(self.ipe_rates_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if r['package_type'] == package_type]

        logger.info(f"✅ Loaded {len(rows)} IPE {package_type} pricing rows")

        service_code = 'FDX_IPE_EXPORT'

        for row in rows:
            zone = row['zone']
            scope_key = (service_code, zone)

            if scope_key not in self.scopes:
                logger.warning(f"⚠️ Scope not found for {service_code} Zone {zone}")
                continue

            scope_id = self.scopes[scope_key]

            # Parse weight and price
            min_weight = row['min_weight_kg']
            max_weight = row['max_weight_kg']
            price_eur = row['price_eur']
            is_min_charge = row['is_min_charge'] == 'True'

            # Handle empty weights (Envelope without weight spec)
            if not min_weight or not max_weight:
                continue

            min_weight = float(min_weight)
            max_weight = float(max_weight)
            price_eur = Decimal(price_eur)

            band_id = self.next_band_id
            self.next_band_id += 1

            self.bands.append({
                'band_id': band_id,
                'scope_id': scope_id,
                'min_weight_kg': min_weight,
                'max_weight_kg': max_weight,
                'base_amount': price_eur,
                'amount_per_kg': Decimal('0.0'),
                'is_min_charge': is_min_charge
            })

        logger.info(f"✅ Created {len(self.bands)} IPE pricing bands")

    def write_services(self):
        """Write/update services.csv"""
        services_file = self.output_dir / 'services.csv'

        # Load existing services
        existing_services = []
        if services_file.exists():
            with open(services_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_services = [row for row in reader if not row['code'].startswith('FDX_')]

        # Add new FedEx services
        new_services = []
        for product_code, service_info in FEDEX_SERVICES.items():
            service_code = service_info['code']
            service_id = self.services.get(service_code)

            if service_id:
                new_services.append({
                    'service_id': service_id,
                    'carrier_id': FEDEX_CARRIER_ID,
                    'code': service_code,
                    'label': service_info['label'],
                    'direction': 'EXPORT',
                    'origin_iso2': 'FR',
                    'incoterm': 'DAP',
                    'service_type': service_info['service_type'],
                    'max_weight_kg': service_info['max_weight_kg'],
                    'volumetric_divisor': 5000,
                    'active_from': '2025-11-21',
                    'active_to': ''
                })

        # Write combined services
        all_services = existing_services + new_services
        all_services.sort(key=lambda x: int(x['service_id']))

        with open(services_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = [
                'service_id', 'carrier_id', 'code', 'label', 'direction',
                'origin_iso2', 'incoterm', 'service_type', 'max_weight_kg',
                'volumetric_divisor', 'active_from', 'active_to'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_services)

        logger.info(f"✅ Wrote {len(new_services)} FedEx services to {services_file}")

    def write_scopes(self):
        """Write tariff_scopes.csv"""
        scopes_file = self.output_dir / 'tariff_scopes.csv'

        # Load existing non-FedEx scopes
        existing_scopes = []
        if scopes_file.exists():
            with open(scopes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_scopes = [row for row in reader if not row['code'].startswith('FDX_')]

        # Create new FedEx scopes
        new_scopes = []
        for (service_code, zone), scope_id in self.scopes.items():
            service_id = self.services[service_code]
            product = service_code.replace('FDX_', '').replace('_EXPORT', '')

            new_scopes.append({
                'scope_id': scope_id,
                'service_id': service_id,
                'code': f"FDX_{product}_ZONE_{zone}",
                'description': f"FedEx {product} Export - Zone {zone}",
                'is_catch_all': False
            })

        # Write combined scopes
        all_scopes = existing_scopes + new_scopes
        all_scopes.sort(key=lambda x: int(x['scope_id']))

        with open(scopes_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['scope_id', 'service_id', 'code', 'description', 'is_catch_all']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_scopes)

        logger.info(f"✅ Wrote {len(new_scopes)} FedEx scopes to {scopes_file}")

    def write_scope_countries(self):
        """Write tariff_scope_countries.csv"""
        countries_file = self.output_dir / 'tariff_scope_countries.csv'

        # Load existing non-FedEx country mappings
        existing_mappings = []
        fedex_scope_ids = set(self.scopes.values())

        if countries_file.exists():
            with open(countries_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_mappings = [
                    row for row in reader
                    if int(row['scope_id']) not in fedex_scope_ids
                ]

        # Create new FedEx mappings
        new_mappings = []
        for scope_id, countries in self.scope_countries.items():
            for country_iso2 in sorted(countries):
                new_mappings.append({
                    'scope_id': scope_id,
                    'country_iso2': country_iso2
                })

        # Write combined mappings
        all_mappings = existing_mappings + new_mappings
        all_mappings.sort(key=lambda x: (int(x['scope_id']), x['country_iso2']))

        with open(countries_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['scope_id', 'country_iso2']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_mappings)

        logger.info(f"✅ Wrote {len(new_mappings)} FedEx country mappings to {countries_file}")

    def write_bands(self):
        """Write tariff_bands.csv"""
        bands_file = self.output_dir / 'tariff_bands.csv'

        # Load existing non-FedEx bands
        existing_bands = []
        fedex_scope_ids = set(self.scopes.values())

        if bands_file.exists():
            with open(bands_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_bands = [
                    row for row in reader
                    if int(row['scope_id']) not in fedex_scope_ids
                ]

        # Write combined bands
        all_bands = existing_bands + self.bands
        all_bands.sort(key=lambda x: int(x['band_id']))

        with open(bands_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = [
                'band_id', 'scope_id', 'min_weight_kg', 'max_weight_kg',
                'base_amount', 'amount_per_kg', 'is_min_charge'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_bands)

        logger.info(f"✅ Wrote {len(self.bands)} FedEx pricing bands to {bands_file}")

    def run(self):
        """Execute full ETL pipeline"""
        logger.info("🚀 Starting FedEx V2 ETL")

        # Phase 1: Process zone chart (services, scopes, countries)
        self.process_zone_chart()

        # Phase 2: Process IPE rates (pricing bands)
        self.process_ipe_rates(package_type='Package')

        # Phase 3: Write all output files
        self.write_services()
        self.write_scopes()
        self.write_scope_countries()
        self.write_bands()

        logger.info("✅ FedEx V2 ETL complete!")
        logger.info(f"📊 Summary:")
        logger.info(f"   - Services: {len(self.services)}")
        logger.info(f"   - Scopes: {len(self.scopes)}")
        logger.info(f"   - Country mappings: {sum(len(c) for c in self.scope_countries.values())}")
        logger.info(f"   - Pricing bands: {len(self.bands)}")


def main():
    """Main entry point"""
    # Paths
    zone_chart = "/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_export_zone_chart.csv"
    ipe_rates = "/Users/yoyaku/YOYAKU Dropbox/Benjamin Belaga/Downloads/fedex_ipe_export_rates.csv"
    output_dir = "/Users/yoyaku/repos/pricing-engine/data/normalized"

    # Run ETL
    etl = FedExV2ETL(zone_chart, ipe_rates, output_dir)
    etl.run()


if __name__ == '__main__':
    main()
