# Stratégie d'Amélioration de la Détection de Fraude

## Problème Actuel

Après les améliorations, les résultats se sont dégradés :
- **Avant** : 4/11 TP, 0 FP (Précision 100%, Rappel 36%)
- **Maintenant** : 3/11 TP, 6 FP (Précision 33%, Rappel 27%)

## Analyse des Faux Positifs

Tous les faux positifs ont en commun :
1. **Balance > 0€** (pas de vidage de compte)
2. **Montant < 30% du salaire** (pas d'anomalie de montant)
3. **Seulement "new_merchant"** comme raison (sans time_correlation ni autres indicateurs)

### Exemples de Faux Positifs
- Transaction e-commerce de 103€ avec balance de 4254€ → Détectée comme fraude avec "new_merchant"
- Transaction e-commerce de 59€ avec balance de 545€ → Détectée comme fraude avec "new_merchant"
- Transaction transfer de 630€ avec balance de 963€ → Détectée comme fraude avec "new_dest,amount_anomaly"

## Solution : Approche Conservatrice

### Principe : "Mieux vaut manquer une fraude que d'accuser un innocent"

1. **Règles strictes pour chaque pattern** :
   - **BEC Urgent Invoice** : Balance DOIT être exactement €0.00 (pas €100, pas €500)
   - **Parcel Customs Fee** : DOIT avoir time_correlation + phishing email/SMS (new_merchant seul n'est PAS suffisant)
   - **Identity Verification** : DOIT avoir pattern_multiple_withdrawals + location_anomaly (ville différente de résidence)
   - **Card Cloning** : DOIT avoir new_venue + location_anomaly + séquence de transactions (ville différente)

2. **Indicateurs seuls = PAS de fraude** :
   - new_merchant seul = NORMAL (shopping normal)
   - new_dest seul = NORMAL (envoi d'argent normal)
   - amount_anomaly seul = NORMAL (gros achats légitimes)
   - location_anomaly seul = NORMAL (voyages normaux)

3. **Combinaisons requises** :
   - new_merchant + time_correlation + phishing email/SMS = FRAUD
   - new_dest + account_drained (€0.00) + amount_anomaly = FRAUD
   - pattern_multiple_withdrawals + location_anomaly (ville différente) = FRAUD

## Améliorations Apportées au Prompt

1. **Règles plus strictes** : Chaque pattern nécessite TOUS ses indicateurs
2. **Exceptions claires** : Liste explicite de ce qui n'est PAS de la fraude
3. **Balance critique** : Seulement €0.00 = account draining, pas €100 ou €500
4. **Time correlation obligatoire** : Pour parcel_customs_fee, time_correlation est MANDATORY

## Prochaines Étapes

1. Tester avec le prompt amélioré
2. Analyser les résultats
3. Ajuster si nécessaire
4. Si les faux positifs persistent, ajouter des outils API spécialisés pour aider l'agent
