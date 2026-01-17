"""Node d'agrégation des features et calcul du score de risque."""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from ..state import FraudState

# Verrou pour la sauvegarde thread-safe
_save_lock = asyncio.Lock()


# Features montant/merchant
# Ajustés selon analyse comparative : vraies fraudes (10) vs faux positifs (100)
# Features très discriminantes : account_drained (40% vs 0%), high_amount (30% vs 5%), suspicious_type (30% vs 5%)
WEIGHT_ACCOUNT_DRAINED = 0.30  # TRÈS DISCRIMINANT (40% vraies fraudes vs 0% faux positifs)
WEIGHT_BALANCE_VERY_LOW = 0.03  # Réduit (moins discriminant)
WEIGHT_ABNORMAL_AMOUNT = 0.10  # Moyen (5/11 fraudes = 45%)
WEIGHT_HIGH_AMOUNT = 0.15  # DISCRIMINANT (30% vraies fraudes vs 5% faux positifs = 6x)
WEIGHT_LARGE_WITHDRAWAL = 0.01  # Réduit (moins discriminant)
WEIGHT_NEW_DEST = 0.05  # RÉDUIT (trop commun : 100% faux positifs aussi)
WEIGHT_NEW_MERCHANT = 0.10  # Moyen (2/11 fraudes = 18%)
WEIGHT_POST_WITHDRAWAL = 0.08  # Moyen (2/11 fraudes = 18%)
WEIGHT_PATTERN_MULTIPLE_WITHDRAWALS = 0.15  # Important (4/11 fraudes = 36%)
WEIGHT_SUSPICIOUS_TYPE = 0.12  # DISCRIMINANT (30% vraies fraudes vs 5% faux positifs = 6x)

# Features pays/voyage
WEIGHT_IMPOSSIBLE_TRAVEL = 0.20  # Important (6/11 fraudes = 55%)
WEIGHT_LOCATION_ANOMALY = 0.18  # Important (6/11 fraudes = 55%)
WEIGHT_LOCATION_MISMATCH = 0.01  # TRÈS RÉDUIT (95% faux positifs aussi - trop commun)
WEIGHT_NEW_VENUE = 0.08  # Moyen (2/11 fraudes = 18%)
WEIGHT_GPS_CONTRADICTION = 0.02  # Réduit (moins discriminant)
WEIGHT_LOCATION_MISSING = 0.01  # Réduit (moins discriminant)

# Features SMS/Email
WEIGHT_TIME_CORRELATION = 0.25  # TRÈS IMPORTANT (9/11 fraudes = 82% dans ground truth)
WEIGHT_PHISHING_INDICATORS = 0.01  # TRÈS RÉDUIT (100% faux positifs - trop commun)
WEIGHT_SUSPICIOUS_SMS = 0.05  # Moyen (peu présent mais discriminant quand présent)
WEIGHT_SUSPICIOUS_EMAIL = 0.01  # TRÈS RÉDUIT (100% faux positifs - trop commun)

FRAUD_SCORE_THRESHOLD = 0.25


