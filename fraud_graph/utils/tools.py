"""Outils pour l'agent LangGraph."""

import json
from datetime import datetime, timezone
from typing import Optional

from Agent.helpers.http_client import make_api_request


async def get_transaction_aggregated(transaction_ids: str) -> str:
    """Récupère les données agrégées d'une ou plusieurs transactions.
    
    Args:
        transaction_ids: UUID de transaction(s) au format JSON string
            - Single: "uuid-here"
            - Batch: ["uuid1", "uuid2", ...]
    
    Returns:
        Données agrégées au format TOON
    """
    try:
        transaction_ids_list = json.loads(transaction_ids)
        if not isinstance(transaction_ids_list, list):
            transaction_ids_list = [transaction_ids_list]
    except (json.JSONDecodeError, TypeError):
        transaction_ids_list = [transaction_ids]
    
    if not transaction_ids_list:
        return "Error: transaction_ids list cannot be empty"
    
    if len(transaction_ids_list) > 200:
        return f"Error: Maximum 200 transaction IDs allowed. Got: {len(transaction_ids_list)}"
    
    for tid in transaction_ids_list:
        if not isinstance(tid, str) or len(tid) != 36:
            return f"Error: Invalid transaction_id (must be 36 chars UUID). Got: {tid}"
    
    if len(transaction_ids_list) == 1:
        endpoint = f"/transactions/{transaction_ids_list[0]}"
        try:
            data = await make_api_request("GET", endpoint, response_format="toon")
            return data
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                return f"Error: Transaction {transaction_ids_list[0]} not found"
            return f"Error: Failed to retrieve transaction {transaction_ids_list[0]}: {error_msg}"
    else:
        endpoint = "/transactions/batch"
        try:
            data = await make_api_request(
                "POST", endpoint, json_data=transaction_ids_list, response_format="toon"
            )
            return data
        except Exception as e:
            error_msg = str(e)
            return f"Error: Failed to retrieve batch transactions: {error_msg}"


async def get_current_time(city: Optional[str] = None) -> str:
    """Retourne l'heure actuelle au format ISO 8601.
    
    Args:
        city: Nom de la ville (optionnel, non utilisé actuellement)
        
    Returns:
        L'heure actuelle au format ISO 8601 (UTC)
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
