# UPS API Integration - Real-Time Pricing

## 📋 Vue d'ensemble

Le pricing engine supporte maintenant **2 sources** de pricing UPS :

1. **UPS WWE (Grilles statiques CSV)** - Déjà intégré ✅
   - 88 pays couverts
   - Prix fixes extraits du fichier Excel
   - Service: `UPS_ECONOMY_DDU_EXPORT_FR`
   - ⚠️ USA SUSPENDU (tarifs Trump)

2. **UPS API (Temps réel)** - Nouveau 🆕
   - Calculs dynamiques via UPS Rating API
   - Prix en temps réel selon adresse exacte
   - 2 APIs: STANDARD (Europe) + WWE (Monde)

---

## 🔑 Configuration des Credentials

### 1. Obtenir les Credentials UPS

**Aller sur**: https://www.ups.com/upsdeveloperkit

1. Créer un compte développeur UPS
2. Créer 2 applications:
   - **App 1**: Standard API (Europe) → Account C394D0
   - **App 2**: WWE API (Worldwide) → Account R5J577
3. Noter les credentials:
   - Client ID
   - Client Secret
   - Account Number

### 2. Configurer les Credentials

**Fichier**: `~/.credentials/yoyaku/api-keys/ups.env`

```bash
# STANDARD API (Europe - C394D0)
UPS_STANDARD_CLIENT_ID=ncNlUVwO8H5jl2rXFwLmDkVXVlErtAEm5hLWepUOyPY1qqbY
UPS_STANDARD_CLIENT_SECRET=GIREojIxhNgg2Sug0S6XTOEuja4oDxi3vLzgqIcELeRbybSXv05wpFXnGMdAiLjk
UPS_STANDARD_ACCOUNT=C394D0

# WWE API (Worldwide Economy - R5J577)
UPS_WWE_CLIENT_ID=IXqQKQBGAGSGOG5GZ9AvJGzD7VHKhAqPgx8M5Q7Y7GJXQhFG
UPS_WWE_CLIENT_SECRET=G0GAGGyJaJBMGGbQGyZGWUlGLMVa7AAGM5GJAGSd5FAQIAGHGGqQDpBBHGqHBvs
UPS_WWE_ACCOUNT=R5J577
```

**Note**: Template disponible dans `ups.env.template`

---

## 🚀 Utilisation

### Test Standalone

```python
from src.integrations.ups_api import UPSAPIClient

client = UPSAPIClient()

# Get rates for 2kg to USA
rates = client.get_shipping_rates(
    weight_kg=2.0,
    destination_country='US',
    destination_city='New York',
    destination_postal='10001'
)

for rate in rates:
    print(f"{rate['service_name']}: {rate['price']} {rate['currency']}")
```

### Intégration avec Pricing Engine

```python
from src.engine.engine import PricingEngine, ORIGIN_PARIS
from src.integrations.ups_api import UPSAPIClient

# Initialize both engines
pricing_engine = PricingEngine(origin=ORIGIN_PARIS)
ups_api = UPSAPIClient()

# Compare WWE static vs API real-time
wwe_offers = pricing_engine.price('US', 2.0)
api_rates = ups_api.get_shipping_rates(2.0, 'US')

print("WWE Static Prices:")
for offer in wwe_offers:
    if 'WWE' in offer.service_code or 'DDU' in offer.service_code:
        print(f"  {offer.service_code}: {float(offer.total)} EUR")

print("\nAPI Real-time Prices:")
for rate in api_rates:
    print(f"  {rate['service_name']}: {float(rate['price'])} EUR")
```

---

## 🔄 Dual API System

### STANDARD API (C394D0)
- **Pays couverts**: Europe (30+ pays)
  - FR, DE, ES, IT, PL, NL, BE, AT, CH, SE, NO, DK, FI, PT, GR, IE, CZ, HU, RO, BG, SK, SI, HR, EE, LV, LT, LU, CY, MT
- **Services**:
  - UPS Standard (Code: 11)
  - UPS Express (Code: 07)
  - UPS Express Saver (Code: 65)
