"""
UPS API Integration - Real-time pricing via UPS Rating API
Supports dual API system: STANDARD (Europe) and WWE (Worldwide)
"""

import requests
import base64
import json
import time
import logging
import os
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UPSCredentials:
    """UPS API credentials"""
    client_id: str
    client_secret: str
    account_number: str
    description: str


class UPSCredentialsManager:
    """Manage UPS credentials from environment"""

    def __init__(self):
        self.configs = self._load_credentials()

    def _load_credentials(self) -> Dict[str, UPSCredentials]:
        """
        Load UPS credentials from ~/.credentials/yoyaku/api-keys/ups.env

        Expected format:
        UPS_STANDARD_CLIENT_ID=...
        UPS_STANDARD_CLIENT_SECRET=...
        UPS_STANDARD_ACCOUNT=C394D0

        UPS_WWE_CLIENT_ID=...
        UPS_WWE_CLIENT_SECRET=...
        UPS_WWE_ACCOUNT=R5J577
        """
        credentials_file = os.path.expanduser("~/.credentials/yoyaku/api-keys/ups.env")

        # Default fallback values (from old bot)
        configs = {
            'STANDARD': UPSCredentials(
                client_id=os.getenv('UPS_STANDARD_CLIENT_ID', 'ncNlUVwO8H5jl2rXFwLmDkVXVlErtAEm5hLWepUOyPY1qqbY'),
                client_secret=os.getenv('UPS_STANDARD_CLIENT_SECRET', 'GIREojIxhNgg2Sug0S6XTOEuja4oDxi3vLzgqIcELeRbybSXv05wpFXnGMdAiLjk'),
                account_number=os.getenv('UPS_STANDARD_ACCOUNT', 'C394D0'),
                description='Europe - Express and Standard services'
            ),
            'WWE': UPSCredentials(
                client_id=os.getenv('UPS_WWE_CLIENT_ID', 'IXqQKQBGAGSGOG5GZ9AvJGzD7VHKhAqPgx8M5Q7Y7GJXQhFG'),
                client_secret=os.getenv('UPS_WWE_CLIENT_SECRET', 'G0GAGGyJaJBMGGbQGyZGWUlGLMVa7AAGM5GJAGSd5FAQIAGHGGqQDpBBHGqHBvs'),
                account_number=os.getenv('UPS_WWE_ACCOUNT', 'R5J577'),
                description='Worldwide - Economy service only'
            )
        }

        # Try to load from file
        if os.path.exists(credentials_file):
            try:
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        if '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip('"').strip("'")

                            # Parse UPS credentials
                            if key == 'UPS_STANDARD_CLIENT_ID':
                                configs['STANDARD'].client_id = value
                            elif key == 'UPS_STANDARD_CLIENT_SECRET':
                                configs['STANDARD'].client_secret = value
                            elif key == 'UPS_STANDARD_ACCOUNT':
                                configs['STANDARD'].account_number = value
                            elif key == 'UPS_WWE_CLIENT_ID':
                                configs['WWE'].client_id = value
                            elif key == 'UPS_WWE_CLIENT_SECRET':
                                configs['WWE'].client_secret = value
                            elif key == 'UPS_WWE_ACCOUNT':
                                configs['WWE'].account_number = value

                logger.info("✅ UPS credentials loaded from ups.env")
            except Exception as e:
                logger.warning(f"⚠️ Error loading ups.env: {e}, using defaults")
        else:
            logger.warning(f"⚠️ Credentials file not found: {credentials_file}, using defaults")

        return configs


