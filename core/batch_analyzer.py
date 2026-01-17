import os
import json
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List
from google.adk.runners import Runner
from google.genai import types

from helpers.analysis_state import AnalysisState
from helpers.config import SAVE_INTERVAL, PROJECT_ROOT
from helpers.token_estimator import estimate_tokens
from helpers.event_processor import process_event
from helpers.json_parser import parse_json_response
from helpers.display import format_progress_line

# Configuration des retries
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY_BASE = float(os.getenv('RETRY_DELAY_BASE', '2.0'))  # Délai de base en secondes

async def analyze_batch_with_agent(
    runner: Runner,
    transactions: List[Dict[str, Any]],
    batch_num: int,
    batch_start_idx: int,
    state: AnalysisState,
    semaphore: asyncio.Semaphore,
    user_id: str = "analyst",
) -> List[Dict[str, Any]]:
    
    transaction_ids = [t.get("transaction_id", "unknown") for t in transactions]
    batch_start_time = datetime.now()
    
    async with semaphore:
        print(f"\n{'='*70}", flush=True)
        print(f"🔄 [Batch {batch_num}] Début analyse de {len(transactions)} transactions...", flush=True)
        print(f"{'='*70}", flush=True)
        
        session = runner.session_service.create_session(
            app_name='transaction_fraud_analysis',
            user_id=user_id
        )
        
        import json
        transaction_ids_json = json.dumps(transaction_ids)
        
        # Utiliser uniquement le prompt système, pas de prompt utilisateur personnalisé
        prompt = f"""Analyze {len(transactions)} transactions.

STEP 1: Call get_transaction_aggregated('{transaction_ids_json}') ONCE.
STEP 2: Analyze all transactions from the returned data.
STEP 3: Follow the output format specified in your instructions.

CRITICAL: Only ONE tool call to get_transaction_aggregated. Use the batch endpoint."""
        
        system_prompt = ""
        if hasattr(runner, 'agent') and hasattr(runner.agent, 'instruction'):
            system_prompt = runner.agent.instruction
        
        system_prompt_tokens = estimate_tokens(system_prompt)
        user_prompt_tokens = estimate_tokens(prompt)
        estimated_prompt_total = system_prompt_tokens + user_prompt_tokens
        
        print(f"📝 Prompt tokens (estimé):", flush=True)
        print(f"   - System prompt: {system_prompt_tokens:,} tokens ({len(system_prompt):,} chars)", flush=True)
        print(f"   - User prompt: {user_prompt_tokens:,} tokens ({len(prompt):,} chars)", flush=True)
        print(f"   - Total prompt: {estimated_prompt_total:,} tokens", flush=True)
        
        try:
            response_text = ""
            tool_calls_count = 0
            tool_call_details = []
            token_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            
            prompt_text = prompt
            
            user_message = types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
            
            print(f"🚀 Envoi de la requête à l'agent...", flush=True)
            print(f"   📋 Session ID: {session.id[:8] if len(session.id) > 8 else session.id}...", flush=True)
            print(f"   👤 User ID: {user_id}", flush=True)
            
            event_count = 0
            last_log_time = datetime.now()
            start_wait_time = datetime.now()
            heartbeat_task = None
            
            async def heartbeat():
                while True:
                    await asyncio.sleep(5)
                    elapsed = (datetime.now() - start_wait_time).total_seconds()
                    if event_count == 0:
                        print(f"   💓 En attente d'événements... ({elapsed:.0f}s écoulées, {event_count} événements reçus)", flush=True)
                    else:
                        print(f"   💓 En cours... ({elapsed:.0f}s écoulées, {event_count} événements reçus)", flush=True)
            
            async def process_events():
                nonlocal event_count, last_log_time, response_text, token_usage, tool_calls_count
                
                print(f"   🔄 Démarrage de la boucle d'événements...", flush=True)
                
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session.id,
                    new_message=user_message
                ):
                    event_count += 1
                    event_type = type(event).__name__
                    current_time = datetime.now()
                    
                    if event_count == 1:
                        elapsed = (current_time - start_wait_time).total_seconds()
                        print(f"   ✅ Premier événement reçu après {elapsed:.1f}s: {event_type}", flush=True)
                    
                    if (current_time - last_log_time).total_seconds() > 10:
                        elapsed = (current_time - start_wait_time).total_seconds()
                        print(f"   ⏳ Événement #{event_count}: {event_type} (temps écoulé: {elapsed:.1f}s)", flush=True)
                        last_log_time = current_time
                    
                    if 'ToolCall' in event_type or 'tool_call' in event_type.lower():
                        tool_calls_count += 1
                        tool_name = getattr(event, 'function_name', getattr(event, 'name', 'unknown'))
                        tool_call_details.append({
                            "call_num": tool_calls_count,
                            "name": tool_name,
                            "timestamp": datetime.now().isoformat()
                        })
                        elapsed = (datetime.now() - start_wait_time).total_seconds()
                        print(f"   🔧 Tool call #{tool_calls_count}: {tool_name} (après {elapsed:.1f}s)", flush=True)
                    
                    if 'Content' in event_type or 'content' in event_type.lower() or 'Text' in event_type or 'Delta' in event_type:
                        text_preview = ""
                        if hasattr(event, 'text'):
                            text_preview = event.text[:100] if event.text else ""
                        elif hasattr(event, 'content'):
                            if hasattr(event.content, 'text'):
                                text_preview = event.content.text[:100] if event.content.text else ""
                        if text_preview:
                            print(f"   📝 Contenu reçu ({len(text_preview)} chars): {text_preview}...", flush=True)
                    
                    response_text, token_usage, tool_calls_count = process_event(
                        event, response_text, token_usage, tool_calls_count, batch_num
                    )
                
                print(f"   ✅ Tous les événements reçus (total: {event_count})", flush=True)
            
            def is_retryable_error(error: Exception) -> bool:
                """Détermine si une erreur est retryable (503, rate limit, timeout temporaire)."""
                error_msg = str(error).lower()
                error_type = type(error).__name__
                
                # Service Unavailable (503)
                if "service unavailable" in error_msg or "503" in error_msg:
                    return True
                
                # Rate limit (429)
                if "rate limit" in error_msg or "429" in error_msg:
                    return True
                
                # Timeout (peut être temporaire)
                if "timeout" in error_msg and "ServiceUnavailableError" in error_type:
                    return True
                
                # Erreurs réseau temporaires
                if "connection" in error_msg or "network" in error_msg:
                    return True
                
                return False
            
            def extract_retry_delay(error: Exception) -> float:
                """Extrait le délai de retry suggéré depuis l'erreur."""
                error_msg = str(error)
                
                # Chercher "retry_after_seconds" dans le message d'erreur
                if "retry_after_seconds" in error_msg:
                    try:
                        match = re.search(r'"retry_after_seconds":\s*(\d+)', error_msg)
                        if match:
                            return float(match.group(1))
                    except:
                        pass
                
                return RETRY_DELAY_BASE
            
            # Logique de retry avec backoff exponentiel
            last_error = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    heartbeat_task = asyncio.create_task(heartbeat())
                    await asyncio.wait_for(process_events(), timeout=700.0)
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    # Succès - sortir de la boucle de retry
                    break
                    
                except asyncio.TimeoutError:
                    if heartbeat_task:
                        heartbeat_task.cancel()
                    elapsed = (datetime.now() - start_wait_time).total_seconds()
                    print(f"   ⏱️  Timeout après {elapsed:.1f}s: {event_count} événements reçus", flush=True)
                    if attempt < MAX_RETRIES:
                        retry_delay = RETRY_DELAY_BASE * (2 ** attempt)
                        print(f"   🔄 Retry {attempt + 1}/{MAX_RETRIES} dans {retry_delay:.1f}s...", flush=True)
                        await asyncio.sleep(retry_delay)
                        # Réinitialiser pour le retry
                        event_count = 0
                        response_text = ""
                        start_wait_time = datetime.now()
                        continue
                    raise
                    
                except ValueError as e:
                    # Erreur de fonction non trouvée - Mistral peut générer des noms de fonction invalides
                    if "is not found in the tools_dict" in str(e):
                        if heartbeat_task:
                            heartbeat_task.cancel()
                        elapsed = (datetime.now() - start_wait_time).total_seconds()
                        print(f"   ⚠️  Erreur de fonction invalide après {elapsed:.1f}s: {str(e)[:100]}", flush=True)
                        print(f"   💡 Mistral a tenté d'appeler une fonction invalide. Continuons avec la réponse actuelle...", flush=True)
                        # Ne pas lever l'exception, continuer avec la réponse actuelle
                        break
                    else:
                        raise
                        
                except Exception as e:
                    last_error = e
                    if heartbeat_task:
                        heartbeat_task.cancel()
                    elapsed = (datetime.now() - start_wait_time).total_seconds()
                    
                    # Vérifier si l'erreur est retryable
                    if is_retryable_error(e) and attempt < MAX_RETRIES:
                        retry_delay = extract_retry_delay(e)
                        # Backoff exponentiel avec jitter
                        actual_delay = retry_delay * (2 ** attempt) + (asyncio.get_event_loop().time() % 1)
                        print(f"   ⚠️  Erreur retryable après {elapsed:.1f}s ({event_count} événements): {type(e).__name__}", flush=True)
                        print(f"   🔄 Retry {attempt + 1}/{MAX_RETRIES} dans {actual_delay:.1f}s...", flush=True)
                        await asyncio.sleep(actual_delay)
                        # Réinitialiser pour le retry
                        event_count = 0
                        response_text = ""
                        start_wait_time = datetime.now()
                        continue
                    else:
                        # Erreur non retryable ou nombre max de retries atteint
                        print(f"   ❌ Erreur après {elapsed:.1f}s ({event_count} événements): {type(e).__name__}: {str(e)[:200]}", flush=True)
                        if attempt >= MAX_RETRIES:
                            print(f"   ⛔ Nombre maximum de retries ({MAX_RETRIES}) atteint", flush=True)
                        import traceback
                        print(f"   📋 Traceback:", flush=True)
                        traceback.print_exc()
                        raise
            
            # Nettoyer la réponse (enlever markdown si présent)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                # Enlever les blocs de code markdown
                lines = response_text.split('\n')
                response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])
                response_text = response_text.strip()
            
            batch_end_time = datetime.now()
            batch_duration = (batch_end_time - batch_start_time).total_seconds()
            
            print(f"\n📊 Résultats de l'analyse:", flush=True)
            print(f"   - Tool calls: {tool_calls_count}", flush=True)
            if tool_call_details:
                for detail in tool_call_details:
                    print(f"     • {detail['name']} (call #{detail['call_num']})", flush=True)
            
            if token_usage["total_tokens"] == 0:
                estimated_prompt = estimate_tokens(prompt_text)
                estimated_completion = estimate_tokens(response_text)
                estimated_tools = tool_calls_count * 100
                
                token_usage["prompt_tokens"] = estimated_prompt + estimated_tools
                token_usage["completion_tokens"] = estimated_completion
                token_usage["total_tokens"] = token_usage["prompt_tokens"] + token_usage["completion_tokens"]
                token_usage["estimated"] = True
                print(f"   ⚠️  Tokens estimés (API n'a pas retourné les tokens)", flush=True)
            else:
                token_usage["estimated"] = False
                print(f"   ✅ Tokens depuis l'API", flush=True)
            
            print(f"   📤 Prompt tokens: {token_usage['prompt_tokens']:,}", flush=True)
            print(f"   📥 Completion tokens: {token_usage['completion_tokens']:,}", flush=True)
            print(f"   📊 Total tokens: {token_usage['total_tokens']:,}", flush=True)
            print(f"   💰 Coût estimé (gpt-5-mini): ${token_usage['total_tokens'] * 0.0000001:.4f}", flush=True)
            print(f"   ⏱️  Durée: {batch_duration:.2f}s", flush=True)
            print(f"   📏 Réponse length: {len(response_text):,} caractères", flush=True)
            print(f"   📈 Tokens/transaction: {token_usage['total_tokens'] // len(transactions):,}", flush=True)
            
            # Parser le format texte : uuid | [reasons]
            frauds_detected = []
            if response_text:
                for line in response_text.split('\n'):
                    line = line.strip()
                    if not line or '|' not in line:
                        continue
                    
                    # Séparer par pipe, en gérant les espaces
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        transaction_id = parts[0].strip()
                        reasons_str = parts[1].strip()
                        
                        # Extraire les raisons (format: [reason1, reason2, ...])
                        reasons = []
                        reasons_str = reasons_str.strip()
                        if reasons_str.startswith('[') and reasons_str.endswith(']'):
                            reasons_str = reasons_str[1:-1].strip()
                            if reasons_str:
                                reasons = [r.strip() for r in reasons_str.split(',') if r.strip()]
                        
                        # Si on a un transaction_id et des raisons, c'est une fraude détectée
                        if transaction_id and reasons:
                            frauds_detected.append({
                                "transaction_id": transaction_id,
                                "risk_level": "critical",
                                "risk_score": 100,  # Par défaut, toutes les fraudes détectées sont critical
                                "reason": "; ".join(reasons) if reasons else "Fraud detected",
                                "anomalies": reasons if reasons else ["Fraud detected"]
                            })
            
            print(f"   🔍 Fraudes détectées (high/critical): {len(frauds_detected)}/{len(transactions)}", flush=True)
            
            # Créer les résultats pour toutes les transactions
            results = []
            frauds_by_id = {f["transaction_id"]: f for f in frauds_detected}
            
            for i, transaction in enumerate(transactions):
                transaction_id = transaction.get("transaction_id", "unknown")
                transaction_num = batch_start_idx + i + 1
                
                if transaction_id in frauds_by_id:
                    # Transaction identifiée comme fraude
                    fraud_data = frauds_by_id[transaction_id]
                    result = {
                        "transaction_id": transaction_id,
                        "risk_level": fraud_data["risk_level"],
                        "risk_score": fraud_data["risk_score"],
                        "reason": fraud_data["reason"],
                        "anomalies": fraud_data["anomalies"],
                        "token_usage": {
                            "prompt_tokens": token_usage["prompt_tokens"] // len(transactions),
                            "completion_tokens": token_usage["completion_tokens"] // len(transactions),
                            "total_tokens": token_usage["total_tokens"] // len(transactions),
                            "estimated": token_usage.get("estimated", False)
                        }
                    }
                    print(format_progress_line(transaction_num, result, result["token_usage"], 
                                             len([r for r in results if r.get("risk_level") in ["high", "critical"]]), 
                                             state.total_transactions, state.start_time))
                else:
                    # Transaction non frauduleuse (low)
                    result = {
                        "transaction_id": transaction_id,
                        "risk_level": "low",
                        "risk_score": 0,
                        "reason": "No anomalies detected - transaction appears normal",
                        "anomalies": [],
                        "token_usage": {
                            "prompt_tokens": token_usage["prompt_tokens"] // len(transactions),
                            "completion_tokens": token_usage["completion_tokens"] // len(transactions),
                            "total_tokens": token_usage["total_tokens"] // len(transactions),
                            "estimated": token_usage.get("estimated", False)
                        }
                    }
                
                completed = state.add_result(result)
                results.append(result)
            
            # Le fichier texte est mis à jour automatiquement par AnalysisState
            if completed % SAVE_INTERVAL == 0:
                frauds_count = len([r for r in state.get_results() if r.get("risk_level") in ["high", "critical"]])
                print(f"💾 Progression: {completed} résultats ({frauds_count} fraudes détectées)")
            
            print(f"\n✅ [Batch {batch_num}] Analyse terminée: {len(results)} résultats en {batch_duration:.2f}s", flush=True)
            print(f"{'='*70}\n", flush=True)
            
            return results
            
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            results = []
            error_details = f"Parsing error: {str(e)}"
            if hasattr(e, 'pos'):
                error_details += f" at position {e.pos}"
            if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                error_details += f" (line {e.lineno}, column {e.colno})"
            
            # Sauvegarder un aperçu de la réponse problématique pour debug
            if os.getenv('DEBUG_ERRORS') == '1':
                error_file = PROJECT_ROOT / "scripts" / "results" / f"json_error_batch_{batch_num}.txt"
                error_file.parent.mkdir(parents=True, exist_ok=True)
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"Batch {batch_num} - JSON Error\n")
                    f.write(f"Error: {error_details}\n")
                    f.write(f"\nResponse text ({len(response_text)} chars):\n")
                    f.write("="*70 + "\n")
                    f.write(response_text)
                    f.write("\n" + "="*70 + "\n")
                print(f"   💾 Réponse problématique sauvegardée dans: {error_file.name}", flush=True)
            
            for transaction in transactions:
                transaction_id = transaction.get("transaction_id", "unknown")
                result = {
                    "transaction_id": transaction_id,
                    "risk_level": "error",
                    "risk_score": -1,
                    "reason": error_details,
                    "anomalies": [],
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated": False}
                }
                completed = state.add_result(result)
                results.append(result)
            print(f"❌ [Batch {batch_num}] Erreur parsing: {error_details[:100]}... | Progress: {completed}/{state.total_transactions}", flush=True)
            return results
            
        except Exception as e:
            results = []
            error_msg = str(e)
            error_type = type(e).__name__
            
            if len(error_msg) > 200:
                error_msg_short = error_msg[:200] + "..."
            else:
                error_msg_short = error_msg
            
            if "LiteLLM" in error_msg or "litellm" in error_msg.lower():
                error_summary = f"API/LiteLLM error: {error_type}"
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                error_summary = f"Timeout error: {error_type}"
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                error_summary = f"Rate limit error: {error_type}"
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                error_summary = f"Network error: {error_type}"
            else:
                error_summary = f"{error_type}: {error_msg_short}"
            
            for transaction in transactions:
                transaction_id = transaction.get("transaction_id", "unknown")
                result = {
                    "transaction_id": transaction_id,
                    "risk_level": "error",
                    "risk_score": -1,
                    "reason": f"Analysis error: {error_summary}",
                    "anomalies": [f"Error type: {error_type}"],
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated": False}
                }
                completed = state.add_result(result)
                results.append(result)
            
            print(f"❌ [Batch {batch_num}] Erreur analyse: {error_summary} | Progress: {completed}/{state.total_transactions}")
            
            if os.getenv('DEBUG_ERRORS') == '1':
                import traceback
                print(f"   Détails complets de l'erreur:")
                print(f"   {error_type}: {error_msg}")
                traceback.print_exc()
            
            return results