- **Délai**: 1-3 jours (Europe)

### WWE API (R5J577)
- **Pays couverts**: Reste du monde (150+ pays)
  - US, GB, JP, AU, BR, CA, CN, IN, ZA, etc.
  - ⚠️ **USA suspendu** (tarifs Trump 2025)
- **Services**:
  - UPS Worldwide Economy DDU (Code: 96)
  - UPS Worldwide Express (Code: 07)
  - UPS Worldwide Expedited (Code: 08)
- **Délai**: 7-14 jours (Economy), 3-5 jours (Express)

**Logique de routage automatique**:
```python
europe_countries = {'FR', 'DE', 'ES', 'IT', ...}
api_type = 'STANDARD' if destination in europe_countries else 'WWE'
```

---

## 📊 Comparaison WWE Static vs API Real-time

### Avantages WWE Static (CSV)
✅ **Aucun credential requis**
✅ **Pas de limite d'appels API**
✅ **Réponse instantanée** (pas de latence réseau)
✅ **Prix garantis** (contrat négocié)
✅ **Pas de dépendance externe**

### Avantages UPS API Real-time
✅ **Prix précis selon adresse exacte**
✅ **Surcharges calculées dynamiquement**
✅ **Services additionnels disponibles** (Express, Ground, etc.)
✅ **Zones résidentielles détectées**
✅ **Tarifs à jour automatiquement**

### Recommandation YOYAKU

**Pour le comparateur Discord** :
1. **Afficher WWE Static en priorité** (prix garantis)
2. **Ajouter API Real-time en option** (prix précis sur demande)
3. **Indiquer la source** : "WWE (contrat)" vs "API (temps réel)"

**Exemple Discord Bot**:
```
📦 Envoi 2kg → USA

💶 Prix WWE (contrat négocié):
  ~~UPS Economy DDU: 13.67 EUR~~ 🚫 SUSPENDU (tarifs Trump)

💡 Prix API temps réel (sur demande):
  UPS Worldwide Express: 45.23 EUR (3-5 jours)
  UPS Worldwide Expedited: 38.91 EUR (4-6 jours)

✅ Alternative recommandée:
  FedEx IP Export: 14.46 EUR
```

---

## 🔧 Architecture Technique

### Authentification OAuth2

```python
# Token flow
1. Encode credentials: Base64(client_id:client_secret)
2. POST https://wwwcie.ups.com/security/v1/oauth/token
3. Grant type: client_credentials
4. Token TTL: 3600s (1 heure)
5. Cache token avec 5min buffer
```

### Rating API Request

```json
{
  "RateRequest": {
    "Shipment": {
      "Shipper": {
        "Name": "YOYAKU SARL",
        "ShipperNumber": "C394D0",
        "Address": {
          "AddressLine": "14 boulevard de la Chapelle",
          "City": "PARIS",
          "PostalCode": "75018",
          "CountryCode": "FR"
        }
      },
      "ShipTo": {
        "Address": {
          "City": "New York",
          "CountryCode": "US",
          "PostalCode": "10001"
        }
      },
      "Package": [{
        "PackageWeight": {
          "Weight": "2.0",
          "UnitOfMeasurement": {"Code": "KGS"}
        }
      }]
    }
  }
}
```

### Response Parsing

```json
{
  "RateResponse": {
    "RatedShipment": [
      {
        "Service": {"Code": "96"},
        "TotalCharges": {
          "MonetaryValue": "45.23",
          "CurrencyCode": "EUR"
        }
      }
    ]
  }
}
```

---

## 🧪 Tests

### Test Basique

```bash
cd /Users/yoyaku/repos/pricing-engine
python3 src/integrations/ups_api.py
```

**⚠️ Important: TEST Environment Limitations**

Le code utilise actuellement l'environnement TEST (`wwwcie.ups.com`). Cet environnement a des **restrictions importantes**:

