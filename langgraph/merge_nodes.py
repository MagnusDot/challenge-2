"""Nodes de merge pour combiner les résultats parallèles."""

from .state import FraudState


def merge_fetch_results(state: FraudState) -> FraudState:
    """Merge les résultats des fetch nodes parallèles.
    
    Ce node est appelé après que tous les fetch nodes aient terminé.
    LangGraph appelle automatiquement ce node avec l'état combiné.
    
    Args:
        state: État avec toutes les données fetchées
        
    Returns:
        État inchangé (déjà combiné par LangGraph)
    """
    # LangGraph combine automatiquement les états, donc on retourne juste l'état
    return state


def merge_prescoring_results(state: FraudState) -> FraudState:
    """Merge les résultats des nodes de pré-scoring parallèles.
    
    Ce node est appelé après que tous les prescoring nodes aient terminé.
    
    Args:
        state: État avec toutes les features calculées
        
    Returns:
        État inchangé (déjà combiné par LangGraph)
    """
    # LangGraph combine automatiquement les états, donc on retourne juste l'état
    return state
