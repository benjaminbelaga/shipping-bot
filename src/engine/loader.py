"""
Data Loader - Charge les CSV normalisés en mémoire
Construit les index pour un accès rapide
"""

import csv
import json
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class Carrier:
    carrier_id: int
    code: str
    name: str
    currency: str


@dataclass
class Service:
    service_id: int
    carrier_id: int
    carrier_code: str
    code: str
    label: str
    direction: str
    origin_iso2: str
    incoterm: str
    service_type: str
    max_weight_kg: float


@dataclass
class TariffScope:
    scope_id: int
    service_id: int
    code: str
    description: str
    is_catch_all: bool
    countries: Set[str]  # Set de ISO2
    bands: List['TariffBand']


@dataclass
class TariffBand:
    band_id: int
    scope_id: int
    min_weight_kg: float
    max_weight_kg: float
    base_amount: Decimal
    amount_per_kg: Decimal
    is_min_charge: bool


@dataclass
class SurchargeRule:
    surcharge_id: int
    service_id: int
    name: str
    kind: str
    basis: str
    value: Decimal
    conditions: dict


class DataLoader:
    """Charge les données normalisées depuis CSV"""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "normalized"

        self.data_dir = data_dir

        # Données chargées
        self.carriers: Dict[int, Carrier] = {}
        self.services: Dict[int, Service] = {}
        self.scopes: Dict[int, TariffScope] = {}
        self.surcharges: Dict[int, List[SurchargeRule]] = {}  # service_id -> rules

        # Index rapides
        self.scopes_by_service: Dict[int, List[TariffScope]] = {}
        self.scope_by_service_country: Dict[tuple, TariffScope] = {}  # (service_id, iso2) -> scope

    def load_all(self):
        """Charge toutes les données"""
        print("📦 Loading pricing data...")

        self._load_carriers()
        self._load_services()
        self._load_scopes()
        self._load_bands()
        self._load_surcharges()

        self._build_indexes()

        print(f"✅ Loaded {len(self.carriers)} carriers, {len(self.services)} services, "
              f"{len(self.scopes)} scopes")

    def _load_carriers(self):
        """Charge carriers.csv"""
        path = self.data_dir / "carriers.csv"

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                carrier = Carrier(
                    carrier_id=int(row["carrier_id"]),
                    code=row["code"],
                    name=row["name"],
                    currency=row["currency"]
                )
                self.carriers[carrier.carrier_id] = carrier

    def _load_services(self):
        """Charge services.csv"""
        path = self.data_dir / "services.csv"

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                carrier = self.carriers[int(row["carrier_id"])]

                service = Service(
                    service_id=int(row["service_id"]),
                    carrier_id=int(row["carrier_id"]),
                    carrier_code=carrier.code,
                    code=row["code"],
                    label=row["label"],
                    direction=row["direction"],
                    origin_iso2=row["origin_iso2"],
                    incoterm=row["incoterm"],
                    service_type=row["service_type"],
                    max_weight_kg=float(row["max_weight_kg"])
                )
                self.services[service.service_id] = service

    def _load_scopes(self):
        """Charge tariff_scopes.csv + tariff_scope_countries.csv"""
        scopes_path = self.data_dir / "tariff_scopes.csv"
        countries_path = self.data_dir / "tariff_scope_countries.csv"

        # Charger scopes
        with scopes_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                scope = TariffScope(
                    scope_id=int(row["scope_id"]),
                    service_id=int(row["service_id"]),
                    code=row["code"],
                    description=row["description"],
                    is_catch_all=row["is_catch_all"].lower() == "true",
                    countries=set(),
                    bands=[]
                )
                self.scopes[scope.scope_id] = scope

        # Charger mappings pays
        with countries_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                scope_id = int(row["scope_id"])
                iso2 = row["country_iso2"]

                if scope_id in self.scopes:
                    self.scopes[scope_id].countries.add(iso2)

    def _load_bands(self):
        """Charge tariff_bands.csv et associe aux scopes"""
        path = self.data_dir / "tariff_bands.csv"

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                band = TariffBand(
                    band_id=int(row["band_id"]),
                    scope_id=int(row["scope_id"]),
                    min_weight_kg=float(row["min_weight_kg"]),
                    max_weight_kg=float(row["max_weight_kg"]),
                    base_amount=Decimal(row["base_amount"]),
                    amount_per_kg=Decimal(row["amount_per_kg"]),
                    is_min_charge=row["is_min_charge"].lower() == "true"
                )

                scope_id = band.scope_id
                if scope_id in self.scopes:
                    self.scopes[scope_id].bands.append(band)

        # Trier les bands par min_weight pour chaque scope
        for scope in self.scopes.values():
            scope.bands.sort(key=lambda b: b.min_weight_kg)

    def _load_surcharges(self):
        """Charge surcharge_rules.csv"""
        path = self.data_dir / "surcharge_rules.csv"

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                service_id = int(row["service_id"])

                # Parse conditions JSON
                conditions_str = row.get("conditions", "{}")
                try:
                    conditions = json.loads(conditions_str) if conditions_str else {}
                except json.JSONDecodeError:
                    conditions = {}

                rule = SurchargeRule(
                    surcharge_id=int(row["surcharge_id"]),
                    service_id=service_id,
                    name=row["name"],
                    kind=row["kind"],
                    basis=row["basis"],
                    value=Decimal(row["value"]),
                    conditions=conditions
                )

                if service_id not in self.surcharges:
                    self.surcharges[service_id] = []

                self.surcharges[service_id].append(rule)

    def _build_indexes(self):
        """Construit les index pour accès rapide"""

        # Index: service_id -> scopes
        for scope in self.scopes.values():
            service_id = scope.service_id

            if service_id not in self.scopes_by_service:
                self.scopes_by_service[service_id] = []

            self.scopes_by_service[service_id].append(scope)

        # Index: (service_id, country_iso2) -> scope
        for scope in self.scopes.values():
            for iso2 in scope.countries:
                key = (scope.service_id, iso2)
                # Priorité aux scopes non catch-all
                if key not in self.scope_by_service_country or not scope.is_catch_all:
                    self.scope_by_service_country[key] = scope


def load_engine():
    """Helper: charge et retourne un DataLoader prêt"""
    loader = DataLoader()
    loader.load_all()
    return loader
