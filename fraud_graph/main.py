import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from fraud_graph.graph import create_fraud_detection_graph
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
from fraud_graph.nodes.agent_batch import analyze_frauds_with_agent
from fraud_graph.nodes.aggregate_frauds import aggregate_confirmed_frauds


async def process_single_transaction_async(transaction_id: str) -> Dict[str, Any]:
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
        state = await fetch_all_data(state)
        
        if not state.get("transaction"):
            return None
        
        amount_features = analyze_amount_merchant(state)
        country_features = analyze_country_travel(state)
        sms_email_features = analyze_sms_email(state)
        
        state = {
            **state,
            **amount_features,
            **country_features,
            **sms_email_features,
        }
        state = merge_prescoring_results(state)
        
        state = aggregate_features_and_score(state)
        
        state = decision_ok(state)
        
        risk_score = state.get("risk_score", 0.0)
        if risk_score > 0.25:
            result_dict = {
                "transaction_id": transaction_id,
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
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
    from Agent.helpers.http_client import make_api_request
    
    print("🚀 Initialisation de l'analyse parallèle...")
    
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
    
    results = await asyncio.gather(
        *[process_single_transaction_async(tx_id) for tx_id in transaction_ids],
        return_exceptions=True
    )
    
    frauds = [r for r in results if r is not None and not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]
    
    if errors:
        print(f"⚠️  {len(errors)} erreurs rencontrées")
    
    print(f"\n✅ Analyse terminée: {len(frauds)} fraudes détectées sur {len(transaction_ids)} transactions")
    
    print(f"\n{'='*70}")
    print("🤖 ANALYSE AVEC L'AGENT LLM")
    print(f"{'='*70}") 
    print("📥 Analyse des transactions de fraud.json par batch de 50 (asynchrone) avec l'agent...")
    
    agent_state: FraudState = {
        "transaction_ids": [],
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
        "agent_analysis_results": None,
        "real_frauds": None,
    }
    
    agent_state = await analyze_frauds_with_agent(agent_state)
    
    agent_state = aggregate_confirmed_frauds(agent_state)
    
    agent_results = agent_state.get("agent_analysis_results", {})
    real_frauds = agent_state.get("real_frauds", {})
    
    if agent_results:
        frauds_confirmed = agent_results.get("frauds_detected", [])
        print(f"\n✅ Analyse agent terminée: {len(frauds_confirmed)} fraudes confirmées")
    
    if real_frauds:
        confirmed_count = real_frauds.get("total_confirmed_frauds", 0)
        print(f"💾 {confirmed_count} fraudes avérées sauvegardées dans real_fraud.json")
    
    return {
        "transaction_ids": transaction_ids,
        "total_transactions": len(transaction_ids),
        "frauds": frauds,
        "frauds_count": len(frauds),
        "errors": len(errors),
        "agent_analysis": agent_results,
    }


async def analyze_single_transaction(transaction_id: str) -> FraudState:
    print(f"🚀 Initialisation du graphe LangGraph...")
    app = create_fraud_detection_graph()
    
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
    
    result = await app.ainvoke(initial_state)
    
    return result


async def main():
    import os
    
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
        
        results_file = Path("fraud_graph/results/fraud.json")
        if results_file.exists():
            print(f"\n💾 Résultats sauvegardés dans: {results_file}")
        
        if result.get('agent_analysis'):
            agent_results = result['agent_analysis']
            frauds_confirmed = agent_results.get('frauds_detected', [])
            print(f"\n🤖 Analyse agent:")
            print(f"  Fraudes confirmées: {len(frauds_confirmed)}")
            if frauds_confirmed:
                print(f"\n🚨 Fraudes confirmées par l'agent:")
                for fraud in frauds_confirmed[:10]:
                    print(f"  - {fraud.get('transaction_id')}: {fraud.get('reason', 'N/A')}")
                if len(frauds_confirmed) > 10:
                    print(f"  ... et {len(frauds_confirmed) - 10} autres")
            
            agent_file = Path("fraud_graph/results/agent_analysis.json")
            if agent_file.exists():
                print(f"  💾 Résultats agent sauvegardés dans: {agent_file}")
        
        real_fraud_file = Path("fraud_graph/results/real_fraud.json")
        if real_fraud_file.exists():
            with open(real_fraud_file, 'r', encoding='utf-8') as f:
                real_frauds_data = json.load(f)
            confirmed_count = real_frauds_data.get('total_confirmed_frauds', 0)
            print(f"\n🎯 Fraudes avérées (real_fraud.json): {confirmed_count}")
            print(f"  💾 Fichier: {real_fraud_file}")


if __name__ == "__main__":
    asyncio.run(main())
