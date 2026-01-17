"""Nodes d'initialisation du graphe."""

from Agent.helpers.http_client import make_api_request
from ..state import FraudState


async def fetch_all_transaction_ids(state: FraudState) -> FraudState:
    """Récupère tous les IDs de transactions via l'API.
    
    Args:
        state: État initial du graphe
        
    Returns:
        État mis à jour avec transaction_ids
    """
    try:
        endpoint = "/transactions/ids"
        data = await make_api_request("GET", endpoint, response_format="json")
        
        transaction_ids = data.get("transaction_ids", [])
        
        return {
            **state,
            "transaction_ids": transaction_ids,
            "results": [],
        }
    except Exception as e:
        return {
            **state,
            "transaction_ids": [],
            "results": [],
        }
