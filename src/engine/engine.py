"""
Pricing Engine - Moteur de tarification unifié
"""

import json
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass

from .loader import DataLoader, TariffScope, TariffBand, SurchargeRule
from .country_resolver import CountryResolver


@dataclass
class OriginAddress:
    """Adresse d'origine pour les calculs d'expédition"""
    name: str  # e.g., "YOYAKU SARL"
    address_line: str  # e.g., "14 boulevard de la Chapelle"
    city: str  # e.g., "PARIS"
    postal_code: str  # e.g., "75018"
    country_iso2: str  # e.g., "FR"
    state_province: str = ""  # Optional, for countries like US


# Predefined origin addresses
ORIGIN_PARIS = OriginAddress(
    name="YOYAKU SARL",
    address_line="14 boulevard de la Chapelle",
    city="PARIS",
    postal_code="75018",
    country_iso2="FR"
)


@dataclass
class PriceOffer:
    """Résultat d'un calcul de prix"""
    carrier_code: str
    carrier_name: str
    service_code: str
    service_label: str
    freight: Decimal
    surcharges: Decimal
    total: Decimal
    currency: str
    scope_code: str
    band_details: str
    warning: Optional[str] = None  # Warning message if service restricted
    is_suspended: bool = False  # True if service suspended for this destination


