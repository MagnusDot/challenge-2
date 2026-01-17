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
    transaction_ids = state.get("transaction_ids", [])
    current_id = state.get("current_transaction_id")
    
    if not transaction_ids:
        return {
            **state,
            "current_transaction_id": None,
        }
    
    if not current_id:
        current_id = transaction_ids[0]
        print(f"🔄 Début du traitement de la transaction: {current_id} (1/{len(transaction_ids)})")
    else:
        try:
            index = transaction_ids.index(current_id) + 1
            print(f"🔄 Traitement de la transaction: {current_id} ({index}/{len(transaction_ids)})")
        except ValueError:
            print(f"🔄 Traitement de la transaction: {current_id}")
    
    return {
        **state,
        "current_transaction_id": current_id,
    }


def get_next_transaction(state: FraudState) -> FraudState:
    transaction_ids = state.get("transaction_ids", [])
    current_id = state.get("current_transaction_id")
    
    if not transaction_ids or not current_id:
        return {
            **state,
            "current_transaction_id": None,
        }
    
    try:
        current_index = transaction_ids.index(current_id)
        if current_index + 1 < len(transaction_ids):
            next_id = transaction_ids[current_index + 1]
            print(f"➡️  Passage à la transaction suivante: {next_id} (index {current_index + 1}/{len(transaction_ids)})")
            return {
                **state,
                "current_transaction_id": next_id,
            }
        else:
            print(f"✅ Toutes les transactions ont été traitées ({len(transaction_ids)} transactions)")
    except ValueError:
        print(f"⚠️  Transaction {current_id} non trouvée dans la liste")
    
    return {
        **state,
        "current_transaction_id": None,
    }


def should_continue_loop(state: FraudState) -> str:
    current_id = state.get("current_transaction_id")
    
    if current_id:
        return "continue"
    return "end"


def create_fraud_detection_graph():
    graph = StateGraph(FraudState)
    
    graph.add_node("fetch_all_transaction_ids", fetch_all_transaction_ids)
    
    graph.add_node("process_single_transaction", process_single_transaction)
    
    graph.add_node("fetch_all_data", fetch_all_data)
    
    graph.add_node("analyze_amount_merchant", analyze_amount_merchant)
    graph.add_node("analyze_country_travel", analyze_country_travel)
    graph.add_node("analyze_sms_email", analyze_sms_email)
    
    graph.add_node("merge_prescoring_results", merge_prescoring_results)
    
    graph.add_node("aggregate_features_and_score", aggregate_features_and_score)
    graph.add_node("save_result_to_json", save_result_to_json)
    
    graph.add_node("decision_ok", decision_ok)
    graph.add_node("llm_analysis", llm_analysis)
    
    graph.add_node("get_next_transaction", get_next_transaction)
    
    graph.set_entry_point("fetch_all_transaction_ids")
    
    graph.add_edge("fetch_all_transaction_ids", "process_single_transaction")
    
    graph.add_edge("process_single_transaction", "fetch_all_data")
    
    graph.add_edge("fetch_all_data", "analyze_amount_merchant")
    graph.add_edge("fetch_all_data", "analyze_country_travel")
    graph.add_edge("fetch_all_data", "analyze_sms_email")
    
    graph.add_edge("analyze_amount_merchant", "merge_prescoring_results")
    graph.add_edge("analyze_country_travel", "merge_prescoring_results")
    graph.add_edge("analyze_sms_email", "merge_prescoring_results")
    
    graph.add_edge("merge_prescoring_results", "aggregate_features_and_score")
    
    graph.add_edge("aggregate_features_and_score", "decision_ok")
    graph.add_edge("decision_ok", "save_result_to_json")
    
    graph.add_edge("save_result_to_json", "get_next_transaction")
    
    graph.add_conditional_edges(
        "get_next_transaction",
        should_continue_loop,
        {
            "continue": "process_single_transaction",
            "end": END,
        }
    )
    
    app = graph.compile()
    
    return app
