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

logger = logging.getLogger(__name__)

from ..state import FraudState
from core.runner_setup import setup_runner
from .llm_batch import analyze_batch_with_agent_sync
from .save_real_fraud import save_fraud_to_real_fraud_json

BATCH_SIZE = 5


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


async def analyze_frauds_with_agent(state: FraudState) -> FraudState:
    transaction_ids = await load_fraud_transaction_ids()
    
    if not transaction_ids:
        print('⚠️  Aucune transaction dans fraud.json')
        return state
    
    print(f'📥 {len(transaction_ids)} transactions à analyser avec l\'agent')
    
    runner = setup_runner()
    user_id = 'fraud_analyst'
    
    total_batches = (len(transaction_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f'🔄 Traitement par batch de {BATCH_SIZE} transactions ({total_batches} batches)')
    
    batch_tasks = []
    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(transaction_ids))
        batch_ids = transaction_ids[batch_start:batch_end]
        
        # Use sync version - tools are now synchronous, so Google ADK Agent can execute them properly
        # Wrap in async function to run in thread pool
        async def run_batch_sync(bn, bid):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                analyze_batch_with_agent_sync,
                runner,
                bid,
                bn,
                user_id
            )
        
        task = run_batch_sync(batch_num, batch_ids)
        batch_tasks.append(task)
    
    print(f'🚀 Lancement de {total_batches} batches en parallèle...')
    
    completed_batches = 0
    batch_status = {i: {'status': 'pending', 'start_time': None, 'frauds': 0, 'error': None} for i in range(total_batches)}
    status_lock = asyncio.Lock()
    
    async def update_status(batch_num: int, status: str, frauds: int = 0, error: str = None):
        async with status_lock:
            batch_status[batch_num]['status'] = status
            if status == 'running' and batch_status[batch_num]['start_time'] is None:
                batch_status[batch_num]['start_time'] = datetime.now()
            if frauds > 0:
                batch_status[batch_num]['frauds'] = frauds
            if error:
                batch_status[batch_num]['error'] = error
    
    async def print_status_summary():
        while True:
            await asyncio.sleep(3)
            async with status_lock:
                running = sum(1 for s in batch_status.values() if s['status'] == 'running')
                completed = sum(1 for s in batch_status.values() if s['status'] == 'completed')
                errors = sum(1 for s in batch_status.values() if s['status'] == 'error')
                pending = total_batches - completed - errors - running
                
                if completed_batches >= total_batches:
                    break
                
                if running > 0 or pending > 0:
                    running_batches = [i for i, s in batch_status.items() if s['status'] == 'running']
                    running_summary = []
                    for batch_num in running_batches[:5]:
                        status = batch_status[batch_num]
                        elapsed = (datetime.now() - status['start_time']).total_seconds() if status['start_time'] else 0
                        running_summary.append(f"#{batch_num + 1}({elapsed:.0f}s)")
                    
                    summary = f'📊 {completed}/{total_batches} terminés'
                    if running > 0:
                        summary += f' | 🔄 {running} en cours'
                        if running_summary:
                            summary += f' [{", ".join(running_summary)}]'
                    if pending > 0:
                        summary += f' | ⏳ {pending} en attente'
                    if errors > 0:
                        summary += f' | ❌ {errors} erreurs'
                    
                    print(f'\r{summary}', end='', flush=True)
    
    status_task = asyncio.create_task(print_status_summary())
    
    async def process_batch_with_save(batch_num: int, task) -> Dict[str, Any]:
        nonlocal completed_batches
        try:
            await update_status(batch_num, 'running')
            result = await task
            
            if isinstance(result, Exception):
                error_msg = str(result)
                await update_status(batch_num, 'error', error=error_msg[:100])
                async with status_lock:
                    completed_batches += 1
                
                logger.error(
                    f"❌ Batch {batch_num + 1}/{total_batches} - Exception: {type(result).__name__}\n"
                    f"   Message: {error_msg[:500]}",
                    exc_info=result if hasattr(result, '__traceback__') else None
                )
                print(f'\n❌ Batch {batch_num + 1}/{total_batches}: {type(result).__name__}: {error_msg[:200]}')
                return {'error': error_msg, 'error_type': type(result).__name__, 'batch_num': batch_num + 1}
            else:
                # Vérifier si le résultat contient une erreur
                if isinstance(result, dict) and 'error' in result:
                    error_msg = result.get('error', 'Unknown error')
                    error_type = result.get('error_type', 'Unknown')
                    await update_status(batch_num, 'error', error=error_msg[:100])
                    async with status_lock:
                        completed_batches += 1
                    
                    logger.error(
                        f"❌ Batch {batch_num + 1}/{total_batches} - Erreur dans le résultat:\n"
                        f"   Type: {error_type}\n"
                        f"   Message: {error_msg[:500]}\n"
                        f"   Transaction IDs: {result.get('transaction_ids', [])}"
                    )
                    print(f'\n❌ Batch {batch_num + 1}/{total_batches}: {error_type}: {error_msg[:200]}')
                    return result
                
                frauds = result.get('frauds_detected', [])
                if frauds:
                    await save_fraud_to_real_fraud_json(frauds)
                
                await update_status(batch_num, 'completed', frauds=len(frauds))
                async with status_lock:
                    completed_batches += 1
                
                logger.info(f"✅ Batch {batch_num + 1}/{total_batches}: {len(frauds)} fraudes détectées")
                print(f'\n✅ Batch {batch_num + 1}/{total_batches}: {len(frauds)} fraudes détectées')
                return result
        except Exception as e:
            error_msg = str(e)
            await update_status(batch_num, 'error', error=error_msg[:100])
            async with status_lock:
                completed_batches += 1
            
            logger.error(
                f"❌ Erreur dans process_batch_with_save (batch {batch_num + 1}):\n"
                f"   Type: {type(e).__name__}\n"
                f"   Message: {error_msg[:500]}",
                exc_info=True
            )
            print(f'\n❌ Erreur dans le batch {batch_num + 1}: {type(e).__name__}: {error_msg[:200]}')
            return {'error': error_msg, 'error_type': type(e).__name__, 'batch_num': batch_num + 1}
    
    batch_results = await asyncio.gather(
        *[process_batch_with_save(batch_num, task) for batch_num, task in enumerate(batch_tasks)],
        return_exceptions=True
    )
    
    status_task.cancel()
    try:
        await status_task
    except asyncio.CancelledError:
        pass
    
    print()  # Nouvelle ligne après le résumé
    
    all_frauds = []
    total_tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    error_summary = []
    
    for result in batch_results:
        if isinstance(result, Exception):
            error_summary.append({
                'batch_num': 'unknown',
                'error_type': type(result).__name__,
                'error': str(result)[:200]
            })
            logger.error(f"Exception dans batch_results: {type(result).__name__}: {str(result)[:500]}", exc_info=result)
            continue
        elif isinstance(result, dict) and 'error' in result:
            batch_num = result.get('batch_num', 'unknown')
            error_type = result.get('error_type', 'Unknown')
            error_msg = result.get('error', 'Unknown error')
            error_summary.append({
                'batch_num': batch_num,
                'error_type': error_type,
                'error': error_msg[:200],
                'transaction_ids': result.get('transaction_ids', [])
            })
            logger.warning(f"Batch {batch_num} en erreur: {error_type} - {error_msg[:200]}")
            continue
        else:
            frauds = result.get('frauds_detected', [])
            all_frauds.extend(frauds)
            tokens = result.get('token_usage', {})
            total_tokens['prompt_tokens'] += tokens.get('prompt_tokens', 0)
            total_tokens['completion_tokens'] += tokens.get('completion_tokens', 0)
            total_tokens['total_tokens'] += tokens.get('total_tokens', 0)
    
    # Afficher le résumé des erreurs
    if error_summary:
        print(f'\n⚠️  RÉSUMÉ DES ERREURS ({len(error_summary)} batches en erreur):')
        for err in error_summary[:10]:  # Limiter à 10 pour ne pas surcharger
            print(f"   Batch {err['batch_num']}: {err['error_type']} - {err['error'][:150]}")
        if len(error_summary) > 10:
            print(f"   ... et {len(error_summary) - 10} autres erreurs")
        
        logger.warning(
            f"⚠️  {len(error_summary)} batches en erreur sur {total_batches}:\n" +
            "\n".join([f"   Batch {e['batch_num']}: {e['error_type']} - {e['error'][:200]}" for e in error_summary])
        )
    
    output_file = Path('fraud_graph/results/agent_analysis.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'total_transactions': len(transaction_ids),
        'total_batches': total_batches,
        'frauds_detected': all_frauds,
        'token_usage': total_tokens,
        'batch_results': batch_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    print(f'💾 Résultats sauvegardés dans: {output_file}')
    print(f'🚨 {len(all_frauds)} fraudes confirmées par l\'agent sur {len(transaction_ids)} transactions analysées')
    
    return {
        **state,
        'agent_analysis_results': results_data
    }
