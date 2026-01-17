#!/usr/bin/env python3
"""Script pour exécuter l'agent LangGraph sur une transaction unique."""

import sys
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le chemin parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from fraud_graph.Agent import create_fraud_agent, LangGraphRunner

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Réduire le bruit
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.ERROR)


async def run_agent_on_transaction(transaction_id: str):
    """Exécute l'agent sur une transaction unique.
    
    Args:
        transaction_id: UUID de la transaction à analyser
    """
    print(f"🔄 Création de l'agent LangGraph...")
    agent = create_fraud_agent()
    
    print(f"✅ Agent créé")
    print(f"📊 Analyse de la transaction: {transaction_id}")
    print(f"{'='*60}")
    
    # Créer le runner
    runner = LangGraphRunner(agent)
    
    # Créer une session
    session = runner.session_service.create_session(
        app_name='transaction_fraud_analysis',
        user_id='fraud_analyst'
    )
    
    # Préparer le message
    user_prompt = f"""Analyze transaction {transaction_id}.

STEP 1: Call get_transaction_aggregated_batch('["{transaction_id}"]') to get transaction data.
STEP 2: Analyze the transaction thoroughly using all available tools if needed.
STEP 3: If the transaction is FRAUDULENT, you MUST call the report_fraud tool (not just mention it in text):
   - Use the report_fraud tool with transaction_id and reasons
   - transaction_id: The UUID of the fraudulent transaction
   - reasons: A comma-separated list of fraud indicators (e.g., "new_dest,amount_anomaly,time_correlation")

CRITICAL RULES:
- Use tools to gather evidence before making decisions
- If fraud is detected, you MUST call the report_fraud tool (execute it, don't just write about it)
- Call report_fraud() ONLY if you determine the transaction is fraudulent
- If no fraud detected, do NOT call report_fraud()"""
    
    # Créer un message compatible
    user_message = type('Content', (), {
        'parts': [type('Part', (), {'text': user_prompt})()],
        'text': user_prompt
    })()
    
    # Variables pour suivre l'exécution
    response_text = ''
    tool_calls = []
    fraud_detected = False
    
    print(f"\n🚀 Exécution de l'agent...\n")
    
    try:
        async for event in runner.run_async(
            user_id='fraud_analyst',
            session_id=session.id,
            new_message=user_message
        ):
            event_type = getattr(event, 'type', type(event).__name__)
            
            # Détecter les tool calls
            if 'tool_call' in event_type.lower() or hasattr(event, 'function_name'):
                tool_name = getattr(event, 'function_name', getattr(event, 'name', getattr(event, 'function', None)))
                if tool_name:
                    print(f"🔧 Tool call: {tool_name}")
                    tool_calls.append(tool_name)
                    
                    if tool_name == 'report_fraud':
                        fraud_detected = True
                        args = {}
                        if hasattr(event, 'args'):
                            args = event.args
                        elif hasattr(event, 'arguments'):
                            if isinstance(event.arguments, dict):
                                args = event.arguments
                            elif isinstance(event.arguments, str):
                                try:
                                    args = json.loads(event.arguments)
                                except:
                                    pass
                        
                        if isinstance(args, dict):
                            transaction_id_arg = args.get('transaction_id', '')
                            reasons = args.get('reasons', '')
                            print(f"🚨 FRAUDE DÉTECTÉE!")
                            print(f"   Transaction ID: {transaction_id_arg}")
                            print(f"   Raisons: {reasons}")
            
            # Extraire le texte de réponse
            if hasattr(event, 'text'):
                response_text += event.text
            elif hasattr(event, 'content'):
                if hasattr(event.content, 'text'):
                    response_text += event.content.text
                elif hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text'):
                            response_text += part.text
        
        print(f"\n{'='*60}")
        print(f"✅ Analyse terminée")
        print(f"\n📊 Résumé:")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Tool calls: {len(tool_calls)} ({', '.join(tool_calls) if tool_calls else 'aucun'})")
        print(f"   Fraude détectée: {'OUI' if fraud_detected else 'NON'}")
        
        if response_text:
            print(f"\n📝 Réponse de l'agent (derniers 500 caractères):")
            print(response_text[-500:])
        
        return {
            'transaction_id': transaction_id,
            'fraud_detected': fraud_detected,
            'tool_calls': tool_calls,
            'response_text': response_text
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}", exc_info=True)
        print(f"\n❌ Erreur: {e}")
        raise


def main():
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print("Usage: python fraud_graph/run_agent.py <transaction_id>")
        print("\nExemple:")
        print("  python fraud_graph/run_agent.py eea21a8b-6d1c-47ae-b6c4-313603e561cd")
        sys.exit(1)
    
    transaction_id = sys.argv[1]
    
    # Valider le format UUID
    if len(transaction_id) != 36 or transaction_id.count('-') != 4:
        print(f"❌ Erreur: Format UUID invalide: {transaction_id}")
        print("   Format attendu: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)
    
    try:
        result = asyncio.run(run_agent_on_transaction(transaction_id))
        
        # Sauvegarder le résultat
        output_file = Path(__file__).parent / 'results' / f'agent_single_{transaction_id[:8]}.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'result': result
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultat sauvegardé dans: {output_file}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
