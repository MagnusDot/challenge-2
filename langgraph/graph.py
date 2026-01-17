"""Construction du graphe LangGraph pour la détection de fraude."""

from langgraph.graph import StateGraph, END

from .state import FraudState
from .fetch_nodes import fetch_all_data
from .prescoring_nodes import (
    analyze_amount_merchant,
    analyze_country_travel,
    analyze_sms_email,
)
from .merge_nodes import merge_prescoring_results
from .aggregation_node import aggregate_features_and_score, save_result_to_json
from .nodes import route_on_score, decision_ok
from .llm_node import llm_analysis


def process_single_transaction(state: FraudState) -> FraudState:
    """Initialise le traitement d'une transaction unique.
    
    Args:
        state: État avec transaction_ids
        
    Returns:
        État avec current_transaction_id défini
    """
    transaction_ids = state.get("transaction_ids", [])
    
    if not transaction_ids:
        return state
    
    # Prendre la première transaction de la liste
    current_id = transaction_ids[0]
    
    return {
        **state,
        "current_transaction_id": current_id,
        "results": state.get("results", []),
    }


def create_fraud_detection_graph():
    """Crée et compile le graphe LangGraph pour la détection de fraude.
    
    Architecture parallèle:
    1. process_single_transaction: Initialise le traitement
    2. fetch_transaction_data, fetch_user_profile, fetch_communications: Récupération parallèle
    3. analyze_amount_merchant, analyze_country_travel, analyze_sms_email: Pré-scoring parallèle
    4. aggregate_features_and_score: Agrégation et calcul du score
    5. save_result_to_json: Sauvegarde du résultat
    6. route_on_score: Route conditionnel (score <= 0.5 → decision_ok, sinon → llm_analysis)
    7. decision_ok: Sortie directe sans LLM
    8. llm_analysis: Analyse approfondie avec Google ADK
    
    Returns:
        Graph LangGraph compilé
    """
    # Création du graphe
    graph = StateGraph(FraudState)
    
    # Node d'initialisation
    graph.add_node("process_single_transaction", process_single_transaction)
    
    # Node de récupération (une seule API call qui retourne tout)
    graph.add_node("fetch_all_data", fetch_all_data)
    
    # Nodes de pré-scoring en parallèle
    graph.add_node("analyze_amount_merchant", analyze_amount_merchant)
    graph.add_node("analyze_country_travel", analyze_country_travel)
    graph.add_node("analyze_sms_email", analyze_sms_email)
    
    # Node de merge après prescoring
    graph.add_node("merge_prescoring_results", merge_prescoring_results)
    
    # Node d'agrégation
    graph.add_node("aggregate_features_and_score", aggregate_features_and_score)
    graph.add_node("save_result_to_json", save_result_to_json)
    
    # Nodes de décision
    graph.add_node("decision_ok", decision_ok)
    graph.add_node("llm_analysis", llm_analysis)
    
    # Point d'entrée
    graph.set_entry_point("process_single_transaction")
    
    # Récupération des données (une seule API call)
    graph.add_edge("process_single_transaction", "fetch_all_data")
    
    # Pré-scoring parallèle (après fetch)
    graph.add_edge("fetch_all_data", "analyze_amount_merchant")
    graph.add_edge("fetch_all_data", "analyze_country_travel")
    graph.add_edge("fetch_all_data", "analyze_sms_email")
    
    # Merge des résultats de prescoring
    graph.add_edge("analyze_amount_merchant", "merge_prescoring_results")
    graph.add_edge("analyze_country_travel", "merge_prescoring_results")
    graph.add_edge("analyze_sms_email", "merge_prescoring_results")
    
    # Agrégation (après merge prescoring)
    graph.add_edge("merge_prescoring_results", "aggregate_features_and_score")
    
    # Sauvegarde puis routing conditionnel
    graph.add_edge("aggregate_features_and_score", "save_result_to_json")
    
    # Edge conditionnel basé sur le score (après sauvegarde)
    graph.add_conditional_edges(
        "save_result_to_json",
        route_on_score,
        {
            "decision_ok": "decision_ok",
            "llm_analysis": "llm_analysis",
        }
    )
    
    # Points de sortie
    graph.add_edge("decision_ok", END)
    graph.add_edge("llm_analysis", END)
    
    # Compilation
    app = graph.compile()
    
    return app
