"""Node d'agrégation des features et calcul du score de risque."""

import json
from pathlib import Path
from datetime import datetime

from ..state import FraudState

# Features montant/merchant
WEIGHT_ACCOUNT_DRAINED = 0.20
WEIGHT_BALANCE_VERY_LOW = 0.10
WEIGHT_ABNORMAL_AMOUNT = 0.05
WEIGHT_HIGH_AMOUNT = 0.03
WEIGHT_LARGE_WITHDRAWAL = 0.02
WEIGHT_NEW_DEST = 0.15  # Nouveau fraud signal (très important)
WEIGHT_NEW_MERCHANT = 0.08  # Nouveau fraud signal
WEIGHT_POST_WITHDRAWAL = 0.05  # Nouveau fraud signal
WEIGHT_PATTERN_MULTIPLE_WITHDRAWALS = 0.05  # Nouveau fraud signal

# Features pays/voyage
WEIGHT_IMPOSSIBLE_TRAVEL = 0.12
WEIGHT_LOCATION_ANOMALY = 0.05
WEIGHT_LOCATION_MISMATCH = 0.03
WEIGHT_NEW_VENUE = 0.05  # Nouveau fraud signal
WEIGHT_GPS_CONTRADICTION = 0.03

# Features SMS/Email
WEIGHT_TIME_CORRELATION = 0.15  # Nouveau fraud signal (très important)
WEIGHT_PHISHING_INDICATORS = 0.10
WEIGHT_SUSPICIOUS_SMS = 0.04
WEIGHT_SUSPICIOUS_EMAIL = 0.04

# Seuil de score pour considérer une transaction comme fraude
FRAUD_SCORE_THRESHOLD = 0.5


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
    
    # Calcul du score de risque pondéré (basé sur fraud signals du dataset)
    score = (
        # Features montant/merchant
        WEIGHT_ACCOUNT_DRAINED * aggregated_features.get("account_drained", 0) +
        WEIGHT_BALANCE_VERY_LOW * aggregated_features.get("balance_very_low", 0) +
        WEIGHT_ABNORMAL_AMOUNT * aggregated_features.get("abnormal_amount", 0) +
        WEIGHT_HIGH_AMOUNT * aggregated_features.get("high_amount", 0) +
        WEIGHT_LARGE_WITHDRAWAL * aggregated_features.get("large_withdrawal", 0) +
        WEIGHT_NEW_DEST * aggregated_features.get("new_dest", 0) +
        WEIGHT_NEW_MERCHANT * aggregated_features.get("new_merchant", 0) +
        WEIGHT_POST_WITHDRAWAL * aggregated_features.get("post_withdrawal", 0) +
        WEIGHT_PATTERN_MULTIPLE_WITHDRAWALS * aggregated_features.get("pattern_multiple_withdrawals", 0) +
        # Features pays/voyage
        WEIGHT_IMPOSSIBLE_TRAVEL * aggregated_features.get("impossible_travel", 0) +
        WEIGHT_LOCATION_ANOMALY * aggregated_features.get("location_anomaly", 0) +
        WEIGHT_LOCATION_MISMATCH * aggregated_features.get("location_mismatch", 0) +
        WEIGHT_NEW_VENUE * aggregated_features.get("new_venue", 0) +
        WEIGHT_GPS_CONTRADICTION * aggregated_features.get("gps_contradiction", 0) +
        # Features SMS/Email
        WEIGHT_TIME_CORRELATION * aggregated_features.get("time_correlation", 0) +
        WEIGHT_PHISHING_INDICATORS * aggregated_features.get("phishing_indicators", 0) +
        WEIGHT_SUSPICIOUS_SMS * min(aggregated_features.get("suspicious_sms_count", 0), 3) / 3.0 +
        WEIGHT_SUSPICIOUS_EMAIL * min(aggregated_features.get("suspicious_email_count", 0), 3) / 3.0
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
    
    Sauvegarde uniquement les transactions avec score > 0.5 (celles qui seraient
    allées au LLM, donc considérées comme fraudes).
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec results
    """
    transaction_id = state.get("current_transaction_id")
    risk_score = state.get("risk_score", 0.0)
    
    if not transaction_id:
        return state
    
    # Ne sauvegarder que les transactions avec score > 0.5 (fraudes)
    # Ce sont celles qui seraient allées au LLM
    if risk_score <= FRAUD_SCORE_THRESHOLD:
        return state
    
    # Préparation du résultat (uniquement pour les fraudes)
    result = {
        "transaction_id": transaction_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "risk_score": risk_score,
        "decision": state.get("decision", "FRAUDULENT"),  # Par défaut FRAUDULENT si score > 0.5
        "features": state.get("aggregated_features", {}),
        "explanation": state.get("explanation"),
    }
    
    # Ajout au résultat global
    results = state.get("results", [])
    results.append(result)
    
    # Sauvegarde dans un fichier JSON
    output_dir = Path("fraud_graph/results")
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
