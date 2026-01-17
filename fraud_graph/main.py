"""Script principal pour lancer l'analyse LangGraph de toutes les transactions."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from fraud_graph.agent import create_fraud_detection_graph
from fraud_graph.state import FraudState
from fraud_graph.nodes import (
    fetch_all_data,
    analyze_amount_merchant,
    analyze_country_travel,
    analyze_sms_email,
    merge_prescoring_results,
    aggregate_features_and_score,
    decision_ok,
)
from fraud_graph.nodes.aggregation import save_fraud_result_async


async def process_single_transaction_async(transaction_id: str) -> Dict[str, Any]:
    """Traite une transaction individuelle de manière asynchrone.
    
    Exécute tout le pipeline de détection de fraude pour une transaction.
    
    Args:
        transaction_id: UUID de la transaction à analyser
        
    Returns:
        Résultat de l'analyse (None si pas de fraude, dict si fraude)
    """
    # État initial pour cette transaction
    state: FraudState = {
        "transaction_ids": [transaction_id],
        "current_transaction_id": transaction_id,
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
    
    try:
        # 1. Récupération des données
        state = await fetch_all_data(state)
        
        if not state.get("transaction"):
            return None
        
        # 2. Pré-scoring en parallèle
        amount_features = analyze_amount_merchant(state)
        country_features = analyze_country_travel(state)
        sms_email_features = analyze_sms_email(state)
        
        # 3. Merge des résultats
        state = {
            **state,
            **amount_features,
            **country_features,
            **sms_email_features,
        }
        state = merge_prescoring_results(state)
        
        # 4. Agrégation et calcul du score
        state = aggregate_features_and_score(state)
        
        # 5. Décision
        state = decision_ok(state)
        
        # 6. Sauvegarde (seulement si score > 0.25 - seuil ajusté pour être plus sélectif)
        risk_score = state.get("risk_score", 0.0)
        if risk_score > 0.25:
            result_dict = {
                "transaction_id": transaction_id,
                "timestamp": datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
                "risk_score": risk_score,
                "decision": state.get("decision", "FRAUDULENT"),
                "features": state.get("aggregated_features", {}),
                "explanation": state.get("explanation"),
            }
            await save_fraud_result_async(result_dict, transaction_id)
            return {
                "transaction_id": transaction_id,
                "risk_score": risk_score,
                "decision": state.get("decision"),
                "features": state.get("aggregated_features", {}),
                "explanation": state.get("explanation"),
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur lors du traitement de {transaction_id}: {e}")
        return None


async def analyze_all_transactions() -> Dict[str, Any]:
    """Analyse toutes les transactions en parallèle de manière asynchrone.
    
    Récupère tous les IDs de transactions, puis les traite tous en parallèle
    avec asyncio.gather() pour maximiser les performances.
    
    Returns:
        Dictionnaire avec les statistiques et résultats
    """
    from Agent.helpers.http_client import make_api_request
    
    print("🚀 Initialisation de l'analyse parallèle...")
    
    # Récupération de tous les IDs
    print("📥 Récupération de tous les IDs de transactions...")
    try:
        endpoint = "/transactions/ids"
        data = await make_api_request("GET", endpoint, response_format="json")
        transaction_ids = data.get("transaction_ids", [])
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des IDs: {e}")
        return {"error": str(e)}
    
    if not transaction_ids:
        print("⚠️  Aucune transaction trouvée")
        return {"transaction_ids": [], "frauds": []}
    
    print(f"📊 {len(transaction_ids)} transactions à analyser")
    print("🔄 Traitement en parallèle en cours...")
    print("-" * 60)
    
    # Traitement de toutes les transactions en parallèle
    results = await asyncio.gather(
        *[process_single_transaction_async(tx_id) for tx_id in transaction_ids],
        return_exceptions=True
    )
    
    # Filtrer les résultats (garder seulement les fraudes)
    frauds = [r for r in results if r is not None and not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]
    
    if errors:
        print(f"⚠️  {len(errors)} erreurs rencontrées")
    
    print(f"\n✅ Analyse terminée: {len(frauds)} fraudes détectées sur {len(transaction_ids)} transactions")
    
    return {
        "transaction_ids": transaction_ids,
        "total_transactions": len(transaction_ids),
        "frauds": frauds,
        "frauds_count": len(frauds),
        "errors": len(errors),
    }


async def analyze_single_transaction(transaction_id: str) -> FraudState:
    """Analyse une transaction spécifique avec le graphe LangGraph.
    
    Args:
        transaction_id: UUID de la transaction à analyser
        
    Returns:
        État final avec décision et explication
    """
    print(f"🚀 Initialisation du graphe LangGraph...")
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
    
    print(f"🔍 Analyse de la transaction: {transaction_id}")
    print("-" * 60)
    
    # Exécution du graphe
    result = await app.ainvoke(initial_state)
    
    return result


async def main():
    """Point d'entrée principal."""
    import os
    
    # Vérifier que l'API est accessible
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                print("⚠️  L'API ne répond pas correctement")
                print("💡 Lancez l'API avec: just api-dev")
                sys.exit(1)
    except Exception as e:
        print("⚠️  Impossible de se connecter à l'API (http://localhost:8000)")
        print("💡 Lancez l'API avec: just api-dev")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Analyse d'une transaction spécifique
        transaction_id = sys.argv[1]
        result = await analyze_single_transaction(transaction_id)
        
        print(f"\n📊 Résultat:")
        print(f"  Score de risque: {result.get('risk_score', 0.0)}")
        print(f"  Décision: {result.get('decision', 'UNKNOWN')}")
        print(f"  Explication: {result.get('explanation', 'N/A')}")
        
        if result.get('llm_result'):
            print(f"\n🤖 Analyse LLM:")
            print(f"  {result['llm_result']}")
    else:
        # Analyse de toutes les transactions (en parallèle)
        result = await analyze_all_transactions()
        
        if "error" in result:
            print(f"❌ Erreur: {result['error']}")
            sys.exit(1)
        
        print(f"\n📊 Résultats:")
        print(f"  Transactions analysées: {result.get('total_transactions', 0)}")
        print(f"  Fraudes détectées: {result.get('frauds_count', 0)}")
        
        if result.get('frauds'):
            print(f"\n🚨 Transactions frauduleuses détectées:")
            for fraud in result['frauds']:
                print(f"  - {fraud.get('transaction_id')}: Score {fraud.get('risk_score', 0.0)}")
        
        # Afficher le chemin des résultats sauvegardés
        results_file = Path("fraud_graph/results/fraud.json")
        if results_file.exists():
            print(f"\n💾 Résultats sauvegardés dans: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
