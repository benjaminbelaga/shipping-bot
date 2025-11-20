# UPS Integration Status - 2025-11-20

## 🎯 Objectif Principal
**Intégrer UPS API pour pricing temps réel - À TOUT PRIX** ⚠️

---

## ✅ Ce Qui Est Fait

### 1. UPS WWE Static (CSV) - PRODUCTION READY ✅

**Extraction complète**: 6 services UPS depuis Excel
- ✅ `UPS_STANDARD` (10 pays Asie) - Ex: Japon 2kg = 4.91 EUR
- ✅ `UPS_EXPRESS_SAVER` (10 pays)
- ✅ `UPS_ECONOMY_DDU_EXPORT_FR` (88 pays worldwide)
- ✅ `UPS_ECONOMY_DDU_IMPORT_NL` (2 pays)
- ✅ `UPS_EXPRESS_DDP_EXPORT_DE` (1 pays)
- ✅ `UPS_EXPRESS_DDP_IMPORT_NL` (3 pays)

**Total**: 3,845 pricing bands

**Fichiers**:
- `src/etl/ups_all_services.py` - ETL extraction
- `data/carriers/ups_*.csv` - Pricing data
- `data/service_restrictions.json` - Restrictions Trump

**Fonctionnalités**:
- ✅ Multi-zone handling (CA 1-5, AU 1-3) → minimum price
- ✅ Deduplication automatique
- ✅ Trump tariffs restrictions
- ✅ PriceOffer avec warnings

**Test**:
```python
from src.engine.engine import PricingEngine, ORIGIN_PARIS
engine = PricingEngine(origin=ORIGIN_PARIS)
offers = engine.price('JP', 2.0)  # Japon 2kg = 4.91 EUR ✅
```

### 2. UPS API Client - CODE COMPLET ⚠️

**Fichier**: `src/integrations/ups_api.py` (411 lignes)

**Implémenté**:
- ✅ OAuth2 authentication avec token caching
- ✅ Dual API system (STANDARD C394D0 + WWE R5J577)
- ✅ Automatic routing (Europe → STANDARD, Monde → WWE)
- ✅ RequestOption "Shop" pour tous les services
- ✅ Credentials management depuis ~/.credentials
- ✅ Production/Test environment switching

**Classes**:
- `UPSCredentials` (dataclass)
- `UPSCredentialsManager` (environment loader)
- `UPSAPIClient` (OAuth2 + Rating API)

**Status**: Code fonctionnel mais **API retourne erreur 111100**

### 3. Documentation Complète ✅

**Guides créés**:
- `docs/UPS_SERVICES_GUIDE.md` - Nomenclature 6 services
- `docs/UPS_API_INTEGRATION.md` - Guide technique API
- `docs/UPS_INTEGRATION_COMPLETE.md` - Rapport de synthèse
- `~/.credentials/yoyaku/api-keys/ups.env` - Credentials configurés

---

## ❌ Ce Qui Bloque

### Problème Principal: Error 111100

**Erreur UPS API**:
```json
{
  "response": {
    "errors": [{
      "code": "111100",
      "message": "The requested service is invalid from the selected origin."
    }]
  }
}
```

**Tests effectués**:

| Test | Environment | Auth | Rating | Résultat |
|------|-------------|------|--------|----------|
| STANDARD (DE) | TEST | ✅ Token OK | ❌ 111100 | Échec |
| STANDARD (DE) | PROD | ✅ Token OK | ❌ 111100 | Échec |
| WWE (US) | TEST | ❌ 401 | - | Échec auth |
| WWE (US) | PROD | ❌ 401 | - | Échec auth |

**Compte utilisé**: C394D0 (Rating approved depuis 2025-05-22)

**Payload envoyé**: ✅ Correct (RequestOption: "Shop", ShipFrom Paris)

**Ancien bot**: ❌ Même erreur (bot ne fonctionne pas non plus)

### Hypothèses

1. **Compte UPS mal configuré**
   - C394D0 approuvé pour Rating API ✅
   - Mais peut-être pas activé pour origine France?
   - Besoin activation spécifique UPS?

2. **Credentials WWE manquants**
   - WWE (R5J577) retourne 401 Unauthorized
   - Credentials de l'ancien bot périmés?
   - Besoin nouvelle app WWE?

3. **Paramètre manquant dans payload**
   - NegotiatedRatesIndicator?
   - Pickup type spécifique?
   - Champ requis non documenté?

4. **Restrictions géographiques**
   - Compte C394D0 limité à certaines destinations?
   - France non autorisée comme origine pour Rating?

---

## 🎯 Plan d'Action UPS API

### Phase 1: Investigation (URGENT)

**Action 1**: Contacter UPS Support
- [ ] Ouvrir ticket support UPS Developer Portal
- [ ] Question: "Error 111100 avec compte C394D0 depuis France"
- [ ] Demander activation complète Rating API pour origine FR
- [ ] Vérifier si compte nécessite configuration spéciale

**Action 2**: Tester avec compte différent
- [ ] Créer nouveau compte UPS Developer
- [ ] Activer Rating API
- [ ] Tester si erreur 111100 persiste
- [ ] Comparer configuration avec C394D0

**Action 3**: Analyser payload UPS
- [ ] Utiliser Postman UPS collection officielle
- [ ] Tester exemple exact de la doc UPS
- [ ] Comparer différences avec notre payload
- [ ] Identifier paramètre manquant