class PricingEngine:
    """Moteur de tarification principal"""

    def __init__(self, loader: DataLoader = None, origin: Optional[OriginAddress] = None):
        """
        Initialize Pricing Engine

        Args:
            loader: DataLoader instance (creates default if None)
            origin: Origin address for shipments (default: None)
                    Use ORIGIN_PARIS for YOYAKU shipments from Paris

        Example:
            # Generic pricing (no origin)
            engine = PricingEngine()

            # YOYAKU-specific pricing with fixed Paris origin
            engine = PricingEngine(origin=ORIGIN_PARIS)
        """
        if loader is None:
            loader = DataLoader()
            loader.load_all()

        self.loader = loader
        self.resolver = CountryResolver()
        self.origin = origin

        # Load service restrictions (Trump tariffs, etc.)
        self.restrictions = self._load_restrictions()

    def price(self, dest: str, weight_kg: float, debug: bool = False) -> List[PriceOffer]:
        """
        Calcule les prix pour tous les services disponibles

        Args:
            dest: Nom du pays de destination (ex: "Australie", "AU", "australia")
            weight_kg: Poids en kilogrammes
            debug: Si True, affiche les détails du calcul

        Returns:
            Liste d'offres triées par prix croissant
        """

        # Résoudre le pays
        dest_iso2 = self.resolver.resolve(dest)

        if not dest_iso2:
            if debug:
                print(f"❌ Unknown country: {dest}")
            return []

        if debug:
            print(f"🌍 Resolved: {dest} → {dest_iso2} ({self.resolver.get_name(dest_iso2)})")
            print(f"⚖️  Weight: {weight_kg} kg\n")

        offers = []

        # Pour chaque service
        for service_id, service in self.loader.services.items():
            # Vérifier poids max
            if weight_kg > service.max_weight_kg:
                if debug:
                    print(f"⏭️  {service.code}: weight exceeds max {service.max_weight_kg}kg")
                continue

            # Trouver le scope pour ce pays
            scope = self._find_scope(service_id, dest_iso2)

            if not scope:
                if debug:
                    print(f"⏭️  {service.code}: no scope for {dest_iso2}")
                continue

            # Trouver la bande de poids
            band = self._find_band(scope, weight_kg)

            if not band:
                if debug:
                    print(f"⏭️  {service.code}: no band for {weight_kg}kg")
                continue

            # Calculer le fret de base
            freight = self._calculate_freight(band, weight_kg)

            # Calculer les surcharges
            surcharge_total = self._calculate_surcharges(service_id, dest_iso2, weight_kg, freight)

            # Total
            total = freight + surcharge_total

            # Carrier info
            carrier = self.loader.carriers[service.carrier_id]

            # Check for service restrictions
            warning, is_suspended = self._check_restriction(service.code, dest_iso2)

            offer = PriceOffer(
                carrier_code=carrier.code,
                carrier_name=carrier.name,
                service_code=service.code,
                service_label=service.label,
                freight=freight,
                surcharges=surcharge_total,
                total=total,
                currency=carrier.currency,
                scope_code=scope.code,
                band_details=f"{band.min_weight_kg}-{band.max_weight_kg}kg",
                warning=warning,
                is_suspended=is_suspended
            )

            offers.append(offer)

            if debug:
                print(f"✅ {service.code} ({scope.code}): "
                      f"{float(freight):.2f} + {float(surcharge_total):.2f} = "
                      f"{float(total):.2f} {carrier.currency}")

        # Trier par prix croissant
        offers.sort(key=lambda o: o.total)

        return offers

    def _find_scope(self, service_id: int, dest_iso2: str) -> Optional[TariffScope]:
        """
        Trouve le scope tarifaire pour un service et un pays

        Priorité:
        1. Scope spécifique au pays (non catch-all)
        2. Scope catch-all (Reste du monde)
        """

        # Index direct
        key = (service_id, dest_iso2)
        if key in self.loader.scope_by_service_country:
            return self.loader.scope_by_service_country[key]

        # Fallback: chercher un scope catch-all pour ce service
        scopes = self.loader.scopes_by_service.get(service_id, [])

        for scope in scopes:
            if scope.is_catch_all:
                return scope

        return None

    def _find_band(self, scope: TariffScope, weight_kg: float) -> Optional[TariffBand]:
        """
        Trouve la bande de poids appropriée

        Les bandes sont triées par min_weight_kg croissant
        On cherche la première bande où min_weight <= weight <= max_weight
        """

        for band in scope.bands:
            if band.min_weight_kg <= weight_kg <= band.max_weight_kg:
                return band

        return None

    def _calculate_freight(self, band: TariffBand, weight_kg: float) -> Decimal:
        """
        Calcule le fret de base

        Formule: base_amount + amount_per_kg * weight_kg

        Si is_min_charge, on prend max(formule, base_amount)
        """

        freight = band.base_amount + band.amount_per_kg * Decimal(str(weight_kg))

        if band.is_min_charge:
            freight = max(freight, band.base_amount)

        return freight

    def _calculate_surcharges(
        self,
        service_id: int,
        dest_iso2: str,
        weight_kg: float,
        freight: Decimal,
        conditions: Optional[Dict] = None
    ) -> Decimal:
        """
        Calcule le total des surcharges applicables

        Surcharges supportées:
        - PERCENT sur FREIGHT: surcharge = freight * value / 100
        - FLAT (per shipment): surcharge = value
        - PER_KG: surcharge = value * weight_kg

        Conditions de filtrage:
        - delivery_type: "residential" | "commercial"
        - delivery_frequency: "weekly" | "daily"
        - Autres conditions custom par transporteur

        Ordre d'application (selon ARCHITECTURE.md):
        1. Surcharges négatives (remises) en premier
        2. Surcharges positives (frais) ensuite
        3. Total final >= 0
        """

        if conditions is None:
            conditions = {}

        rules = self.loader.surcharges.get(service_id, [])

        # Filtrer les règles applicables (vérifier conditions)
        applicable_rules = []
        for rule in rules:
            if self._matches_conditions(rule.conditions, conditions):
                applicable_rules.append(rule)

        # Trier: négatives en premier, positives ensuite
        applicable_rules.sort(key=lambda r: r.value)

        total = Decimal(0)

        for rule in applicable_rules:
            if rule.kind == "PERCENT":
                if rule.basis == "FREIGHT":
                    surcharge = freight * rule.value / Decimal(100)
                elif rule.basis == "TOTAL":
                    # Total = freight + surcharges précédentes
                    surcharge = (freight + total) * rule.value / Decimal(100)
                else:
                    surcharge = Decimal(0)

            elif rule.kind == "FLAT":
                surcharge = rule.value

            elif rule.kind == "PER_KG":
                surcharge = rule.value * Decimal(str(weight_kg))

            else:
                surcharge = Decimal(0)

            total += surcharge

        return total

    def _matches_conditions(self, rule_conditions: Dict, query_conditions: Dict) -> bool:
        """
        Vérifie si une règle de surcharge s'applique selon les conditions

        Args:
            rule_conditions: Conditions définies dans la règle (ex: {"delivery_type": "residential"})
            query_conditions: Conditions de la requête utilisateur (ex: {"delivery_type": "residential"})

        Returns:
            True si la règle s'applique, False sinon

        Logique:
        - Si rule_conditions est vide {}, la règle s'applique toujours (surcharge universelle)
        - Sinon, toutes les clés de rule_conditions doivent matcher query_conditions
        """

        # Règle sans conditions = s'applique toujours
        if not rule_conditions:
            return True

        # Vérifier que chaque condition de la règle est satisfaite
        for key, required_value in rule_conditions.items():
            # Si la condition n'est pas présente dans la requête, la règle ne s'applique pas
            if key not in query_conditions:
                return False

            # Si la valeur ne correspond pas, la règle ne s'applique pas
            if query_conditions[key] != required_value:
                return False

        return True

    def _load_restrictions(self) -> Dict:
        """
        Load service restrictions from JSON config

        Returns:
            Dict with restrictions indexed by (service_code, country_iso2)
        """
        restrictions_file = Path(__file__).parent.parent.parent / "data" / "service_restrictions.json"

        if not restrictions_file.exists():
            return {}

        try:
            with open(restrictions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Index by (service_code, country_iso2)
            indexed = {}
            for restriction in data.get('restrictions', []):
                key = (restriction['service_code'], restriction['country_iso2'])
                indexed[key] = restriction

            return indexed
        except Exception as e:
            print(f"⚠️  Warning: Could not load restrictions: {e}")
            return {}

    def _check_restriction(self, service_code: str, dest_iso2: str) -> tuple:
        """
        Check if a service has restrictions for a destination

        Returns:
            (warning_message, is_suspended)
        """
        key = (service_code, dest_iso2)
        restriction = self.restrictions.get(key)

        if not restriction:
            return (None, False)

        status = restriction.get('status', 'UNKNOWN')
        is_suspended = status == 'SUSPENDED'
        warning = restriction.get('message_fr', '⚠️ Service restreint')

        return (warning, is_suspended)


def main():
    """Test du moteur"""
    engine = PricingEngine()

    test_queries = [
        ("Australie", 2.0),
        ("US", 2.0),
        ("DE", 0.5),
        ("GB", 1.0),
    ]

    for dest, weight in test_queries:
        print("=" * 70)
        print(f"Query: {weight}kg → {dest}")
        print("=" * 70)

        offers = engine.price(dest, weight, debug=True)

        if offers:
            print(f"\n📊 {len(offers)} offers found (sorted by price):\n")

            for i, offer in enumerate(offers, 1):
                print(f"{i}. {offer.carrier_name} - {offer.service_label}")
                print(f"   Freight: {float(offer.freight):.2f} {offer.currency}")
                print(f"   Surcharges: {float(offer.surcharges):.2f} {offer.currency}")
                print(f"   TOTAL: {float(offer.total):.2f} {offer.currency}")
                print(f"   (Scope: {offer.scope_code}, Band: {offer.band_details})")
                print()
        else:
            print("\n❌ No offers found\n")

        print()


if __name__ == "__main__":
    main()
