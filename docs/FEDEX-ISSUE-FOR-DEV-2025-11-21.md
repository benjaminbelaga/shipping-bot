# 🚨 PROBLÈME FEDEX - Pour Développeur External

**Date:** 2025-11-21 01:15 UTC
**Rapporté par:** Benjamin Belaga
**Priorité:** HAUTE - FedEx absent pour destinations majeures (Georgia, Germany, South Korea, etc.)

---

## 🎯 PROBLÈME RÉSUMÉ

**User Query:** `/price 1kg Georgia`
**Résultat:** 5 services (Delivengo + UPS) mais **PAS de FedEx** ❌

**Destinations affectées:** Georgia, Germany <24kg, South Korea, Russia, et probablement beaucoup d'autres

**Scepticisme justifié:**
- 🇰🇷 South Korea absent de FedEx? **ABSURDE** - c'est un marché majeur FedEx!
- 🇩🇪 Germany nécessite 24kg+? **ABSURDE** - FedEx livre des colis légers en Allemagne!
- Georgia pas couvert? **Probablement faux**

---

## 🔍 ROOT CAUSE SUSPECTÉ

### Données CSV Actuelles:

**UPS Services:** 6 services différents
```
UPS_EXPRESS_SAVER
UPS_STANDARD
UPS_ECONOMY_DDU_EXPORT_FR
UPS_ECONOMY_DDU_IMPORT_NL
UPS_EXPRESS_DDP_EXPORT_DE
UPS_EXPRESS_DDP_IMPORT_NL
```

**FedEx Services:** 1 SEUL service! ❌
```
FDX_IP_EXPORT (FedEx International Priority Export)
```

**Conclusion:** Les données FedEx sont **INCOMPLÈTES**! Il manque probablement:
- FedEx Economy
- FedEx Express Standard
- FedEx Ground
- FedEx International Economy
- Autres services comme UPS

---

## 📊 DONNÉES TECHNIQUES

### Fichiers CSV Concernés

**Location:** `/Users/yoyaku/repos/pricing-engine/data/normalized/`

1. **services.csv** - Définition services carriers
2. **tariff_scopes.csv** - Zones géographiques (16 zones FedEx A-X)
3. **tariff_scope_countries.csv** - Mapping pays → zones
4. **tariff_bands.csv** - Grilles tarifaires par poids

### Contenu Actuel services.csv

```csv
service_id,carrier_id,code,label,direction,origin_iso2,incoterm,service_type,max_weight_kg,volumetric_divisor,active_from,active_to
1,1,DELIVENGO_2025,Delivengo Profil 2025,EXPORT,FR,DAP,MAIL,2.0,5000,2025-01-01,
2,2,SPRING_EU_HOME,Spring Europe domicile,EXPORT,FR,DAP,PARCEL,20.0,5000,2025-01-01,
3,2,SPRING_ROW_HOME,Spring Reste du monde domicile,EXPORT,FR,DAP,PARCEL,20.0,5000,2025-01-01,
4,3,FDX_IP_EXPORT,FedEx International Priority Export,EXPORT,FR,DAP,EXPRESS,70.5,5000,2025-01-01,
5,4,UPS_EXPRESS_SAVER,UPS Express Saver,EXPORT,FR,DAP,EXPRESS,70.0,5000,2023-04-22,
6,4,UPS_STANDARD,UPS Standard,EXPORT,FR,DAP,GROUND,70.0,5000,2023-04-22,
7,4,UPS_ECONOMY_DDU_EXPORT_FR,UPS Economy DDU Export FR,EXPORT,FR,DDU,ECONOMY,70,5000,2022-04-10,
8,4,UPS_ECONOMY_DDU_IMPORT_NL,UPS Economy DDU Import NL,IMPORT,NL,DDU,ECONOMY,70,5000,2022-04-10,
9,4,UPS_EXPRESS_DDP_EXPORT_DE,UPS Express DDP Export DE,EXPORT,DE,DDP,EXPRESS,70,5000,2022-04-10,
10,4,UPS_EXPRESS_DDP_IMPORT_NL,UPS Express DDP Import NL,IMPORT,NL,DDP,EXPRESS,70,5000,2022-04-10,
```

**Observation:** UPS = 6 lignes, FedEx = 1 ligne seulement!

---

## 🧪 TESTS REPRODUCTIBLES

### Test 1: Georgia 1kg (User Report)

```bash
cd /Users/yoyaku/repos/pricing-engine
python3 -m src.engine.engine price GE 1kg
```

**Résultat actuel:**
```
Delivengo: 16.00 EUR
UPS WWE: 21.78 EUR
UPS API: 3 services (39.37, 97.98, 114.02 EUR)
FedEx: ❌ RIEN
```