class UPSAPIClient:
    """UPS API client for real-time rate shopping"""

    # Europe countries → STANDARD API
    EUROPE_COUNTRIES = {
        'FR', 'DE', 'ES', 'IT', 'PL', 'NL', 'BE', 'AT', 'CH',
        'SE', 'NO', 'DK', 'FI', 'PT', 'GR', 'IE', 'CZ', 'HU',
        'RO', 'BG', 'SK', 'SI', 'HR', 'EE', 'LV', 'LT', 'LU', 'CY', 'MT'
    }

    # UPS service code names
    SERVICE_NAMES = {
        '03': 'UPS Ground',
        '11': 'UPS Standard',
        '01': 'UPS Next Day Air',
        '02': 'UPS Second Day Air',
        '13': 'UPS Next Day Air Saver',
        '14': 'UPS Next Day Air Early AM',
        '08': 'UPS Worldwide Expedited',
        '07': 'UPS Worldwide Express',
        '54': 'UPS Worldwide Express Plus',
        '65': 'UPS Express Saver',
        '96': 'UPS Worldwide Economy DDU',  # WWE service
        '92': 'UPS SurePost',
    }

    def __init__(self, credentials_manager: Optional[UPSCredentialsManager] = None, production: bool = True):
        if credentials_manager is None:
            credentials_manager = UPSCredentialsManager()

        self.credentials = credentials_manager

        # Environment selection
        if production:
            self.base_url = "https://onlinetools.ups.com/api"  # PRODUCTION
            self.auth_url = "https://onlinetools.ups.com/security/v1/oauth/token"
        else:
            self.base_url = "https://wwwcie.ups.com/api"  # TEST
            self.auth_url = "https://wwwcie.ups.com/security/v1/oauth/token"

        self.tokens = {}  # Token cache

        # YOYAKU Paris origin address
        self.origin_address = {
            "AddressLine": "14 boulevard de la Chapelle",
            "City": "PARIS",
            "StateProvinceCode": "",
            "PostalCode": "75018",
            "CountryCode": "FR"
        }

    def get_access_token(self, api_type: str) -> str:
        """
        Get OAuth2 access token for UPS API

        Args:
            api_type: 'STANDARD' or 'WWE'

        Returns:
            Access token string
        """
        if api_type not in ['STANDARD', 'WWE']:
            raise ValueError(f"Invalid API type: {api_type}")

        # Check cache
        cache_key = f"{api_type}_token"
        if cache_key in self.tokens:
            token_info = self.tokens[cache_key]
            if token_info.get('expires_at', 0) > time.time() + 300:  # 5min buffer
                return token_info['token']

        config = self.credentials.configs[api_type]

        # OAuth2 authentication (use instance auth_url)
        auth_url = self.auth_url

        # Encode credentials in Base64
        credentials = f"{config.client_id}:{config.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_credentials}'
        }

        data = {
            'grant_type': 'client_credentials'
        }

        try:
            response = requests.post(auth_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data['access_token']
            expires_in = int(token_data.get('expires_in', 3600))  # Convert to int

            # Cache token
            self.tokens[cache_key] = {
                'token': access_token,
                'expires_at': time.time() + expires_in
            }

            logger.info(f"✅ UPS {api_type} token obtained (expires in {expires_in}s)")
            return access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ UPS {api_type} authentication error: {e}")
            raise

    def get_shipping_rates(
        self,
        weight_kg: float,
        destination_country: str,
        destination_city: str = "Main City",
        destination_postal: str = "00000"
    ) -> List[Dict[str, Any]]:
        """
        Get real-time shipping rates from UPS API

        Args:
            weight_kg: Package weight in kilograms
            destination_country: ISO2 country code (e.g., 'US', 'GB')
            destination_city: Destination city name
            destination_postal: Destination postal code

        Returns:
            List of rate dictionaries with keys:
            - service_code: UPS service code ('11', '96', etc.)
            - service_name: Human-readable name
            - price: Price in EUR (Decimal)
            - currency: Currency code
            - delivery_days: Estimated delivery time
            - api_type: 'STANDARD' or 'WWE'
        """
        # Determine which API to use
        api_type = 'STANDARD' if destination_country in self.EUROPE_COUNTRIES else 'WWE'

        try:
            # Get access token
            access_token = self.get_access_token(api_type)
            config = self.credentials.configs[api_type]

            # Build request payload
            rating_url = f"{self.base_url}/rating/v1/Rate"

            payload = {
                "RateRequest": {
                    "Request": {
                        "RequestOption": "Shop",  # Get all available services
                        "TransactionReference": {
                            "CustomerContext": f"YOYAKU-{int(time.time())}"
                        }
                    },
                    "Shipment": {
                        "Shipper": {
                            "Name": "YOYAKU SARL",
                            "ShipperNumber": config.account_number,
                            "Address": self.origin_address
                        },
                        "ShipTo": {
                            "Name": "Customer",
                            "Address": {
                                "City": destination_city,
                                "CountryCode": destination_country,
                                "PostalCode": destination_postal
                            }
                        },
                        "ShipFrom": {
                            "Name": "YOYAKU SARL",
                            "Address": self.origin_address
                        },
                        "Package": [
                            {
                                "PackagingType": {
                                    "Code": "02",  # Customer Supplied Package
                                    "Description": "Customer Supplied Package"
                                },
                                "Dimensions": {
                                    "UnitOfMeasurement": {
                                        "Code": "CM",
                                        "Description": "Centimeters"
                                    },
                                    "Length": "30",
                                    "Width": "30",
                                    "Height": "15"
                                },
                                "PackageWeight": {
                                    "UnitOfMeasurement": {
                                        "Code": "KGS",
                                        "Description": "Kilograms"
                                    },
                                    "Weight": str(weight_kg)
                                }
                            }
                        ]
                    }
                }
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'transactionSrc': 'testing'
            }

            # API call
            logger.debug(f"📤 UPS API {api_type} request to {rating_url}")
            logger.debug(f"   Weight: {weight_kg}kg, Destination: {destination_country}")

            response = requests.post(rating_url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"❌ UPS API {api_type} error: {response.status_code} - {response.text}")
                logger.debug(f"   Request payload: {json.dumps(payload, indent=2)}")
                return []

            # Parse response
            data = response.json()
            rates = []

            if 'RateResponse' in data and 'RatedShipment' in data['RateResponse']:
                shipments = data['RateResponse']['RatedShipment']
                if not isinstance(shipments, list):
                    shipments = [shipments]

                for shipment in shipments:
                    service = shipment.get('Service', {})
                    service_code = service.get('Code', 'Unknown')
                    service_name = self.SERVICE_NAMES.get(service_code, f'UPS Service {service_code}')

                    # Total price
                    total_charges = shipment.get('TotalCharges', {})
                    price = Decimal(total_charges.get('MonetaryValue', '0'))
                    currency = total_charges.get('CurrencyCode', 'EUR')

                    # Estimated delivery time
                    delivery_days = self._estimate_delivery_days(service_code, destination_country)

                    rates.append({
                        'service_code': service_code,
                        'service_name': service_name,
                        'price': price,
                        'currency': currency,
                        'delivery_days': delivery_days,
                        'api_type': api_type
                    })

            logger.info(f"✅ {len(rates)} UPS rates obtained for {weight_kg}kg to {destination_country}")
            return rates

        except Exception as e:
            logger.error(f"❌ UPS API {api_type} call error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _estimate_delivery_days(self, service_code: str, destination_country: str) -> str:
        """Estimate delivery days based on service and destination"""

        is_europe = destination_country in self.EUROPE_COUNTRIES

        if is_europe:
            estimates = {
                '11': '1-3',  # Standard Europe
                '07': '1-2',  # Express
                '08': '2-3',  # Expedited
                '65': '1-2',  # Express Saver
                '01': '1',    # Next Day
                '02': '2',    # Second Day
            }
        else:
            estimates = {
                '96': '7-14',  # WWE
                '07': '3-5',   # Worldwide Express
                '08': '4-6',   # Worldwide Expedited
                '54': '1-3',   # Express Plus
                '11': '5-8',   # Standard International
            }

        return estimates.get(service_code, '5-10')


def main():
    """Test UPS API integration"""
    logging.basicConfig(level=logging.INFO)

    client = UPSAPIClient()

    test_cases = [
        ('USA', 'US', 2.0),
        ('Japon', 'JP', 2.0),
        ('Allemagne', 'DE', 0.5),
    ]

    print("\n" + "="*70)
    print("🧪 UPS API TEST")
    print("="*70)

    for name, iso2, weight in test_cases:
        print(f"\n📦 {weight}kg → {name} ({iso2})")
        print("-"*70)

        rates = client.get_shipping_rates(weight, iso2)

        if rates:
            for i, rate in enumerate(rates, 1):
                print(f"{i}. {rate['service_name']:35s} {float(rate['price']):6.2f} {rate['currency']} ({rate['delivery_days']} days)")
                print(f"   API: {rate['api_type']}, Service: {rate['service_code']}")
        else:
            print("   ❌ No rates obtained")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
