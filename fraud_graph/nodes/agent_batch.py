import json
import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from google.adk.runners import Runner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurer le logging pour réduire le bruit de LiteLLM
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
os.environ.setdefault("LITELLM_TURN_OFF_MESSAGE_LOGGING", "true")

# Configurer le logger pour afficher les logs
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

from ..state import FraudState
from core.runner_setup import setup_runner
from fraud_graph.Agent.runner_langgraph import LangGraphRunner
from .save_real_fraud import save_fraud_to_real_fraud_json


async def load_fraud_transaction_ids() -> List[str]:
    fraud_file = Path('fraud_graph/results/fraud.json')
    if not fraud_file.exists():
        return []
    
    with open(fraud_file, 'r', encoding='utf-8') as f:
        frauds = json.load(f)
    
    if not isinstance(frauds, list):
        frauds = [frauds]
    
    transaction_ids = [
        item.get('transaction_id')
        for item in frauds
        if isinstance(item, dict) and item.get('transaction_id')
    ]
    
    return transaction_ids


async def analyze_single_transaction_with_agent(
    runner,
    transaction_id: str,
    transaction_num: int,
    total_transactions: int
) -> Dict[str, Any]:
    """Analyse une transaction individuelle avec l'agent."""
    from google.genai import types
    
    session = runner.session_service.create_session(
        app_name='transaction_fraud_analysis',
        user_id='fraud_analyst'
    )
    
    system_prompt = load_system_prompt()
    
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
    
    prompt = f"""{system_prompt}

---

{user_prompt}"""
    
    user_message = types.Content(
        role='user',
        parts=[types.Part(text=prompt)]
    )
    
    fraud_reports = []
    tool_calls_count = 0
    response_text = ''
    token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    
    try:
        logger.info(f"🔄 Analyse transaction {transaction_num}/{total_transactions}: {transaction_id}")
        
        async for event in runner.run_async(
            user_id='fraud_analyst',
            session_id=session.id,
            new_message=user_message
        ):
            event_type = type(event).__name__
            
            if 'ToolCall' in event_type or 'tool_call' in event_type.lower():
                tool_name = getattr(event, 'function_name', getattr(event, 'name', getattr(event, 'function', None)))
                tool_calls_count += 1
                
                if tool_name == 'report_fraud':
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
                        reasons_str = args.get('reasons', '')
                        if transaction_id_arg:
                            fraud_reports.append({
                                'transaction_id': transaction_id_arg,
                                'reasons': reasons_str
                            })
                            logger.info(f"🚨 Fraude détectée: {transaction_id_arg} - {reasons_str}")
        
        frauds_detected = []
        for report in fraud_reports:
            transaction_id_arg = report['transaction_id']
            reasons_str = report['reasons']
            reasons = [r.strip() for r in reasons_str.split(',') if r.strip()] if reasons_str else []
            
            frauds_detected.append({
                'transaction_id': transaction_id_arg,
                'risk_level': 'critical',
                'risk_score': 100,
                'reason': '; '.join(reasons) if reasons else 'Fraud detected',
                'anomalies': reasons if reasons else ['Fraud detected']
            })
        
        return {
            'transaction_id': transaction_id,
            'frauds_detected': frauds_detected,
            'token_usage': token_usage,
            'tool_calls_count': tool_calls_count
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur pour transaction {transaction_id}: {e}", exc_info=True)
        return {
            'transaction_id': transaction_id,
            'frauds_detected': [],
            'error': str(e),
            'error_type': type(e).__name__,
            'token_usage': token_usage
        }


def load_system_prompt() -> str:
    """Charge le prompt système."""
    from fraud_graph.Agent.agent_langgraph import load_system_prompt as load_agent_system_prompt
    return load_agent_system_prompt()


async def analyze_frauds_with_agent(state: FraudState) -> FraudState:
    transaction_ids = await load_fraud_transaction_ids()
    
    if not transaction_ids:
        print('⚠️  Aucune transaction dans fraud.json')
        return state
    
    print(f'📥 {len(transaction_ids)} transactions à analyser avec l\'agent')
    print(f'🔄 Traitement asynchrone en parallèle (toutes les transactions simultanément)')
    
    runner = setup_runner()
    
    all_frauds = []
    total_tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    errors = []
    completed_count = 0
    frauds_count = 0
    start_time = datetime.now()
    status_lock = asyncio.Lock()
    
    def update_progress_bar(completed: int, total: int, frauds: int, errors_count: int):
        """Affiche une barre de progression."""
        percentage = (completed / total * 100) if total > 0 else 0
        bar_length = 50
        filled = int(bar_length * completed / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        if completed > 0:
            avg_time = elapsed / completed
            remaining = (total - completed) * avg_time
            eta_str = f"ETA: {remaining:.0f}s"
        else:
            eta_str = "ETA: --"
        
        status = f"\r📊 [{bar}] {completed}/{total} ({percentage:.1f}%) | 🚨 {frauds} fraudes | ❌ {errors_count} erreurs | {eta_str}"
        print(status, end='', flush=True)
    
    async def process_transaction_with_status(idx: int, transaction_id: str):
        """Traite une transaction et met à jour le statut."""
        nonlocal completed_count, all_frauds, total_tokens, errors, frauds_count
        
        try:
            logger.info(f"🔄 [{idx:4d}/{len(transaction_ids)}] Démarrage: {transaction_id[:8]}...")
            
            result = await analyze_single_transaction_with_agent(
                runner,
                transaction_id,
                idx,
                len(transaction_ids)
            )
            
            async with status_lock:
                completed_count += 1
                
                if 'error' in result:
                    errors.append({
                        'transaction_id': transaction_id,
                        'error': result.get('error'),
                        'error_type': result.get('error_type')
                    })
                    logger.error(f"❌ [{idx:4d}/{len(transaction_ids)}] {transaction_id[:8]}... - Erreur: {result.get('error', 'Unknown')[:100]}")
                else:
                    frauds = result.get('frauds_detected', [])
                    if frauds:
                        all_frauds.extend(frauds)
                        frauds_count += len(frauds)
                        await save_fraud_to_real_fraud_json(frauds)
                        logger.info(f"✅ [{idx:4d}/{len(transaction_ids)}] {transaction_id[:8]}... - {len(frauds)} fraude(s) détectée(s)")
                    else:
                        logger.info(f"⚪ [{idx:4d}/{len(transaction_ids)}] {transaction_id[:8]}... - Aucune fraude")
                    
                    tokens = result.get('token_usage', {})
                    total_tokens['prompt_tokens'] += tokens.get('prompt_tokens', 0)
                    total_tokens['completion_tokens'] += tokens.get('completion_tokens', 0)
                    total_tokens['total_tokens'] += tokens.get('total_tokens', 0)
                
                # Mettre à jour la barre de progression
                update_progress_bar(completed_count, len(transaction_ids), frauds_count, len(errors))
                
                return result
        except Exception as e:
            async with status_lock:
                completed_count += 1
                error_entry = {
                    'transaction_id': transaction_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                errors.append(error_entry)
                logger.error(f"❌ [{idx:4d}/{len(transaction_ids)}] {transaction_id[:8]}... - Exception: {type(e).__name__}: {str(e)[:100]}")
                update_progress_bar(completed_count, len(transaction_ids), frauds_count, len(errors))
            return {'transaction_id': transaction_id, 'error': str(e), 'error_type': type(e).__name__}
    
    # Créer toutes les tâches asynchrones
    print(f'\n🚀 Lancement de {len(transaction_ids)} transactions en parallèle...')
    print(f'⏱️  Démarrage: {start_time.strftime("%H:%M:%S")}')
    print(f'📊 Barre de progression:\n')
    
    tasks = [
        process_transaction_with_status(idx, transaction_id)
        for idx, transaction_id in enumerate(transaction_ids, 1)
    ]
    
    # Exécuter toutes les tâches en parallèle
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Nouvelle ligne après la barre de progression
    print()
    
    # Traiter les résultats qui n'ont pas été traités dans process_transaction_with_status
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception non gérée: {type(result).__name__}: {str(result)[:500]}", exc_info=result)
    
    # Afficher le résumé final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f'\n{"="*70}')
    print(f'📊 RÉSUMÉ FINAL')
    print(f'{"="*70}')
    print(f'✅ Transactions analysées: {len(transaction_ids)}')
    print(f'🚨 Fraudes détectées: {len(all_frauds)}')
    print(f'❌ Erreurs: {len(errors)}')
    print(f'⏱️  Durée totale: {duration:.1f}s ({duration/60:.1f} min)')
    print(f'⚡ Vitesse moyenne: {len(transaction_ids)/duration:.1f} transactions/s')
    print(f'📊 Tokens utilisés: {total_tokens.get("total_tokens", 0):,}')
    
    if errors:
        print(f'\n❌ Détails des erreurs ({len(errors)}):')
        for err in errors[:10]:
            print(f'   - {err["transaction_id"][:8]}...: {err.get("error_type", "Unknown")} - {err.get("error", "Unknown")[:80]}')
        if len(errors) > 10:
            print(f'   ... et {len(errors) - 10} autres erreurs')
    
    output_file = Path('fraud_graph/results/agent_analysis.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'total_transactions': len(transaction_ids),
        'processing_mode': 'async_parallel',  # Indique que c'est un traitement asynchrone en parallèle
        'frauds_detected': all_frauds,
        'token_usage': total_tokens,
        'errors': errors
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    print(f'\n💾 Résultats sauvegardés dans: {output_file}')
    print(f'🚨 {len(all_frauds)} fraudes confirmées par l\'agent sur {len(transaction_ids)} transactions analysées')
    
    return {
        **state,
        'agent_analysis_results': results_data
    }