async def save_fraud_result_async(result: dict, transaction_id: str) -> None:
    """Sauvegarde un résultat de fraude de manière thread-safe (version async).
    
    Utilisée pour le traitement parallèle de plusieurs transactions.
    
    Args:
        result: Dictionnaire avec les résultats de l'analyse
        transaction_id: ID de la transaction
    """
    async with _save_lock:
        output_dir = Path("fraud_graph/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "fraud.json"
        
        # Charger les données existantes si le fichier existe
        existing_data = []
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except (json.JSONDecodeError, IOError):
                # Si le fichier est corrompu, on repart de zéro
                existing_data = []
        
        # Vérifier si cette transaction n'est pas déjà dans le fichier (éviter les doublons)
        existing_ids = {item.get("transaction_id") for item in existing_data if isinstance(item, dict)}
        if transaction_id not in existing_ids:
            existing_data.append(result)
        
        # Sauvegarder
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)


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
        WEIGHT_SUSPICIOUS_TYPE * aggregated_features.get("suspicious_type", 0) +
        # Features pays/voyage
        WEIGHT_IMPOSSIBLE_TRAVEL * aggregated_features.get("impossible_travel", 0) +
        WEIGHT_LOCATION_ANOMALY * aggregated_features.get("location_anomaly", 0) +
        WEIGHT_LOCATION_MISMATCH * aggregated_features.get("location_mismatch", 0) +
        WEIGHT_NEW_VENUE * aggregated_features.get("new_venue", 0) +
        WEIGHT_GPS_CONTRADICTION * aggregated_features.get("gps_contradiction", 0) +
        WEIGHT_LOCATION_MISSING * aggregated_features.get("location_missing", 0) +
        # Features SMS/Email
        WEIGHT_TIME_CORRELATION * aggregated_features.get("time_correlation", 0) +
        WEIGHT_PHISHING_INDICATORS * aggregated_features.get("phishing_indicators", 0) +
        WEIGHT_SUSPICIOUS_SMS * min(aggregated_features.get("suspicious_sms_count", 0), 3) / 3.0 +
        WEIGHT_SUSPICIOUS_EMAIL * min(aggregated_features.get("suspicious_email_count", 0), 3) / 3.0
    )
    
    # SUPPRIMÉ : Ajustement basé sur balance_ratio (trop commun dans faux positifs)
    # balance_ratio présent dans 100% des faux positifs, donc non discriminant
    
    # Identification des transactions sûrement normales
    # Si AUCUNE feature critique n'est activée, c'est probablement une transaction normale
    critical_features = [
        "account_drained",
        "high_amount",
        "suspicious_type",
        "impossible_travel",
        "location_anomaly",
        "time_correlation",
        "pattern_multiple_withdrawals",
        "new_merchant",
        "post_withdrawal",
        "new_venue",
    ]
    
    has_critical_feature = any(
        aggregated_features.get(feature, 0) == 1 
        for feature in critical_features
    )
    
    # Si aucune feature critique ET score bas, réduire drastiquement le score
    # (transaction sûrement normale)
    if not has_critical_feature and score < 0.3:
        score = score * 0.3  # Réduction drastique pour les transactions normales
    
    # Bonus pour les transactions avec plusieurs features critiques
    # (même si le score de base est bas, plusieurs signaux = suspect)
    critical_count = sum(
        1 for feature in critical_features 
        if aggregated_features.get(feature, 0) == 1
    )
    if critical_count >= 2:
        score += 0.15  # Bonus pour plusieurs signaux critiques
    
    # Normalisation entre 0 et 1
    score = min(1.0, max(0.0, score))
    
    return {
        **state,
        "aggregated_features": aggregated_features,
        "risk_score": round(score, 2),
    }


def save_result_to_json(state: FraudState) -> FraudState:
    """Sauvegarde le résultat dans un fichier JSON (version sync pour le graphe).
    
    Sauvegarde les transactions suspectes (score > 0.15) pour tri ultérieur.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec results
    """
    transaction_id = state.get("current_transaction_id")
    risk_score = state.get("risk_score", 0.0)
    
    if not transaction_id:
        return state
    
    # Sauvegarder les transactions avec score > 0.15 (suspectes)
    if risk_score <= FRAUD_SCORE_THRESHOLD:
        return state
    
    # Préparation du résultat (pour les éléments suspects)
    result = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "risk_score": risk_score,
        "decision": state.get("decision", "SUSPECT"),  # Tag SUSPECT pour tri ultérieur
        "features": state.get("aggregated_features", {}),
        "explanation": state.get("explanation"),
    }
    
    # Ajout au résultat global
    results = state.get("results", [])
    results.append(result)
    
    # Sauvegarde dans un fichier JSON unique (fraud.json) - version sync
    output_dir = Path("fraud_graph/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "fraud.json"
    
    # Charger les données existantes si le fichier existe
    existing_data = []
    if output_file.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except (json.JSONDecodeError, IOError):
            # Si le fichier est corrompu, on repart de zéro
            existing_data = []
    
    # Vérifier si cette transaction n'est pas déjà dans le fichier (éviter les doublons)
    existing_ids = {item.get("transaction_id") for item in existing_data if isinstance(item, dict)}
    if transaction_id not in existing_ids:
        existing_data.append(result)
    
    # Sauvegarder
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    return {
        **state,
        "results": results,
    }
