# LangGraph Fraud Detection

Architecture hybride combinant des règles déterministes et un LLM conditionnel pour la détection de fraude.

## Architecture

```
┌─────────────────────────────┐
│ fetch_all_transaction_ids   │  Récupère tous les IDs via API
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ process_single_transaction  │  Initialise le traitement
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│    fetch_all_data          │  Récupère toutes les données (API)
└──────────────┬──────────────┘
               ↓
    ┌──────────┴──────────┐
    │                     │
    ↓                     ↓
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Amount & │    │ Country &│    │ SMS/Email│
│ Merchant │    │ Travel   │    │ Analysis │
│ Analysis │    │ Analysis │    │          │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     └───────────────┴───────────────┘
                     ↓
        ┌────────────────────────┐
        │ merge_prescoring_results│
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │aggregate_features_score │  Agrège features + score
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │  save_result_to_json   │  Sauvegarde JSON (score > 0.5)
        └────────────┬───────────┘
                     ↓
        ┌────────────────────────┐
        │    route_on_score      │  Routing conditionnel
        └──────┬───────────────┘
               │
    score ≤ 0.5│  │ score > 0.5
               │  │
    ┌──────────▼──┐  ┌──────────────┐
    │ decision_ok │  │ llm_analysis │
    │  (NO LLM)   │  │ (Google ADK) │
    └──────┬──────┘  └──────┬──────┘
           │                 │
           └────────┬────────┘
                    ↓
        ┌────────────────────────┐
        │ get_next_transaction   │  Passe à la suivante
        └──────┬─────────────────┘
               │
        continue│  │ end
               │  │
    ┌──────────▼──┐  ┌──────────────┐
    │   continue   │  │     END     │
    │  (boucle)    │  │             │
    └──────────────┘  └──────────────┘
```

## Principe Clé

**Le graphe décide s'il appelle le LLM, pas le LLM lui-même.**