**Erreur courante en TEST**:
```
ERROR: 400 - {"response":{"errors":[{"code":"111100","message":"The requested service is invalid from the selected origin."}]}}
```

**Cause**: L'environnement TEST UPS ne supporte pas toutes les combinaisons origine/destination.

**Solutions**:
1. **Production**: Passer en production (`onlinetools.ups.com`) - voir section ci-dessous
2. **Fallback**: Utiliser UPS WWE static (CSV) pour les tests

### Test avec Credentials Manquants

Si les credentials ne sont pas configurés, le client utilise les **valeurs fallback** du code (credentials de test depuis l'ancien bot).

**Note**: Ces credentials de test ont des limitations strictes en environnement TEST.

---

## ⚠️ Limitations et Restrictions

### Tarifs Trump 2025

Les services UPS WWE vers USA sont **suspendus** via `service_restrictions.json`.

**L'API retournera toujours des prix** mais :
1. Le pricing engine marque l'offre comme `is_suspended=True`
2. Un warning s'affiche : "Service suspendu (tarifs Trump)"
3. L'alternative FedEx est recommandée

### Rate Limits UPS API

**TEST Environment** (`wwwcie.ups.com`):
- Limite: 250 requêtes/heure/application
- Environnement de test uniquement

**PRODUCTION Environment** (`onlinetools.ups.com`):
- Limite: Variable selon contrat
- Nécessite activation par UPS

**Pour passer en PROD**: Changer `self.base_url` dans `UPSAPIClient.__init__()`:
```python
self.base_url = "https://onlinetools.ups.com/api"  # PRODUCTION
```

---

## 📚 Références

**Documentation UPS**:
- Developer Kit: https://www.ups.com/upsdeveloperkit
- Rating API: https://developer.ups.com/api/reference/rating/v1
- OAuth Guide: https://developer.ups.com/api/reference/oauth

**Code source**:
- Client API: `src/integrations/ups_api.py`
- Ancien bot: https://github.com/benjaminbelaga/YOYAKU-Logistics-Bot-Final
- Tests: `test_ups_integration.py` (ancien repo)

**Credentials**:
- Template: `~/.credentials/yoyaku/api-keys/ups.env.template`
- Production: `~/.credentials/yoyaku/api-keys/ups.env`

---

## 🎯 Prochaines Étapes

1. ✅ Client UPS API créé (`src/integrations/ups_api.py`)
2. ⏳ Ajouter service "UPS_API_REALTIME" au data model
3. ⏳ Intégrer dans le bot Discord avec toggle WWE/API
4. ⏳ Tester en production avec vraies credentials
5. ⏳ Comparer précision WWE vs API sur 100 requêtes
6. ⏳ Documenter écarts de prix WWE Static vs API Real-time

---

## 💡 Cas d'Usage

### 1. Comparaison Rapide (Discord)
```
User: /price 2kg usa
Bot: [Affiche prix WWE + FedEx + Spring]
User: /price-api 2kg usa  # Commande alternative
Bot: [Affiche prix UPS API temps réel avec plus de services]
```

### 2. Prix Précis (Checkout)
```python
# Au checkout WooCommerce, utiliser UPS API avec adresse exacte
address = order.get_shipping_address()
rates = ups_api.get_shipping_rates(
    weight_kg=cart_weight,
    destination_country=address['country'],
    destination_city=address['city'],
    destination_postal=address['postcode']
)
# → Prix ultra-précis incluant surcharges résidentielles
```

### 3. Audit de Prix
```python
# Vérifier écart WWE Static vs API Real-time
for country in ['US', 'JP', 'BR', 'AU']:
    wwe_price = pricing_engine.price(country, 2.0)
    api_price = ups_api.get_shipping_rates(2.0, country)

    diff = api_price[0]['price'] - wwe_price[0].total
    print(f"{country}: WWE={wwe_price[0].total}, API={api_price[0]['price']}, Diff={diff}")
```

---

**Version**: 1.0.0
**Dernière mise à jour**: 2025-11-20
**Auteur**: Benjamin Belaga
