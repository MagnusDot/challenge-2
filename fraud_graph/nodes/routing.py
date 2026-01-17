"""Nodes de routing et décision."""

from ..state import FraudState

# Seuil de score pour décider d'appeler le LLM
RISK_SCORE_THRESHOLD = 0.5


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
    
    Gère à la fois les transactions légitimes et frauduleuses sans appel LLM.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État final avec décision appropriée (LEGITIMATE ou FRAUDULENT)
    """
    risk_score = state.get("risk_score", 0.0)
    
    # Décision basée sur le score de risque (sans LLM)
    if risk_score > RISK_SCORE_THRESHOLD:
        decision = "FRAUDULENT"
        explanation = f"Score de risque élevé ({risk_score}): transaction suspecte détectée"
    else:
        decision = "LEGITIMATE"
        explanation = f"Score de risque faible ({risk_score}): transaction légitime"
    
    return {
        **state,
        "decision": decision,
        "llm_result": None,
        "explanation": explanation,
    }
