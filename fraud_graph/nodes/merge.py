"""Nodes de merge pour combiner les résultats parallèles."""

from ..state import FraudState


def merge_prescoring_results(state: FraudState) -> FraudState:
    """Merge les résultats des nodes de pré-scoring parallèles.
    
    Ce node est appelé après que tous les prescoring nodes aient terminé.
    LangGraph combine automatiquement les états, donc on retourne juste l'état.
    
    Args:
        state: État avec toutes les features calculées
        
    Returns:
        État inchangé (déjà combiné par LangGraph)
    """
    return state
