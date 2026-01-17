import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from google.adk.runners import Runner
from google.genai import types

from helpers.analysis_state import AnalysisState
from helpers.config import SAVE_INTERVAL
from helpers.token_estimator import estimate_tokens
from helpers.event_processor import process_event
from helpers.json_parser import parse_json_response
from helpers.display import format_progress_line

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
        prompt = f"""Analyze {len(transactions)} transactions. Return JSON object with "results" array.

STEP 1: Call get_transaction_aggregated('{transaction_ids_json}') ONCE.
STEP 2: Analyze all transactions from the returned data.
STEP 3: Return JSON object: {{"results": [{{"transaction_id": "id", "risk_level": "low|medium|high|critical", "risk_score": 0-100, "reason": "...", "anomalies": []}}, ...]}}

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
            
            try:
                heartbeat_task = asyncio.create_task(heartbeat())
                await asyncio.wait_for(process_events(), timeout=700.0)
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            except asyncio.TimeoutError:
                if heartbeat_task:
                    heartbeat_task.cancel()
                elapsed = (datetime.now() - start_wait_time).total_seconds()
                print(f"   ⏱️  Timeout après {elapsed:.1f}s: {event_count} événements reçus", flush=True)
                raise
            except Exception as e:
                if heartbeat_task:
                    heartbeat_task.cancel()
                elapsed = (datetime.now() - start_wait_time).total_seconds()
                print(f"   ❌ Erreur après {elapsed:.1f}s ({event_count} événements): {type(e).__name__}: {str(e)[:200]}", flush=True)
                import traceback
                print(f"   📋 Traceback:", flush=True)
                traceback.print_exc()
                raise
            
            response_text = parse_json_response(response_text)
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
            
            batch_results = json.loads(response_text)
            
            if isinstance(batch_results, dict) and "results" in batch_results:
                batch_results = batch_results["results"]
            
            if not isinstance(batch_results, list):
                batch_results = [batch_results]
            
            results = []
            results_by_id = {r.get("transaction_id"): r for r in batch_results if isinstance(r, dict) and "transaction_id" in r}
            
            for i, transaction in enumerate(transactions):
                transaction_id = transaction.get("transaction_id", "unknown")
                transaction_num = batch_start_idx + i + 1
                
                if transaction_id in results_by_id:
                    risk_analysis = results_by_id[transaction_id]
                elif i < len(batch_results) and isinstance(batch_results[i], dict):
                    risk_analysis = batch_results[i]
                else:
                    risk_analysis = {"risk_level": "error", "risk_score": -1, "reason": "Transaction not found in response", "anomalies": []}
                
                if "transaction_id" not in risk_analysis:
                    risk_analysis["transaction_id"] = transaction_id
                
                result = {
                    "transaction_id": transaction_id,
                    "risk_level": risk_analysis.get("risk_level", "unknown"),
                    "risk_score": risk_analysis.get("risk_score", 0),
                    "reason": risk_analysis.get("reason", ""),
                    "anomalies": risk_analysis.get("anomalies", []),
                    "token_usage": {
                        "prompt_tokens": token_usage["prompt_tokens"] // len(transactions),
                        "completion_tokens": token_usage["completion_tokens"] // len(transactions),
                        "total_tokens": token_usage["total_tokens"] // len(transactions),
                        "estimated": token_usage.get("estimated", False)
                    }
                }
                
                completed = state.add_result(result)
                print(format_progress_line(transaction_num, result, result["token_usage"], completed, 
                                         state.total_transactions, state.start_time))
                
                results.append(result)
            
            if completed % SAVE_INTERVAL == 0:
                state.save_results()
                print(f"💾 Sauvegarde intermédiaire: {completed} résultats")
            
            print(f"\n✅ [Batch {batch_num}] Analyse terminée: {len(results)} résultats en {batch_duration:.2f}s", flush=True)
            print(f"{'='*70}\n", flush=True)
            
            return results
            
        except json.JSONDecodeError as e:
            results = []
            for transaction in transactions:
                transaction_id = transaction.get("transaction_id", "unknown")
                result = {
                    "transaction_id": transaction_id,
                    "risk_level": "error",
                    "risk_score": -1,
                    "reason": f"JSON parsing error: {str(e)}",
                    "anomalies": [],
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated": False}
                }
                completed = state.add_result(result)
                results.append(result)
            print(f"❌ [Batch {batch_num}] Erreur JSON: {str(e)[:100]}... | Progress: {completed}/{state.total_transactions}")
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
