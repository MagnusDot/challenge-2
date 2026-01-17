"""Node de récupération des données."""

from Agent.helpers.http_client import make_api_request
from ..state import FraudState


async def fetch_all_data(state: FraudState) -> FraudState:
    """Récupère toutes les données en parallèle via l'API.
    
    Fait un seul appel API qui retourne toutes les données agrégées.
    S'assure que les données sont correctement formatées pour LangGraph.
    
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
        
        # Extraction des données
        # Pydantic model_dump() convertit déjà tout en dicts, y compris les listes
        transaction = data.get("transaction", {})
        sender = data.get("sender", {})
        
        # other_transactions est déjà une liste de dicts (via model_dump())
        user_profile = sender
        
        # Les données sont déjà des listes de dicts (via model_dump())
        sms_data = data.get("sender_sms", []) + data.get("recipient_sms", [])
        email_data = data.get("sender_emails", []) + data.get("recipient_emails", [])
        location_data = data.get("sender_locations", []) + data.get("recipient_locations", [])
        
        return {
            **state,
            "transaction": transaction,
            "user_profile": user_profile,
            "sms_data": sms_data,
            "email_data": email_data,
            "location_data": location_data,
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
