"""Nodes pour le graphe LangGraph de détection de fraude."""

from typing import Dict, Any
import json
import asyncio

from Agent.helpers.http_client import make_api_request
from .state import FraudState


async def ingest_input(state: FraudState) -> FraudState:
    """Node 1: Ingestion des données de transaction.
    
    Récupère les données agrégées de la transaction via l'API.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec transaction et user_profile
    """
    transaction_id = state["transaction_id"]
    
    # Récupération des données agrégées (format JSON pour faciliter le parsing)
    try:
        endpoint = f"/transactions/{transaction_id}"
        data = await make_api_request("GET", endpoint, response_format="json")
        
        # make_api_request avec response_format="json" retourne déjà un dict
        # Pas besoin de json.loads()
        
        return {
            **state,
            "transaction": data.get("transaction", {}),
            "user_profile": data.get("sender", {}),
        }
    except Exception as e:
        return {
            **state,
            "transaction": None,
            "user_profile": None,
            "risk_score": 1.0,  # Score max si erreur
            "decision": "ERROR",
            "explanation": f"Erreur lors de la récupération des données: {str(e)}",
        }


def feature_engineer(state: FraudState) -> FraudState:
    """Node 2: Feature engineering (sans LLM).
    
    Extrait des features déterministes de la transaction et du profil utilisateur.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec features calculées
    """
    transaction = state.get("transaction")
    user_profile = state.get("user_profile")
    
    if not transaction or not user_profile:
        return {
            **state,
            "features": {},
            "risk_score": 1.0,
        }
    
    # Extraction des features
    tx_amount = transaction.get("amount", 0)
    tx_type = transaction.get("transaction_type", "")
    balance_after = transaction.get("balance_after", 0)
    sender_salary = user_profile.get("salary", 0)
    
    # Calcul des features
    features = {
        # Balance critique
        "account_drained": 1 if balance_after == 0.0 else 0,
        "balance_very_low": 1 if 0 < balance_after < 10 else 0,
        
        # Montant anormal par rapport au salaire
        "abnormal_amount": 1 if sender_salary > 0 and tx_amount > sender_salary * 0.3 else 0,
        
        # Type de transaction suspect
        "suspicious_type": 1 if tx_type in ["bonifico", "transfer"] else 0,
        
        # Balance après transaction
        "balance_ratio": balance_after / max(sender_salary / 12, 1) if sender_salary > 0 else 1.0,
        
        # Montant élevé
        "high_amount": 1 if tx_amount > 500 else 0,
        
        # Retrait important
        "large_withdrawal": 1 if tx_type == "prelievo" and tx_amount > 300 else 0,
    }
    
    return {
        **state,
        "features": features,
    }


def risk_scoring(state: FraudState) -> FraudState:
    """Node 3: Calcul du score de risque.
    
    Calcule un score de risque basé sur les features.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec risk_score calculé
    """
    features = state.get("features", {})
    
    if not features:
        return {
            **state,
            "risk_score": 0.0,
        }
    
    # Calcul du score pondéré
    score = (
        0.40 * features.get("account_drained", 0) +  # Poids le plus fort
        0.25 * features.get("balance_very_low", 0) +
        0.15 * features.get("abnormal_amount", 0) +
        0.10 * features.get("suspicious_type", 0) +
        0.05 * features.get("high_amount", 0) +
        0.05 * features.get("large_withdrawal", 0)
    )
    
    # Ajustement basé sur le ratio de balance
    balance_ratio = features.get("balance_ratio", 1.0)
    if balance_ratio < 0.1:  # Moins de 10% du salaire mensuel restant
        score += 0.1
    
    # Normalisation entre 0 et 1
    score = min(1.0, max(0.0, score))
    
    return {
        **state,
        "risk_score": round(score, 2),
    }


def route_on_score(state: FraudState) -> str:
    """Router conditionnel basé sur le score de risque.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        Nom du prochain node: "decision_ok" ou "llm_analysis"
    """
    risk_score = state.get("risk_score", 0.0)
    
    if risk_score <= 0.5:
        return "decision_ok"
    return "llm_analysis"


def decision_ok(state: FraudState) -> FraudState:
    """Node 4: Sortie directe sans LLM (score <= 0.5).
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État final avec décision "LEGITIMATE"
    """
    return {
        **state,
        "decision": "LEGITIMATE",
        "llm_result": None,
        "explanation": f"Score de risque faible ({state.get('risk_score', 0.0)}): transaction légitime",
    }
