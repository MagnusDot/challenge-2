"""Exemple d'utilisation de l'agent LangGraph."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fraud_graph.Agent.agent_langgraph import create_fraud_agent, run_agent_async
from fraud_graph.Agent.runner_langgraph import analyze_batch_with_langgraph_agent


async def example_single_transaction():
    """Exemple d'analyse d'une seule transaction."""
    print("🔄 Création de l'agent...")
    agent = create_fraud_agent()
    
    transaction_id = "abc-123-def-456"
    message = f"""Analyze transaction {transaction_id}.

STEP 1: Call get_transaction_aggregated_batch('["{transaction_id}"]') to get transaction data.
STEP 2: Analyze the transaction.
STEP 3: If fraudulent, call report_fraud(transaction_id, reasons)."""
    
    print(f"📤 Envoi du message: {message[:100]}...")
    
    result = await run_agent_async(agent, message)
    
    print(f"✅ Résultat: {json.dumps(result, indent=2)}")


async def example_batch():
    """Exemple d'analyse d'un batch de transactions."""
    print("🔄 Création de l'agent...")
    agent = create_fraud_agent()
    
    transaction_ids = [
        "abc-123-def-456",
        "def-456-ghi-789",
        "ghi-789-jkl-012",
    ]
    
    print(f"📤 Analyse de {len(transaction_ids)} transactions...")
    
    result = analyze_batch_with_langgraph_agent(
        agent,
        transaction_ids,
        batch_num=1,
        user_id='fraud_analyst'
    )
    
    print(f"✅ Résultat:")
    print(f"   - Fraudes détectées: {len(result['frauds_detected'])}")
    print(f"   - Durée: {result['duration']:.2f}s")
    print(f"   - Tool calls: {result.get('tool_calls_count', 0)}")
    
    if result['frauds_detected']:
        print(f"\n🚨 Fraudes détectées:")
        for fraud in result['frauds_detected']:
            print(f"   - {fraud['transaction_id']}: {fraud['reason']}")


if __name__ == "__main__":
    print("=== Exemple 1: Transaction unique ===\n")
    asyncio.run(example_single_transaction())
    
    print("\n\n=== Exemple 2: Batch de transactions ===\n")
    asyncio.run(example_batch())
