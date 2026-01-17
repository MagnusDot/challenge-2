from datetime import datetime
from typing import Optional

async def get_current_time(city: Optional[str] = None) -> str:
    """Retourne l'heure actuelle au format ISO 8601.
    
    Args:
        city: Nom de la ville (optionnel, non utilisé actuellement)
        
    Returns:
        L'heure actuelle au format ISO 8601 (UTC)
    """
    return datetime.utcnow().isoformat() + "Z"