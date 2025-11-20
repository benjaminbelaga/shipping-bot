#!/usr/bin/env python3
"""
UPS API Debug Script - Capture full request/response for support ticket

Usage:
    python3 debug_ups_api.py --country US --weight 2.0 --debug
    python3 debug_ups_api.py --country DE --weight 0.5 --production
    python3 debug_ups_api.py --test-all
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.ups_api import UPSAPIClient, UPSCredentialsManager


def setup_logging(debug: bool = False):
    """Setup detailed logging"""
    log_level = logging.DEBUG if debug else logging.INFO

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # File handler for full debug log
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f'ups_debug_{timestamp}.log'

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return log_file


def test_single_destination(
    client: UPSAPIClient,
    country: str,
    weight: float,
    city: str = "Main City",
    postal: str = "00000",
    debug_output: Path = None
):
    """Test UPS API for a single destination"""

    logger = logging.getLogger(__name__)

    print("\n" + "=" * 80)
    print(f"🧪 UPS API TEST - {country} ({weight}kg)")
    print("=" * 80)

    # Determine API type
    api_type = 'STANDARD' if country in client.EUROPE_COUNTRIES else 'WWE'
    config = client.credentials.configs[api_type]

    print(f"\n📋 Configuration:")
    print(f"   API Type: {api_type}")
    print(f"   Account: {config.account_number}")
    print(f"   Origin: {client.origin_address['City']}, {client.origin_address['CountryCode']}")
    print(f"   Destination: {city}, {country} {postal}")
    print(f"   Weight: {weight}kg")

    # Test authentication
    print(f"\n🔐 Testing authentication...")
    try:
        token = client.get_access_token(api_type)
        print(f"   ✅ Token obtained: {token[:20]}...{token[-10:]}")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False

    # Test rating API
    print(f"\n📦 Testing rating API...")
    try:
        rates = client.get_shipping_rates(weight, country, city, postal)

        if rates:
            print(f"\n✅ SUCCESS: {len(rates)} rates obtained")
            print("\n📊 Rates:")
            for i, rate in enumerate(rates, 1):
                print(f"   {i}. {rate['service_name']:35s}")
                print(f"      Price: {float(rate['price']):6.2f} {rate['currency']}")
                print(f"      Delivery: {rate['delivery_days']} days")
                print(f"      Service Code: {rate['service_code']}, API: {rate['api_type']}")

            # Save to debug output
            if debug_output:
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'test': {
                        'country': country,
                        'weight': weight,
                        'city': city,
                        'postal': postal
                    },
                    'config': {
                        'api_type': api_type,
                        'account': config.account_number,
                        'origin': client.origin_address
                    },
                    'success': True,
                    'rates': [
                        {
                            'service_code': r['service_code'],
                            'service_name': r['service_name'],
                            'price': float(r['price']),
                            'currency': r['currency'],
                            'delivery_days': r['delivery_days']
                        } for r in rates
                    ]
                }

                with open(debug_output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                print(f"\n💾 Debug output saved to: {debug_output}")

            return True
        else:
            print(f"   ❌ No rates obtained (check logs for errors)")

            # Save error info
            if debug_output:
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'test': {
                        'country': country,
                        'weight': weight,
                        'city': city,
                        'postal': postal
                    },
                    'config': {
                        'api_type': api_type,
                        'account': config.account_number,
                        'origin': client.origin_address
                    },
                    'success': False,
                    'error': 'No rates returned (check logs for UPS API errors)'
                }

                with open(debug_output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                print(f"\n💾 Error info saved to: {debug_output}")

            return False

    except Exception as e:
        print(f"   ❌ Rating API error: {e}")
        logger.exception("Full exception:")
        return False


def test_all_scenarios(client: UPSAPIClient, production: bool):
    """Test multiple scenarios (Europe, Worldwide, different weights)"""

    print("\n" + "=" * 80)
    print("🧪 UPS API COMPREHENSIVE TEST")
    print("=" * 80)
    print(f"Environment: {'PRODUCTION' if production else 'TEST'}")

    test_cases = [
        # Europe (STANDARD API)
        ('Germany', 'DE', 'Berlin', '10115', 0.5),
        ('United Kingdom', 'GB', 'London', 'SW1A 1AA', 1.0),
        ('Spain', 'ES', 'Madrid', '28001', 2.0),

        # Worldwide (WWE API)
        ('USA', 'US', 'New York', '10001', 2.0),
        ('Japan', 'JP', 'Tokyo', '100-0001', 1.5),
        ('Australia', 'AU', 'Sydney', '2000', 3.0),
    ]

    results = []

    for name, country, city, postal, weight in test_cases:
        result = test_single_destination(
            client, country, weight, city, postal
        )
        results.append((name, result))

        # Brief pause between tests
        import time
        time.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name:20s} - {'SUCCESS' if success else 'FAILED'}")

    success_count = sum(1 for _, s in results if s)
    print(f"\nTotal: {success_count}/{len(results)} tests passed")


def main():
    parser = argparse.ArgumentParser(
        description='Debug UPS API integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 debug_ups_api.py --country US --weight 2.0
  python3 debug_ups_api.py --country DE --weight 0.5 --production
  python3 debug_ups_api.py --test-all --debug
  python3 debug_ups_api.py --country JP --weight 1.5 --city Tokyo --postal 100-0001
        '''
    )

    parser.add_argument('--country', type=str, help='Destination country (ISO2 code)')
    parser.add_argument('--weight', type=float, help='Package weight in kg')
    parser.add_argument('--city', type=str, default='Main City', help='Destination city')
    parser.add_argument('--postal', type=str, default='00000', help='Postal code')

    parser.add_argument('--test-all', action='store_true', help='Run all test scenarios')
    parser.add_argument('--production', action='store_true', help='Use production environment')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    print("=" * 80)
    print("🚀 UPS API DEBUG TOOL")
    print("=" * 80)
    print(f"Environment: {'PRODUCTION' if args.production else 'TEST'}")
    print(f"Log file: {log_file}")

    # Check credentials
    creds_file = Path.home() / '.credentials' / 'yoyaku' / 'api-keys' / 'ups.env'
    if not creds_file.exists():
        print(f"\n❌ ERROR: Credentials file not found: {creds_file}")
        print("\nPlease create the file with:")
        print("   UPS_STANDARD_CLIENT_ID=...")
        print("   UPS_STANDARD_CLIENT_SECRET=...")
        print("   UPS_STANDARD_ACCOUNT=C394D0")
        print("")
        print("   UPS_WWE_CLIENT_ID=...")
        print("   UPS_WWE_CLIENT_SECRET=...")
        print("   UPS_WWE_ACCOUNT=R5J577")
        sys.exit(1)

    print(f"✅ Credentials file found: {creds_file}")

    # Initialize client
    try:
        client = UPSAPIClient(production=args.production)
        print("✅ UPS API client initialized")
    except Exception as e:
        print(f"\n❌ ERROR initializing client: {e}")
        logger.exception("Full exception:")
        sys.exit(1)

    # Run tests
    if args.test_all:
        test_all_scenarios(client, args.production)
    elif args.country and args.weight:
        # Single test with debug output
        debug_dir = Path(__file__).parent / 'logs'
        debug_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_output = debug_dir / f'ups_test_{args.country}_{timestamp}.json'

        success = test_single_destination(
            client, args.country, args.weight,
            args.city, args.postal, debug_output
        )

        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\n❌ ERROR: Either --test-all or both --country and --weight are required")
        sys.exit(1)


if __name__ == '__main__':
    main()
