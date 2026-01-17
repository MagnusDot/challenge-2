"""Nodes de routing et décision."""

from ..state import FraudState

# Seuil de score pour considérer une transaction comme légitime
# Seuil bas : seulement les scores très faibles (< 0.15) sont considérés comme légitimes
# Entre 0.15 et 0.25 : zone grise (sera taggé comme SUSPECT)
# > 0.25 : SUSPECT (sauvegardé dans fraud.json)
LEGITIMATE_SCORE_THRESHOLD = 0.15


def route_on_score(state: FraudState) -> str:
    """Router conditionnel basé sur le score de risque.
    
    LLM désactivé pour le moment - toujours route vers decision_ok.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        Nom du prochain node: "decision_ok" (LLM désactivé)
    """
    # LLM désactivé - toujours route vers decision_ok
    return "decision_ok"


def decision_ok(state: FraudState) -> FraudState:
    """Node de sortie directe sans LLM.
    
    Système permissif de tagging : seulement les scores très bas sont légitimes.
    Tout le reste est taggé comme SUSPECT pour tri ultérieur.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État final avec décision appropriée (LEGITIMATE ou SUSPECT)
    """
    risk_score = state.get("risk_score", 0.0)
    
    # Système permissif : seulement les scores très bas (< 0.1) sont légitimes
    # Tout le reste est taggé comme SUSPECT pour tri ultérieur
    if risk_score < LEGITIMATE_SCORE_THRESHOLD:
        decision = "LEGITIMATE"
        explanation = f"Score de risque très faible ({risk_score:.2f}): transaction légitime"
    else:
        decision = "SUSPECT"
        explanation = f"Score de risque ({risk_score:.2f}): élément suspect détecté (à trier)"
    
    return {
        **state,
        "decision": decision,
        "llm_result": None,
        "explanation": explanation,
    }
