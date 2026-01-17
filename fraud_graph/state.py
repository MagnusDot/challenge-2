"""State definition for LangGraph fraud detection."""

from typing import TypedDict, Optional, Dict, Any, List


class FraudState(TypedDict):
    """État du graphe de détection de fraude."""
    transaction_ids: List[str]  # Liste des IDs à traiter
    current_transaction_id: Optional[str]  # ID en cours de traitement
    transaction: Optional[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]]
    sms_data: Optional[List[Dict[str, Any]]]
    email_data: Optional[List[Dict[str, Any]]]
    location_data: Optional[List[Dict[str, Any]]]
    # Features parallèles
    amount_merchant_features: Optional[Dict[str, Any]]
    country_travel_features: Optional[Dict[str, Any]]
    sms_email_features: Optional[Dict[str, Any]]
    # Features agrégées
    aggregated_features: Optional[Dict[str, Any]]
    risk_score: float
    decision: Optional[str]
    llm_result: Optional[Dict[str, Any]]
    explanation: Optional[str]
    results: List[Dict[str, Any]]  # Résultats pour chaque transaction
