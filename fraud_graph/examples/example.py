"""Exemple d'utilisation du graphe LangGraph pour la détection de fraude."""

import asyncio
from fraud_graph.agent import create_fraud_detection_graph
from fraud_graph.state import FraudState


async def analyze_all_transactions() -> FraudState:
    """Analyse toutes les transactions avec le graphe LangGraph.
    
    Le graphe récupère automatiquement tous les IDs de transactions via l'API,
    puis boucle sur chaque transaction pour l'analyser.
    
    Returns:
        État final avec tous les résultats
    """
    # Création du graphe
    app = create_fraud_detection_graph()
    
    # État initial (vide - le graphe récupère les IDs automatiquement)
    initial_state: FraudState = {
        "transaction_ids": [],  # Sera rempli par fetch_all_transaction_ids
        "current_transaction_id": None,
        "transaction": None,
        "user_profile": None,
        "sms_data": None,
        "email_data": None,
        "location_data": None,
        "amount_merchant_features": None,
        "country_travel_features": None,
        "sms_email_features": None,
        "aggregated_features": None,
        "risk_score": 0.0,
        "decision": None,
        "llm_result": None,
        "explanation": None,
        "results": [],
    }
    
    # Exécution du graphe (traite toutes les transactions automatiquement)
    result = await app.ainvoke(initial_state)
    
    return result


async def analyze_single_transaction(transaction_id: str) -> FraudState:
    """Analyse une transaction spécifique avec le graphe LangGraph.
    
    Args:
        transaction_id: UUID de la transaction à analyser
        
    Returns:
        État final avec décision et explication
    """
    # Création du graphe
    app = create_fraud_detection_graph()
    
    # État initial avec une seule transaction
    initial_state: FraudState = {
        "transaction_ids": [transaction_id],
        "current_transaction_id": None,
        "transaction": None,
        "user_profile": None,
        "sms_data": None,
        "email_data": None,
        "location_data": None,
        "amount_merchant_features": None,
        "country_travel_features": None,
        "sms_email_features": None,
        "aggregated_features": None,
        "risk_score": 0.0,
        "decision": None,
        "llm_result": None,
        "explanation": None,
        "results": [],
    }
    
    # Exécution du graphe
    result = await app.ainvoke(initial_state)
    
    return result


async def main():
    """Exemple d'utilisation."""
    import sys
    
    if len(sys.argv) > 1:
        # Analyse d'une transaction spécifique
        transaction_id = sys.argv[1]
        print(f"🔍 Analyse de la transaction: {transaction_id}")
        print("-" * 60)
        
        result = await analyze_single_transaction(transaction_id)
        
        print(f"\n📊 Résultat:")
        print(f"  Score de risque: {result.get('risk_score', 0.0)}")
        print(f"  Décision: {result.get('decision', 'UNKNOWN')}")
        print(f"  Explication: {result.get('explanation', 'N/A')}")
        
        if result.get('llm_result'):
            print(f"\n🤖 Analyse LLM:")
            print(f"  {result['llm_result']}")
    else:
        # Analyse de toutes les transactions
        print("🔍 Analyse de toutes les transactions...")
        print("-" * 60)
        
        result = await analyze_all_transactions()
        
        print(f"\n📊 Résultats:")
        print(f"  Transactions analysées: {len(result.get('transaction_ids', []))}")
        print(f"  Fraudes détectées: {len(result.get('results', []))}")
        
        if result.get('results'):
            print(f"\n🚨 Transactions frauduleuses détectées:")
            for fraud in result['results']:
                print(f"  - {fraud.get('transaction_id')}: Score {fraud.get('risk_score', 0.0)}")


if __name__ == "__main__":
    asyncio.run(main())