**Action 4**: Tester variations payload
```python
# Test 1: Sans dimensions
# Test 2: Avec NegotiatedRatesIndicator
# Test 3: PackagingType différent (01 UPS Letter vs 02 Customer)
# Test 4: Pickup type spécifique
# Test 5: ShipperNumber dans ShipFrom aussi
```

### Phase 2: Solution Alternative (Si API bloquée)

**Option A**: UPS Web Services (XML)
- Tester ancienne API XML au lieu de REST
- Peut-être moins de restrictions
- Documentation: https://www.ups.com/upsdeveloperkit

**Option B**: UPS Plugin/SDK officiel
- Utiliser SDK Python UPS officiel
- Peut gérer la configuration automatiquement
- Vérifier si disponible

**Option C**: Partenariat UPS
- Contacter account manager UPS France
- Demander accès API entreprise
- Négocier activation complète

### Phase 3: Fallback Temporaire

**En attendant résolution API**:
- ✅ Utiliser UPS WWE CSV (fonctionne parfaitement)
- ✅ Afficher dans bot Discord comme "UPS (grille tarifaire)"
- ⏳ Ajouter note: "Tarifs API temps réel à venir"

---

## 📝 TODO List Complète

### Immédiat (Cette semaine)

- [ ] **Contacter UPS Support** - Ouvrir ticket error 111100
- [ ] **Tester Postman UPS** - Collection officielle
- [ ] **Variations payload** - 5 tests différents
- [ ] **Créer compte test** - Nouveau developer account

### Court terme (Semaine prochaine)

- [ ] **Résoudre error 111100** - Avec aide UPS support
- [ ] **Obtenir credentials WWE** - Nouveau app R5J577
- [ ] **Tests production complets** - 20+ destinations
- [ ] **Benchmark WWE CSV vs API** - Comparer précision

### Moyen terme (2-4 semaines)

- [ ] **Intégration bot Discord** - Commande `/price-api`
- [ ] **Cache API responses** - 15-30min TTL
- [ ] **Monitoring API usage** - Rate limits
- [ ] **Documentation utilisateur** - Guide bot Discord

### Long terme (1-2 mois)

- [ ] **A/B testing** - WWE CSV vs API temps réel
- [ ] **Analytics pricing** - Écarts CSV/API
- [ ] **Optimisation coûts** - Réduire appels API
- [ ] **Production rollout** - 100% trafic sur API

---

## 🔧 Debugging Tools

### Test UPS API
```bash
cd /Users/yoyaku/repos/pricing-engine

# Test basic
python3 src/integrations/ups_api.py

# Test avec debug
python3 -c "
from src.integrations.ups_api import UPSAPIClient
import logging
logging.basicConfig(level=logging.DEBUG)
client = UPSAPIClient(production=True)
rates = client.get_shipping_rates(1.0, 'DE', 'Berlin', '10115')
print(rates)
"

# Test credentials
cat ~/.credentials/yoyaku/api-keys/ups.env
```

### Vérifier dashboard UPS
- URL: https://developer.ups.com/apps
- Compte: C394D0
- Vérifier: Rating API status, billing account, services approved

### Postman Collection
- Importer: https://www.postman.com/ups-api/ups-apis
- Tester: Rating API → Shop request
- Comparer: Payload + response vs notre code

---

## 📊 Métriques de Succès

**UPS API sera considéré comme réussi quand**:

1. ✅ Authentication fonctionne (STANDARD + WWE)
2. ✅ Rating API retourne tarifs pour 10+ destinations
3. ✅ Précision ±5% vs UPS.com quotes
4. ✅ Latence <2 secondes par requête
5. ✅ Intégré dans bot Discord production
6. ✅ Utilisé par clients réels sans erreur

---

## 💡 Resources

**UPS Documentation**:
- Developer Portal: https://developer.ups.com
- Rating API: https://developer.ups.com/api/reference?loc=en_US&tag=Rating
- OAuth Guide: https://developer.ups.com/api/reference/oauth
- Postman: https://www.postman.com/ups-api/ups-apis

**Support**:
- Developer Forum: https://developer.ups.com/support
- Email: developersupport@ups.com
- Phone: 1-800-742-5877 (US)

**Code Reference**:
- Old bot: /tmp/YOYAKU-Logistics-Bot-Final
- New integration: /Users/yoyaku/repos/pricing-engine/src/integrations/ups_api.py
- Tests: /Users/yoyaku/repos/pricing-engine/test_ups_api_scenarios.py (à créer)

---

## 🎬 Next Steps

**Prochaine session de travail**:

1. **Ouvrir ticket UPS** (30min)
   - Décrire erreur 111100
   - Fournir payload + response
   - Demander activation origine France

2. **Tester Postman** (1h)
   - Importer collection officielle
   - Reproduire leur exemple exact
   - Identifier différences

3. **Tests variations** (1h)
   - 5 variations payload différentes
   - Logger chaque résultat
   - Documenter ce qui change

4. **Pendant attente UPS** (2-3 jours)
   - Intégrer UPS WWE CSV dans bot Discord
   - Créer commande `/price` fonctionnelle
   - Préparer infra pour switch vers API

**Timeline estimé**: 1-2 semaines pour résoudre API ou trouver alternative

---

**Status**: 🟡 En cours - Bloqué sur error 111100 mais solutions en vue
**Priorité**: 🔴 HAUTE - UPS API requis à tout prix
**Owner**: Benjamin Belaga
**Last Update**: 2025-11-20