**Résultat attendu:**
```
Devrait avoir FedEx Economy ~20-25 EUR
```

### Test 2: Germany 2kg

```bash
python3 -m src.engine.engine price DE 2kg --debug
```

**Résultat actuel:**
```
⏭️ FDX_IP_EXPORT: no band for 2.0kg
(Germany en Zone R avec minimum 24kg!)
```

**Résultat attendu:**
```
FedEx Economy/Standard pour Germany 2kg devrait être disponible
```

### Test 3: South Korea 2kg

```bash
python3 -m src.engine.engine price KR 2kg
```

**Résultat actuel:**
```
Probablement pas de FedEx
```

**Résultat attendu:**
```
FedEx doit servir South Korea (marché majeur!)
```

---

## 📋 ANALYSE DÉTAILLÉE DU PROBLÈME

### Problème 1: Service Unique FedEx

**État actuel:** Seulement `FDX_IP_EXPORT` existe
**Impact:** Couverture limitée, zones avec restrictions poids

**Preuve:**
```bash
$ cat data/normalized/services.csv | grep -i fedex
4,3,FDX_IP_EXPORT,FedEx International Priority Export,EXPORT,FR,DAP,EXPRESS,70.5,5000,2025-01-01,
```

**Résultat:** 1 ligne seulement

### Problème 2: Zone R (Germany) Min 24kg

**État actuel:** Germany dans Zone R avec minimum 24kg
**Impact:** Aucun colis <24kg ne peut utiliser FedEx pour Germany

**Preuve:**
```bash
# Germany est en scope 47 (Zone R)
$ grep ",DE$" data/normalized/tariff_scope_countries.csv | grep "^47,"
47,DE

# Zone R weight bands commence à 24kg
$ grep "^[0-9]*,47," data/normalized/tariff_bands.csv | head -1
XXXXX,47,24.0,24.0,XX.XX,0.0,False
```

### Problème 3: Pays Manquants

**Pays qui DEVRAIENT avoir FedEx mais absents:**
- GE (Georgia)
- KR (South Korea)
- RU (Russia) - possible sanctions mais suspect
- Autres pays non testés

**Preuve à générer:**
```python
import csv

fedex_scope_ids = list(range(38, 54))
fedex_countries = set()

with open('data/normalized/tariff_scope_countries.csv', 'r') as f:
    for row in csv.DictReader(f):
        if int(row['scope_id']) in fedex_scope_ids:
            fedex_countries.add(row['country_iso2'])

# Test pays majeurs
test_countries = ['US', 'CN', 'JP', 'KR', 'DE', 'FR', 'GB', 'AU', 'CA', 'BR', 'IN', 'RU', 'GE']
for country in test_countries:
    status = '✅' if country in fedex_countries else '❌'
    print(f"{status} {country}")
```

---

## 💡 SOLUTION PROPOSÉE

### Option 1: Ajouter Services FedEx Manquants

**Étapes:**

1. **Obtenir grille tarifaire FedEx France Export** (PDF ou Excel officiel)

2. **Identifier tous les services FedEx disponibles:**
   - FedEx International Priority (existe déjà)
   - FedEx International Economy (manquant)
   - FedEx International Standard (manquant)
   - Autres services selon grille

3. **Créer entries dans services.csv:**
```csv
11,3,FDX_ECONOMY_EXPORT,FedEx International Economy Export,EXPORT,FR,DAP,ECONOMY,70.5,5000,2025-01-01,
12,3,FDX_EXPRESS_EXPORT,FedEx International Express,EXPORT,FR,DAP,EXPRESS,70.5,5000,2025-01-01,
...
```

4. **Créer scopes pour chaque nouveau service:**
   - FDX_ECONOMY_ZONE_A, FDX_ECONOMY_ZONE_B, etc.
   - Avec couverture pays correcte (incluant GE, KR, etc.)
   - Avec weight bands dès 0.5kg ou 1kg

5. **Tester:**
```bash
python3 -m src.engine.engine price GE 1kg  # Devrait avoir FedEx
python3 -m src.engine.engine price DE 2kg  # Devrait avoir FedEx
python3 -m src.engine.engine price KR 2kg  # Devrait avoir FedEx
```

### Option 2: Corriger Zone R (Germany)

**Si Germany doit rester en Zone R pour Priority:**
- Créer service FedEx Economy avec Germany en zone différente (min 1kg)
- Germany aura 2 zones FedEx : Zone R (Priority 24kg+) + Zone X (Economy 1kg+)

