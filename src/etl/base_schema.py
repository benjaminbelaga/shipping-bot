"""
Base schema for pricing engine - Canonical data model
All ETL scripts must produce data conforming to this schema
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any
from enum import Enum


class Direction(str, Enum):
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    DOMESTIC = "DOMESTIC"


class ServiceType(str, Enum):
    EXPRESS = "EXPRESS"
    ECONOMY = "ECONOMY"
    MAIL = "MAIL"
    PARCEL = "PARCEL"
    GROUND = "GROUND"


class Incoterm(str, Enum):
    DAP = "DAP"  # Delivered at Place (sans dédouanement)
    DDP = "DDP"  # Delivered Duty Paid (avec dédouanement)


class SurchargeKind(str, Enum):
    PERCENT = "PERCENT"           # % du freight ou total
    FLAT_PER_SHIPMENT = "FLAT"    # Montant fixe par envoi
    FLAT_PER_KG = "PER_KG"        # Montant par kg


class SurchargeBasis(str, Enum):
    FREIGHT = "FREIGHT"     # Appliqué sur le fret de base
    TOTAL = "TOTAL"         # Appliqué sur le total (fret + surcharges précédentes)
    PER_KG = "PER_KG"       # Multiplié par le poids


# ============================================================================
# CARRIERS & SERVICES
# ============================================================================

@dataclass
class Carrier:
    """Transporteur (FEDEX, UPS, LAPOSTE, SPRING)"""
    carrier_id: int
    code: str           # FEDEX, UPS, LAPOSTE, SPRING
    name: str           # FedEx, UPS, La Poste, Spring
    currency: str       # EUR, USD


@dataclass
class Service:
    """Produit tarifaire d'un transporteur"""
    service_id: int
    carrier_id: int
    code: str                       # DELIVENGO_2025, SPRING_EU_HOME, FDX_IP_EXPORT
    label: str                      # Nom commercial
    direction: Direction
    origin_iso2: str                # FR
    incoterm: Incoterm
    service_type: ServiceType
    max_weight_kg: float
    volumetric_divisor: float = 5000.0
    active_from: Optional[str] = None   # YYYY-MM-DD
    active_to: Optional[str] = None


# ============================================================================
# TARIFF SCOPES (Zones / Régions)
# ============================================================================

@dataclass
class TariffScope:
    """
    Zone tarifaire pour un service
    Ex: ZONE_A (FedEx), US (Spring), DELIVENGO_US (La Poste)
    """
    scope_id: int
    service_id: int
    code: str                   # ZONE_A, US, EUROPE1, ROW
    description: str
    is_catch_all: bool = False  # True si "Reste du monde"


@dataclass
class TariffScopeCountry:
    """Mapping scope → pays"""
    scope_id: int
    country_iso2: str           # AU, US, DE...


# ============================================================================
# TARIFF BANDS (Tranches de poids et prix)
# ============================================================================

@dataclass
class TariffBand:
    """
    Tranche de poids et formule de prix

    Prix = base_amount + amount_per_kg * weight_kg

    Exemples:
    - Spring 100g: min=0, max=0.1, base=8.8, per_kg=0
    - Delivengo US: min=0, max=2, base=5.2, per_kg=9.5
    - FedEx IP Zone A 1kg: min=1, max=1, base=14.50, per_kg=0
    - FedEx IP Zone A >71kg: min=71, max=99999, base=0, per_kg=4.16
    """
    band_id: int
    scope_id: int
    min_weight_kg: float
    max_weight_kg: float
    base_amount: Decimal        # Partie fixe
    amount_per_kg: Decimal      # Coefficient * poids
    is_min_charge: bool = False # True si prix minimum (FedEx +)


# ============================================================================
# SURCHARGES (Fuel, DDP/DAP, Residential...)
# ============================================================================

@dataclass
class SurchargeRule:
    """
    Règle de surcharge

    Exemples:
    - Spring Fuel: kind=PERCENT, basis=FREIGHT, value=5.0
    - Spring DAP 1kg: kind=FLAT, basis=PER_SHIPMENT, value=2.45
    - UPS Fuel discount: kind=PERCENT, basis=FREIGHT, value=-30.0
    """
    surcharge_id: int
    service_id: int
    name: str                   # SPRING_FUEL, UPS_RESIDENTIAL
    kind: SurchargeKind
    basis: SurchargeBasis
    value: Decimal              # 5.0 pour 5%, montant fixe, ou per-kg
    conditions: Optional[Dict[str, Any]] = None  # Filtres JSON (pays, poids, mode...)


# ============================================================================
# COUNTRY ALIASES (pour normalisation)
# ============================================================================

@dataclass
class Country:
    """Pays et alias pour normalisation"""
    iso2: str               # AU
    iso3: str               # AUS
    name_en: str            # Australia
    name_fr: str            # Australie
    other_names: List[str]  # ["australie", "oz"]


@dataclass
class CountryAlias:
    """Alias normalisé → ISO2"""
    alias_normalized: str   # "australie" (sans accents, minuscules)
    iso2: str              # AU


# ============================================================================
# CSV SCHEMAS (pour export/import)
# ============================================================================

CSV_CARRIERS = ["carrier_id", "code", "name", "currency"]
CSV_SERVICES = [
    "service_id", "carrier_id", "code", "label", "direction",
    "origin_iso2", "incoterm", "service_type", "max_weight_kg",
    "volumetric_divisor", "active_from", "active_to"
]
CSV_TARIFF_SCOPES = ["scope_id", "service_id", "code", "description", "is_catch_all"]
CSV_TARIFF_SCOPE_COUNTRIES = ["scope_id", "country_iso2"]
CSV_TARIFF_BANDS = [
    "band_id", "scope_id", "min_weight_kg", "max_weight_kg",
    "base_amount", "amount_per_kg", "is_min_charge"
]
CSV_SURCHARGE_RULES = [
    "surcharge_id", "service_id", "name", "kind", "basis", "value", "conditions"
]
