"""Exemple d'utilisation du graphe LangGraph pour la détection de fraude."""

import asyncio
from langgraph.agent import create_fraud_detection_graph
from langgraph.state import FraudState


async def analyze_transaction(transaction_id: str) -> FraudState:
    """Analyse une transaction avec le graphe LangGraph.
    
    Args:
        transaction_id: UUID de la transaction à analyser
        
    Returns:
        État final avec décision et explication
    """
    # Création du graphe
    app = create_fraud_detection_graph()
    
    # État initial
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
    # Exemple de transaction ID (à remplacer par un ID réel)
    transaction_id = "550e8400-e29b-41d4-a716-446655440000"
    
    print(f"🔍 Analyse de la transaction: {transaction_id}")
    print("-" * 60)
    
    result = await analyze_transaction(transaction_id)
    
    print(f"\n📊 Résultat:")
    print(f"  Score de risque: {result.get('risk_score', 0.0)}")
    print(f"  Décision: {result.get('decision', 'UNKNOWN')}")
    print(f"  Explication: {result.get('explanation', 'N/A')}")
    
    if result.get('llm_result'):
        print(f"\n🤖 Analyse LLM:")
        print(f"  {result['llm_result']}")


if __name__ == "__main__":
    asyncio.run(main())
