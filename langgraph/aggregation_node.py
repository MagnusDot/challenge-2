"""Node d'agrégation des features et calcul du score de risque."""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .state import FraudState


def aggregate_features_and_score(state: FraudState) -> FraudState:
    """Agrège toutes les features et calcule le score de risque.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec aggregated_features et risk_score
    """
    # Récupération des features parallèles
    amount_features = state.get("amount_merchant_features", {})
    country_features = state.get("country_travel_features", {})
    sms_email_features = state.get("sms_email_features", {})
    
    # Agrégation de toutes les features
    aggregated_features = {
        **amount_features,
        **country_features,
        **sms_email_features,
    }
    
    # Calcul du score de risque pondéré
    score = (
        # Features montant/merchant (poids total: 50%)
        0.25 * aggregated_features.get("account_drained", 0) +
        0.15 * aggregated_features.get("balance_very_low", 0) +
        0.05 * aggregated_features.get("abnormal_amount", 0) +
        0.03 * aggregated_features.get("high_amount", 0) +
        0.02 * aggregated_features.get("large_withdrawal", 0) +
        
        # Features pays/voyage (poids total: 25%)
        0.15 * aggregated_features.get("impossible_travel", 0) +
        0.05 * aggregated_features.get("location_mismatch", 0) +
        0.05 * aggregated_features.get("gps_contradiction", 0) +
        
        # Features SMS/Email (poids total: 25%)
        0.15 * aggregated_features.get("phishing_indicators", 0) +
        0.05 * min(aggregated_features.get("suspicious_sms_count", 0), 3) / 3.0 +
        0.05 * min(aggregated_features.get("suspicious_email_count", 0), 3) / 3.0
    )
    
    # Ajustement basé sur le ratio de balance
    balance_ratio = aggregated_features.get("balance_ratio", 1.0)
    if balance_ratio < 0.1:
        score += 0.1
    
    # Normalisation entre 0 et 1
    score = min(1.0, max(0.0, score))
    
    return {
        **state,
        "aggregated_features": aggregated_features,
        "risk_score": round(score, 2),
    }


def save_result_to_json(state: FraudState) -> FraudState:
    """Sauvegarde le résultat dans un fichier JSON.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État inchangé
    """
    transaction_id = state.get("current_transaction_id")
    
    if not transaction_id:
        return state
    
    # Préparation du résultat
    result = {
        "transaction_id": transaction_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "risk_score": state.get("risk_score", 0.0),
        "decision": state.get("decision", "UNKNOWN"),
        "features": state.get("aggregated_features", {}),
        "explanation": state.get("explanation"),
    }
    
    # Ajout au résultat global
    results = state.get("results", [])
    results.append(result)
    
    # Sauvegarde dans un fichier JSON
    output_dir = Path("langgraph/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"fraud_analysis_{timestamp}.json"
    
    # Si le fichier existe, charger et ajouter, sinon créer
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
            existing_data.append(result)
            data_to_save = existing_data
    else:
        data_to_save = [result]
    
    # Sauvegarder
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    
    return {
        **state,
        "results": results,
    }
