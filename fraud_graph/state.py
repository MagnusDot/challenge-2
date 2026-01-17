from typing import TypedDict, Optional, Dict, Any, List


class FraudState(TypedDict):
    transaction_ids: List[str]
    current_transaction_id: Optional[str]
    transaction: Optional[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]]
    sms_data: Optional[List[Dict[str, Any]]]
    email_data: Optional[List[Dict[str, Any]]]
    location_data: Optional[List[Dict[str, Any]]]
    amount_merchant_features: Optional[Dict[str, Any]]
    country_travel_features: Optional[Dict[str, Any]]
    sms_email_features: Optional[Dict[str, Any]]
    aggregated_features: Optional[Dict[str, Any]]
    risk_score: float
    decision: Optional[str]
    llm_result: Optional[Dict[str, Any]]
    explanation: Optional[str]
    results: List[Dict[str, Any]]