**Structure:**
```
FDX_IP_EXPORT (Priority):
  - Zone R (Germany): 24kg+ seulement

FDX_ECONOMY_EXPORT (Economy):
  - Zone E (Germany): 1kg+ disponible
```

### Option 3: Valider Avec Grille Réelle

**Avant tout changement:**
1. Consulter grille tarifaire FedEx officielle
2. Vérifier couverture pays réelle
3. Vérifier services réels disponibles
4. Parser données et créer CSV conformes

---

## 🔧 FICHIERS À MODIFIER

### 1. services.csv
**Action:** Ajouter lignes pour services FedEx manquants

**Exemple:**
```csv
# Ajouter après ligne 4:
11,3,FDX_ECONOMY_EXPORT,FedEx International Economy Export,EXPORT,FR,DAP,ECONOMY,70.5,5000,2025-01-01,
12,3,FDX_STANDARD_EXPORT,FedEx International Standard,EXPORT,FR,DAP,GROUND,70.5,5000,2025-01-01,
```

### 2. tariff_scopes.csv
**Action:** Créer scopes pour nouveaux services

**Exemple:**
```csv
# Ajouter scopes pour FDX_ECONOMY_EXPORT (service_id 11):
54,11,FDX_ECONOMY_ZONE_A,FedEx Economy Export - Zone A,False
55,11,FDX_ECONOMY_ZONE_B,FedEx Economy Export - Zone B,False
...
```

### 3. tariff_scope_countries.csv
**Action:** Mapper pays aux nouveaux scopes

**Exemple:**
```csv
# Ajouter Georgia, South Korea, Germany à scopes appropriés:
54,GE   # Georgia en FedEx Economy Zone A
54,KR   # South Korea en FedEx Economy Zone A
54,DE   # Germany en FedEx Economy Zone A (1kg+ disponible)
...
```

### 4. tariff_bands.csv
**Action:** Créer weight bands pour nouveaux scopes

**Exemple:**
```csv
# FedEx Economy Zone A (scope 54) avec bands 0.5kg-70kg:
XXXX,54,0.5,0.5,12.50,0.0,False
XXXX,54,1.0,1.0,15.00,0.0,False
XXXX,54,1.5,1.5,17.50,0.0,False
XXXX,54,2.0,2.0,20.00,0.0,False
...
```

---

## 📊 DONNÉES D'EXPORT POUR ANALYSE

### Export 1: Liste Pays FedEx Actuels

```bash
cd /Users/yoyaku/repos/pricing-engine

python3 << 'EOF' > /tmp/fedex_countries.txt
import csv

fedex_scope_ids = list(range(38, 54))
countries = set()

with open('data/normalized/tariff_scope_countries.csv', 'r') as f:
    for row in csv.DictReader(f):
        if int(row['scope_id']) in fedex_scope_ids:
            countries.add(row['country_iso2'])

print(f"Total FedEx countries (current): {len(countries)}\n")
print("Countries list:")
for country in sorted(countries):
    print(country)
EOF

cat /tmp/fedex_countries.txt
```

### Export 2: Weight Ranges par Zone

```bash
python3 << 'EOF' > /tmp/fedex_zones.txt
import csv

fedex_scope_ids = list(range(38, 54))

# Get scope names
scopes = {}
with open('data/normalized/tariff_scopes.csv', 'r') as f:
    for row in csv.DictReader(f):
        if int(row['scope_id']) in fedex_scope_ids:
            scopes[row['scope_id']] = row['code']

# Get weight bands for each scope
print("FedEx Zones Weight Ranges:\n")
for scope_id in sorted(scopes.keys(), key=int):
    with open('data/normalized/tariff_bands.csv', 'r') as f:
        bands = [row for row in csv.DictReader(f) if row['scope_id'] == scope_id]
        if bands:
            min_w = min(float(b['min_weight_kg']) for b in bands)
            max_w = max(float(b['max_weight_kg']) for b in bands)
            print(f"Scope {scope_id} ({scopes[scope_id]}): {min_w}kg - {max_w}kg ({len(bands)} bands)")
        else:
            print(f"Scope {scope_id} ({scopes[scope_id]}): NO BANDS")
EOF

cat /tmp/fedex_zones.txt
```

### Export 3: Comparaison UPS vs FedEx

```bash
cat data/normalized/services.csv | grep "^[0-9]*,[34]," > /tmp/ups_fedex_comparison.txt
echo "\n=== ANALYSIS ===" >> /tmp/ups_fedex_comparison.txt
echo "UPS services: $(grep ',4,' /tmp/ups_fedex_comparison.txt | wc -l)" >> /tmp/ups_fedex_comparison.txt
echo "FedEx services: $(grep ',3,' /tmp/ups_fedex_comparison.txt | wc -l)" >> /tmp/ups_fedex_comparison.txt

cat /tmp/ups_fedex_comparison.txt
```

