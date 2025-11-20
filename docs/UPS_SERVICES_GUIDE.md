# Guide des Services UPS - YOYAKU Pricing Engine

## 📦 Services UPS Disponibles

### 1. UPS STANDARD (ID 6)
- **Type**: GROUND (économique, délai long)
- **Incoterm**: DAP (Delivered At Place)
- **Direction**: EXPORT depuis FR
- **Couverture**: 10 pays (Asie principalement)
  - CN, GB, ID, JP, KH, LA, MY, PH, TW, VN
- **Prix**: €€ (économique)
- **Délai**: 5-10 jours
- **Use case**: Envois économiques vers Asie

**Exemple**: Japon 2kg = **4.91 EUR** ⭐ (meilleur prix pour JP)

---

### 2. UPS EXPRESS SAVER (ID 5)
- **Type**: EXPRESS (rapide, premium)
- **Incoterm**: DAP (Delivered At Place)
- **Direction**: EXPORT depuis FR
- **Couverture**: 10 pays (mêmes que Standard)
  - CN, GB, ID, JP, KH, LA, MY, PH, TW, VN
- **Prix**: €€€€ (premium)
- **Délai**: 1-3 jours
- **Use case**: Envois urgents vers Asie

**Exemple**: Japon 2kg = **22.71 EUR** (4.6× plus cher que Standard)

---

### 3. UPS ECONOMY DDU EXPORT FR (ID 7) - **WWE EQUIVALENT**
- **Type**: ECONOMY (milieu de gamme)
- **Incoterm**: DDU (Delivered Duty Unpaid - client paie douanes)
- **Direction**: EXPORT depuis FR
- **Couverture**: **88 pays worldwide**
  - Inclut: US, BR, AR, AU, CA, CN, IN, ZA, etc.
- **Prix**: €€€ (milieu de gamme)
- **Délai**: 3-7 jours
- **Use case**: Service worldwide économique

⚠️ **ATTENTION USA**: Service temporairement **SUSPENDU** pour les États-Unis suite aux tarifs douaniers Trump 2025 (effectif depuis 2025-01-20).

**Exemples**:
- ~~USA 2kg = 13.67 EUR~~ 🚫 SUSPENDU
- Brésil 2kg = 25.79 EUR
- Chine 1.5kg = 15.70 EUR

**Alternatives pour USA**:
- FedEx IP Export: 14.46 EUR
- Spring ROW: 28.77 EUR

---

### 4. UPS ECONOMY DDU IMPORT NL (ID 8)
- **Type**: ECONOMY
- **Incoterm**: DDU (Delivered Duty Unpaid)
- **Direction**: IMPORT vers NL (Pays-Bas)
- **Couverture**: 2 pays
  - GB, US
- **Prix**: €€€€
- **Délai**: 3-7 jours
- **Use case**: Import vers Pays-Bas (non pertinent pour YOYAKU FR)

⚠️ **USA SUSPENDU** (tarifs Trump 2025)

---

### 5. UPS EXPRESS DDP EXPORT DE (ID 9)
- **Type**: EXPRESS
- **Incoterm**: DDP (Delivered Duty Paid - YOYAKU paie douanes)
- **Direction**: EXPORT depuis DE (Allemagne)
- **Couverture**: 1 pays
  - GB uniquement
- **Prix**: €€€€
- **Délai**: 1-3 jours
- **Use case**: Export depuis Allemagne (non pertinent pour YOYAKU FR)

---

### 6. UPS EXPRESS DDP IMPORT NL (ID 10)
- **Type**: EXPRESS
- **Incoterm**: DDP (Delivered Duty Paid)
- **Direction**: IMPORT vers NL (Pays-Bas)
- **Couverture**: 3 pays
  - CA, GB, US
- **Prix**: €€€€
- **Délai**: 1-3 jours
- **Use case**: Import Express vers Pays-Bas (non pertinent pour YOYAKU FR)

⚠️ **USA SUSPENDU** (tarifs Trump 2025)

---

## 🎯 Recommandations par Destination

### Asie (CN, JP, KH, LA, MY, PH, TW, VN, ID)
✅ **UPS STANDARD** - Meilleur choix économique
- Exemple: JP 2kg = 4.91 EUR (vs FedEx 13.91 EUR)

### USA 🚫
⚠️ **UPS WWE SUSPENDU** (tarifs Trump 2025)
✅ Alternatives:
1. **FedEx IP Export**: 14.46 EUR (recommandé)
2. Spring ROW: 28.77 EUR

### Amérique du Sud (BR, AR, CL, etc.)
✅ **FedEx IP Export** - Meilleur choix
- FedEx généralement plus compétitif que UPS WWE pour cette zone

### Europe
✅ **Spring EU** ou **La Poste Delivengo**
- UPS ne couvre pas l'Europe dans ces services

---

## 📊 Comparaison Prix USA 2kg

| Service | Prix | Status |
|---------|------|--------|
| ~~UPS Economy DDU (WWE)~~ | ~~13.67 EUR~~ | 🚫 **SUSPENDU** |
| **FedEx IP Export** | **14.46 EUR** | ✅ Recommandé |
| UPS Express DDP Import NL | ~~17.27 EUR~~ | 🚫 SUSPENDU |
| La Poste Delivengo | 24.20 EUR | ✅ Disponible |
| Spring ROW | 28.77 EUR | ✅ Disponible |

---

## 🔧 Gestion des Restrictions

Les restrictions géopolitiques (tarifs Trump, etc.) sont gérées via:
- **Fichier**: `data/service_restrictions.json`
- **Détection automatique**: Le moteur détecte et marque les services suspendus
- **Alternatives suggérées**: FedEx IP, Spring ROW
- **Messages localisés**: FR/EN

**Format PriceOffer**:
```python
offer.is_suspended: bool  # True si service suspendu
offer.warning: str        # Message d'avertissement (FR)
```

---

## 📝 Notes Techniques

### DDU vs DDP
- **DDU** (Delivered Duty Unpaid): Le **client** paie les taxes/douanes
- **DDP** (Delivered Duty Paid): **YOYAKU** paie les taxes/douanes

### Zones Tarifaires
Certains services (DDP Export DE) ont plusieurs zones par pays (CA 1, CA 2, AU 1, AU 2, etc.).
Le moteur prend automatiquement le **prix minimum** parmi les zones.

**Exemple**:
- DDP Export DE vers Canada a 5 zones tarifaires
- Le système garde automatiquement la zone avec le meilleur prix

### Services Non Pertinents pour YOYAKU FR
- **Import NL**: Services d'import vers Pays-Bas (ID 8, 10)
- **Export DE**: Service export depuis Allemagne (ID 9)

Ces services sont dans la base pour référence mais rarement utilisés depuis Paris.

---

## 🚨 Alertes Actives

### Tarifs Trump 2025
**Effectif depuis**: 2025-01-20
**Services affectés**:
- UPS Economy DDU Export FR → USA
- UPS Economy DDU Import NL → USA
- UPS Express DDP Import NL → USA

**Impact**: +110-197% sur les alternatives (FedEx +6%, Spring +110%)

**Action**: Le bot Discord affiche automatiquement un avertissement et suggère FedEx comme alternative.

---

## 📚 Références

- **Fichier source**: `PROPAL YOYAKU ECONOMY DDU (1).xlsx`
- **ETL**: `src/etl/ups_all_services.py`
- **Restrictions**: `data/service_restrictions.json`
- **Total bandes tarifaires**: 3,845
- **Total pays couverts**: 127 (tous services UPS combinés)
