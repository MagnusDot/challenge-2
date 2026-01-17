"""Construction du graphe LangGraph pour la détection de fraude."""

from langgraph.graph import StateGraph, END

from .state import FraudState
from .nodes import (
    fetch_all_transaction_ids,
    fetch_all_data,
    analyze_amount_merchant,
    analyze_country_travel,
    analyze_sms_email,
    merge_prescoring_results,
    aggregate_features_and_score,
    save_result_to_json,
    route_on_score,
    decision_ok,
    llm_analysis,
)


def process_single_transaction(state: FraudState) -> FraudState:
    """Initialise le traitement d'une transaction unique.
    
    Prend la première transaction de la liste et la marque comme en cours de traitement.
    
    Args:
        state: État avec transaction_ids
        
    Returns:
        État avec current_transaction_id défini
    """
    transaction_ids = state.get("transaction_ids", [])
    
    if not transaction_ids:
        return {
            **state,
            "current_transaction_id": None,
        }
    
    # Prendre la première transaction de la liste
    current_id = transaction_ids[0]
    
    return {
        **state,
        "current_transaction_id": current_id,
    }


def get_next_transaction(state: FraudState) -> FraudState:
    """Passe à la transaction suivante dans la liste.
    
    Args:
        state: État actuel
        
    Returns:
        État avec current_transaction_id mis à jour ou None si terminé
    """
    transaction_ids = state.get("transaction_ids", [])
    current_id = state.get("current_transaction_id")
    
    if not transaction_ids or not current_id:
        return {
            **state,
            "current_transaction_id": None,
        }
    
    # Trouver l'index de la transaction actuelle
    try:
        current_index = transaction_ids.index(current_id)
        # Prendre la transaction suivante
        if current_index + 1 < len(transaction_ids):
            next_id = transaction_ids[current_index + 1]
            return {
                **state,
                "current_transaction_id": next_id,
            }
    except ValueError:
        pass
    
    # Plus de transactions à traiter
    return {
        **state,
        "current_transaction_id": None,
    }


def should_continue_loop(state: FraudState) -> str:
    """Détermine si on doit continuer la boucle ou terminer.
    
    Args:
        state: État actuel
        
    Returns:
        "continue" si d'autres transactions à traiter, "end" sinon
    """
    current_id = state.get("current_transaction_id")
    
    if current_id:
        return "continue"
    return "end"


def create_fraud_detection_graph():
    """Crée et compile le graphe LangGraph pour la détection de fraude.
    
    Architecture parallèle avec boucle:
    1. fetch_all_transaction_ids: Récupère tous les IDs de transactions
    2. process_single_transaction: Initialise le traitement d'une transaction
    3. fetch_all_data: Récupère toutes les données agrégées
    4. analyze_amount_merchant, analyze_country_travel, analyze_sms_email: Pré-scoring parallèle
    5. aggregate_features_and_score: Agrégation et calcul du score
    6. save_result_to_json: Sauvegarde du résultat (seulement si score > 0.5)
    7. route_on_score: Route conditionnel (score <= 0.5 → decision_ok, sinon → llm_analysis)
    8. decision_ok/llm_analysis: Décision finale
    9. get_next_transaction: Passe à la transaction suivante (boucle)
    
    Returns:
        Graph LangGraph compilé
    """
    # Création du graphe
    graph = StateGraph(FraudState)
    
    # Node d'initialisation (récupère tous les IDs)
    graph.add_node("fetch_all_transaction_ids", fetch_all_transaction_ids)
    
    # Node de traitement d'une transaction
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
    
    # Node pour passer à la transaction suivante
    graph.add_node("get_next_transaction", get_next_transaction)
    
    # Point d'entrée
    graph.set_entry_point("fetch_all_transaction_ids")
    
    # Après récupération des IDs, traiter la première transaction
    graph.add_edge("fetch_all_transaction_ids", "process_single_transaction")
    
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
    
    # Décision puis sauvegarde (LLM désactivé)
    graph.add_edge("aggregate_features_and_score", "decision_ok")
    graph.add_edge("decision_ok", "save_result_to_json")
    
    # Après sauvegarde, passer à la transaction suivante
    graph.add_edge("save_result_to_json", "get_next_transaction")
    
    # Boucle conditionnelle : continuer ou terminer
    graph.add_conditional_edges(
        "get_next_transaction",
        should_continue_loop,
        {
            "continue": "process_single_transaction",
            "end": END,
        }
    )
    
    # Compilation
    app = graph.compile()
    
    return app
