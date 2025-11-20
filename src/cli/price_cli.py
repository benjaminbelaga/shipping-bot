#!/usr/bin/env python3
"""
CLI pour tester le moteur de pricing

Usage:
    python price_cli.py 2kg AU
    python price_cli.py 0.5 Allemagne
    python price_cli.py 1 "États-Unis"
"""

import sys
import re
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine.engine import PricingEngine


def parse_query(args):
    """
    Parse la requête depuis les arguments CLI

    Formats supportés:
        2kg AU
        2 kg Australie
        0.5 Allemagne
        1.5kg "États-Unis"
    """

    query_str = " ".join(args)

    # Extraire le poids (nombre + optionnel kg/g)
    weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g)?', query_str, re.IGNORECASE)

    if not weight_match:
        return None, None

    weight_str = weight_match.group(1).replace(',', '.')
    weight_kg = float(weight_str)

    # Si en grammes, convertir
    if weight_match.group(2) and weight_match.group(2).lower() == 'g':
        weight_kg /= 1000.0

    # Le reste = pays
    country = query_str.replace(weight_match.group(0), '').strip()

    return weight_kg, country


def format_offer(offer, index=None):
    """Formate une offre pour affichage CLI"""

    prefix = f"{index}. " if index else ""

    lines = [
        f"{prefix}{offer.carrier_name} - {offer.service_label}",
        f"   💰 TOTAL: {float(offer.total):.2f} {offer.currency} HT",
        f"      └─ Fret: {float(offer.freight):.2f} {offer.currency}",
    ]

    if offer.surcharges > 0:
        lines.append(f"      └─ Surcharges: {float(offer.surcharges):.2f} {offer.currency}")

    lines.append(f"      └─ Scope: {offer.scope_code} ({offer.band_details})")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: price_cli.py <weight>kg <country>")
        print("\nExamples:")
        print("  price_cli.py 2kg AU")
        print("  price_cli.py 0.5 Allemagne")
        print("  price_cli.py 1.5kg 'États-Unis'")
        sys.exit(1)

    # Parser la requête
    weight_kg, country = parse_query(sys.argv[1:])

    if not weight_kg or not country:
        print("❌ Invalid query. Format: <weight>kg <country>")
        sys.exit(1)

    # Charger le moteur
    print("📦 Loading pricing engine...")
    engine = PricingEngine()
    print()

    # Calculer les prix
    print("=" * 70)
    print(f"🔍 Query: {weight_kg}kg → {country}")
    print("=" * 70)
    print()

    offers = engine.price(country, weight_kg, debug=False)

    if not offers:
        print("❌ No offers found for this destination/weight")
        print("\nPossible reasons:")
        print("  - Country not supported")
        print("  - Weight exceeds maximum for all services")
        sys.exit(1)

    # Afficher les résultats
    print(f"✅ {len(offers)} offers found (sorted by price):\n")

    for i, offer in enumerate(offers, 1):
        print(format_offer(offer, i))
        print()

    # Best offer
    best = offers[0]
    print("=" * 70)
    print(f"🏆 BEST OFFER: {best.carrier_name} - {best.service_label}")
    print(f"   {float(best.total):.2f} {best.currency} HT")
    print("=" * 70)


if __name__ == "__main__":
    main()
