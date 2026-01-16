"""
Aggregated Transaction API tool for agent.
"""

from typing import Any, Dict

from Agent.helpers.http_client import make_api_request


async def get_transaction_aggregated(transaction_id: str) -> str:
    """
    Récupère une transaction avec TOUTES les données agrégées associées.
    
    Cet outil unique retourne en un seul appel :
    - Les détails complets de la transaction
    - Les informations de l'expéditeur (profil, résidence, salaire, profession)
    - Les informations du destinataire (si disponible)
    - Tous les emails de l'expéditeur et du destinataire
    - Tous les SMS de l'expéditeur et du destinataire  
    - Les données de localisation GPS proches de la date de transaction
    
    Utilisez cet outil pour :
    - Analyser une transaction suspecte de fraude
    - Obtenir le contexte complet d'une transaction
    - Vérifier la cohérence entre transaction, communications et localisation
    - Détecter des anomalies comportementales
    
    Args:
        transaction_id: L'UUID de la transaction (36 caractères)
        
    Returns:
        String JSON formaté avec toutes les données agrégées
        
    Example:
        >>> result = await get_transaction_aggregated("7634023d-5751-4940-a2c9-36b97274f366")
        >>> # Retourne un JSON avec transaction, sender, recipient, emails, sms, locations
    """
    # Validate transaction_id format
    if not transaction_id or len(transaction_id) != 36:
        return f"""Status: error
Message: Invalid transaction_id format. Must be 36 characters UUID.
Provided: {transaction_id}

No data available."""
    
    endpoint = f"/transactions/{transaction_id}"
    
    try:
        # Make API call (asynchronous) - returns full JSON
        data = await make_api_request("GET", endpoint)
        
        # Format response with clear structure
        import json
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        
        return f"""Status: success
Transaction ID: {transaction_id}

Aggregated Data:
{formatted_json}

Data includes:
- Transaction details (amount, type, location, timestamp, etc.)
- Sender profile (name, job, salary, residence)
- Recipient profile (if available)
- Sender emails and SMS
- Recipient emails and SMS  
- GPS locations near transaction time"""
    
    except Exception as e:
        error_msg = str(e)
        
        # Handle 404 specifically
        if "404" in error_msg:
            return f"""Status: error
Message: Transaction not found
Transaction ID: {transaction_id}

The transaction with this ID does not exist in the database."""
        
        # Generic error
        return f"""Status: error
Message: Failed to retrieve aggregated transaction: {error_msg}
Transaction ID: {transaction_id}

No data available."""

