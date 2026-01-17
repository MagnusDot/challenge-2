"""Node de récupération des données."""

from Agent.helpers.http_client import make_api_request
from ..state import FraudState


async def fetch_all_data(state: FraudState) -> FraudState:
    """Récupère toutes les données en parallèle via l'API.
    
    Fait un seul appel API qui retourne toutes les données agrégées.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec toutes les données
    """
    transaction_id = state.get("current_transaction_id")
    
    if not transaction_id:
        return state
    
    try:
        endpoint = f"/transactions/{transaction_id}"
        data = await make_api_request("GET", endpoint, response_format="json")
        
        return {
            **state,
            "transaction": data.get("transaction", {}),
            "user_profile": data.get("sender", {}),
            "sms_data": data.get("sender_sms", []) + data.get("recipient_sms", []),
            "email_data": data.get("sender_emails", []) + data.get("recipient_emails", []),
            "location_data": data.get("sender_locations", []) + data.get("recipient_locations", []),
        }
    except Exception as e:
        return {
            **state,
            "transaction": None,
            "user_profile": None,
            "sms_data": [],
            "email_data": [],
            "location_data": [],
        }
