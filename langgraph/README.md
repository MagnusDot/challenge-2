# LangGraph Fraud Detection

Architecture hybride combinant des règles déterministes et un LLM conditionnel pour la détection de fraude.

## Architecture

```
┌─────────────────────────┐
│ process_single_transaction│  Initialise le traitement
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│    fetch_all_data       │  Récupère toutes les données (API)
└────────────┬────────────┘
             ↓
    ┌────────┴────────┐
    │                 │
    ↓                 ↓
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
        │  save_result_to_json   │  Sauvegarde JSON
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
    └─────────────┘  └──────────────┘
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

- `state.py`: Définition du state TypedDict
- `fetch_nodes.py`: Node de récupération des données (API)
- `prescoring_nodes.py`: Nodes de pré-scoring parallèles (amount/merchant, country/travel, SMS/email)
- `merge_nodes.py`: Nodes de merge pour combiner les résultats parallèles
- `aggregation_node.py`: Agrégation des features et calcul du score + sauvegarde JSON
- `nodes.py`: Nodes utilitaires (routing, decision_ok)
- `llm_node.py`: Node LLM utilisant Google ADK
- `graph.py`: Construction du graphe LangGraph
- `tools.py`: Outils pour l'agent (réutilisés depuis Agent/tools)
- `agent.py`: Point d'entrée principal

## Features Calculées (Pré-scoring Parallèle)

### 1. Amount & Merchant Analysis
- `account_drained`: Balance = 0.00
- `balance_very_low`: Balance < 10€
- `abnormal_amount`: Montant > 30% du salaire
- `high_amount`: Montant > 500€
- `large_withdrawal`: Retrait > 300€
- `suspicious_type`: Type de transaction suspect
- `unknown_merchant`: Merchant inconnu ou description vide
- `suspicious_keywords`: Mots-clés suspects dans la description

### 2. Country & Travel Analysis
- `location_missing`: Localisation manquante
- `location_mismatch`: Localisation différente de la résidence
- `gps_available`: Coordonnées GPS disponibles
- `gps_contradiction`: Contradiction GPS
- `distance_from_residence`: Distance depuis la résidence (km)
- `impossible_travel`: Voyage impossible (> 1000km)

### 3. SMS/Email Analysis
- `has_sms`: Présence de SMS
- `has_email`: Présence d'emails
- `suspicious_sms_count`: Nombre de SMS suspects
- `suspicious_email_count`: Nombre d'emails suspects
- `phishing_indicators`: Indicateurs de phishing
- `total_communications`: Nombre total de communications

## Score de Risque

Score pondéré (0-1) après agrégation:
- **50%** Features montant/merchant (account_drained: 25%, balance_very_low: 15%, etc.)
- **25%** Features pays/voyage (impossible_travel: 15%, location_mismatch: 5%, etc.)
- **25%** Features SMS/Email (phishing_indicators: 15%, suspicious counts: 10%)

## Utilisation

```python
from langgraph.agent import create_fraud_detection_graph

# Création du graphe
app = create_fraud_detection_graph()

# Exécution
initial_state = {
    "transaction_ids": ["uuid-here"],
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

result = await app.ainvoke(initial_state)
```

## Sauvegarde des Résultats

Les résultats sont automatiquement sauvegardés dans `langgraph/results/fraud_analysis_YYYYMMDD_HHMMSS.json` avec:
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