---

## ✅ CHECKLIST DÉVELOPPEUR

**Avant Correction:**
- [ ] Obtenir grille tarifaire FedEx France Export officielle
- [ ] Lire documentation FedEx services disponibles
- [ ] Identifier pays couverts par FedEx réellement
- [ ] Identifier services FedEx disponibles (Economy, Express, Standard, etc.)

**Pendant Correction:**
- [ ] Créer entries services.csv pour chaque service FedEx
- [ ] Créer scopes tariff_scopes.csv (zones géographiques)
- [ ] Mapper pays tariff_scope_countries.csv (GE, KR, DE <24kg, etc.)
- [ ] Créer weight bands tariff_bands.csv (0.5kg-70kg)
- [ ] Vérifier cohérence avec grille officielle

**Après Correction:**
- [ ] Test Georgia 1kg → FedEx disponible
- [ ] Test Germany 2kg → FedEx disponible
- [ ] Test South Korea 2kg → FedEx disponible
- [ ] Test USA 2kg → FedEx disponible (déjà OK, vérifier pas cassé)
- [ ] Test Japan 2kg → FedEx disponible (déjà OK, vérifier pas cassé)
- [ ] Test 20+ destinations majeures
- [ ] Comparer nombre services FedEx vs UPS (devrait être similaire ~4-6)
- [ ] Vérifier prices compétitifs (FedEx Economy < FedEx Priority)

**Documentation:**
- [ ] Mettre à jour README avec services FedEx ajoutés
- [ ] Documenter sources données (grille FedEx utilisée)
- [ ] Créer changelog des modifications

---

## 🎓 RÉFÉRENCES UTILES

### Documentation Projet:
- `docs/COMPLETE-TESTING-SCENARIOS-2025-11-21.md` - Tests 10 pays (contient possibles erreurs)
- `docs/FEDEX-COVERAGE-ANALYSIS-2025-11-21.md` - Analyse détaillée (basé sur données incomplètes)
- `docs/UPS-API-INTEGRATION-GUIDE.md` - Exemple intégration carrier API
- `QUICK-START-PRODUCTION.md` - Deployment guide

### Code Source:
- `src/engine/engine.py:price()` - Logique pricing principale
- `src/engine/loader.py` - Chargement CSV → Python objects
- `src/bot/commands.py:price` - Discord command handler

### Structure Données:
```
data/normalized/
├── carriers.csv          # 4 carriers (Delivengo, Spring, FedEx, UPS)
├── services.csv          # 10 services (1 FedEx, 6 UPS, 2 Spring, 1 Delivengo)
├── tariff_scopes.csv     # 203 scopes (zones géographiques)
├── tariff_scope_countries.csv  # Mapping scope → pays
└── tariff_bands.csv      # ~15,000 weight bands
```

---

## 📞 CONTACT & REPOSITORY

**Projet:** YOYAKU Shipping Price Comparator Bot
**GitHub:** https://github.com/benjaminbelaga/shipping-bot
**Branch:** main
**Status:** ✅ Tout poussé sur GitHub (git status clean)

**Développeur:**
- Benjamin Belaga (ben@yoyaku.fr)
- Prêt à fournir grilles tarifaires si nécessaire

**User Report Original:**
```
"bien joué mais y a pas Fedex check stp et essay ed e comrpendre si fedex
ne montre pas pour d'autre endroit aussi"

Scepticisme:
- South Korea absent? ABSURDE
- Germany 24kg+? ABSURDE
- Georgia pas couvert? Suspect
```

**Conclusion:** User a raison d'être sceptique - données FedEx probablement incomplètes

---

## 🚨 PRIORITÉ CORRECTIF

**HIGH PRIORITY:**
1. Germany 2kg - Market majeur, doit avoir FedEx
2. South Korea - Market majeur, doit avoir FedEx
3. Georgia - User query original

**MEDIUM PRIORITY:**
4. Russia - Vérifier si sanctions ou données manquantes
5. Autres pays européens <24kg
6. Pays Asie/Afrique/Amérique Latine

**VALIDATION:**
- Comparer couverture finale FedEx vs UPS (devrait être ~180-190 pays chacun)
- Vérifier nombre services similaire (UPS=6, FedEx devrait être 4-6)
- Tester 50+ destinations avec poids variés

---

**Créé:** 2025-11-21 01:15 UTC
**Par:** Benjamin Belaga
**Status:** ✅ PRÊT POUR CORRECTION EXTERNE
**Git:** ✅ Tout pushé sur GitHub