- **Score ≤ 0.5** → Sortie directe (pas d'appel LLM) → Transaction légitime
- **Score > 0.5** → Appel LLM (Google ADK) → Analyse approfondie

## Avantages

✅ **Déterministe**: Features et scoring basés sur des règles claires  
✅ **Explicable**: Score de risque calculé de manière transparente  
✅ **Efficace**: LLM appelé uniquement pour les cas suspects  
✅ **Économique**: Réduction des coûts LLM pour les transactions légitimes

## Structure

```
langgraph/
├── __init__.py              # Module principal avec exports
├── agent.py                 # Point d'entrée principal
├── graph.py                 # Construction du graphe LangGraph
├── state.py                 # Définition du state TypedDict
├── README.md                # Documentation
├── nodes/                   # Tous les nodes du graphe
│   ├── __init__.py
│   ├── fetch.py            # Récupération des données (API)
│   ├── prescoring.py       # Pré-scoring parallèle (3 analyses)
│   ├── merge.py            # Merge des résultats parallèles
│   ├── aggregation.py      # Agrégation features + score + sauvegarde
│   ├── routing.py          # Routing conditionnel et décision
│   └── llm.py              # Node LLM avec Google ADK
├── utils/                   # Utilitaires
│   ├── __init__.py
│   └── tools.py            # Outils pour l'agent
└── examples/                # Exemples d'utilisation
    └── example.py
```

## Features Calculées (Pré-scoring Parallèle)

Basées sur les **fraud signals** identifiés dans le dataset .

### 1. Amount & Merchant Analysis
- `account_drained`: Balance = 0.00
- `balance_very_low`: Balance < 10€
- `abnormal_amount`: Montant > 30% du salaire
- `high_amount`: Montant > 500€
- `large_withdrawal`: Retrait > 300€
- `suspicious_type`: Type de transaction suspect
- `unknown_merchant`: Merchant inconnu ou description vide
- `suspicious_keywords`: Mots-clés suspects dans la description
- **`new_dest`**: Nouveau destinataire jamais vu (fraud signal)
- **`new_merchant`**: Nouveau merchant e-commerce jamais vu (fraud signal)
- **`post_withdrawal`**: Transaction après retrait suspect (fraud signal)
- **`pattern_multiple_withdrawals`**: Pattern de retraits multiples (fraud signal)

### 2. Country & Travel Analysis
- `location_missing`: Localisation manquante
- `location_mismatch`: Localisation différente de la résidence
- `gps_available`: Coordonnées GPS disponibles
- `gps_contradiction`: Contradiction GPS
- `distance_from_residence`: Distance depuis la résidence (km)
- **`impossible_travel`**: Voyage impossible (> 1000km) (fraud signal)
- **`location_anomaly`**: Anomalie de localisation (> 100km) (fraud signal)
- **`new_venue`**: Nouveau lieu physique jamais vu (fraud signal)

### 3. SMS/Email Analysis
- `has_sms`: Présence de SMS
- `has_email`: Présence d'emails
- `suspicious_sms_count`: Nombre de SMS suspects
- `suspicious_email_count`: Nombre d'emails suspects
- `phishing_indicators`: Indicateurs de phishing
- `total_communications`: Nombre total de communications
- **`time_correlation`**: Transaction dans les 4h après phishing (fraud signal)

## Score de Risque

Score pondéré (0-1) après agrégation, basé sur les fraud signals du dataset:

### Features Montant/Merchant (poids total: ~68%)
- `new_dest`: 15% (très important - nouveau destinataire)
- `account_drained`: 20%
- `balance_very_low`: 10%
- `new_merchant`: 8%
- `abnormal_amount`: 5%
- `post_withdrawal`: 5%
- `pattern_multiple_withdrawals`: 5%
- Autres: 5%

### Features Pays/Voyage (poids total: ~28%)
- `impossible_travel`: 12%
- `location_anomaly`: 5%
- `new_venue`: 5%
- `location_mismatch`: 3%
- `gps_contradiction`: 3%

### Features SMS/Email (poids total: ~33%)
- `time_correlation`: 15% (très important - corrélation temporelle avec phishing)
- `phishing_indicators`: 10%
- `suspicious_sms_count`: 4%
- `suspicious_email_count`: 4%

**Note**: Les poids sont optimisés pour détecter les 6 scénarios de fraude du dataset:
1. `bank_fraud_alert` - Alerte banque frauduleuse
2. `subscription_renewal` - Renouvellement abonnement
3. `parcel_customs_fee` - Frais douane colis
4. `identity_verification` - Vérification identité
5. `bec_urgent_invoice` - BEC facture urgente
6. `atm_card_cloned` - Carte clonée

## Utilisation

### Analyse de toutes les transactions

```python
from langgraph.agent import create_fraud_detection_graph

# Création du graphe
app = create_fraud_detection_graph()

# État initial (vide - le graphe récupère les IDs automatiquement)
initial_state = {
    "transaction_ids": [],  # Rempli automatiquement par fetch_all_transaction_ids
    "current_transaction_id": None,
    "transaction": None,
    "user_profile": None,
    "sms_data": None,
    "email_data": None,
    "location_data": None,
    "amount_merchant_features": None,
    "country_travel_features": None,
    "sms_email_features": None,
    "aggregated_features": None,
    "risk_score": 0.0,
    "decision": None,
    "llm_result": None,
    "explanation": None,
    "results": [],
}

# Exécution (traite toutes les transactions automatiquement)
result = await app.ainvoke(initial_state)

# Les fraudes sont sauvegardées dans fraud_graph/results/
print(f"Fraudes détectées: {len(result.get('results', []))}")
```

### Analyse d'une transaction spécifique

```python
# État initial avec une transaction spécifique
initial_state = {
    "transaction_ids": ["uuid-here"],
    # ... autres champs
}

result = await app.ainvoke(initial_state)
```

## Sauvegarde des Résultats

Les résultats sont automatiquement sauvegardés dans `fraud_graph/results/fraud_analysis_YYYYMMDD_HHMMSS.json`.

**Important**: Seules les transactions avec un score de risque > 0.5 (fraude) sont sauvegardées.

Chaque résultat sauvegardé contient:
- Transaction ID
- Timestamp
- Risk score
- Decision
- Features agrégées
- Explanation

## Configuration

Utilise les mêmes variables d'environnement que l'agent principal:
- `MODEL`: Modèle LLM à utiliser
- `OPENROUTER_API_KEY`: Clé API OpenRouter
- `SYSTEM_PROMPT_FILE`: Fichier de prompt système
