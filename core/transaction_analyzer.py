import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from google.adk.runners import Runner
from google.genai import types

from helpers.analysis_state import AnalysisState
from helpers.config import SAVE_INTERVAL
from helpers.token_estimator import estimate_tokens
from helpers.event_processor import process_event
from helpers.json_parser import parse_json_response
from helpers.display import format_progress_line

async def analyze_transaction_with_agent(
    runner: Runner,
    transaction: Dict[str, Any],
    transaction_num: int,
    state: AnalysisState,
    prompt_template: str,
    semaphore: asyncio.Semaphore,
    user_id: str = "analyst",
) -> Dict[str, Any]:
    transaction_id = transaction.get("transaction_id", "unknown")

    async with semaphore:
        print(f"🔄 [{transaction_num:3d}] Début analyse: {transaction_id[:8]}...", flush=True)

        session = runner.session_service.create_session(
            app_name='transaction_fraud_analysis',
            user_id=user_id
        )

        prompt = f"Transaction ID: {transaction_id}"

        try:
            response_text = ""
            tool_calls_count = 0
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

            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_message
            ):
                response_text, token_usage, tool_calls_count = process_event(
                    event, response_text, token_usage, tool_calls_count, transaction_num
                )

            response_text = parse_json_response(response_text)

            if token_usage["total_tokens"] == 0:
                estimated_prompt = estimate_tokens(prompt_text)
                estimated_completion = estimate_tokens(response_text)
                estimated_tools = tool_calls_count * 100

                token_usage["prompt_tokens"] = estimated_prompt + estimated_tools
                token_usage["completion_tokens"] = estimated_completion
                token_usage["total_tokens"] = token_usage["prompt_tokens"] + token_usage["completion_tokens"]
                token_usage["estimated"] = True
            else:
                token_usage["estimated"] = False

            risk_analysis = json.loads(response_text)

            result = {
                "transaction_id": transaction_id,
                "risk_level": risk_analysis.get("risk_level", "unknown"),
                "risk_score": risk_analysis.get("risk_score", 0),
                "reason": risk_analysis.get("reason", ""),
                "anomalies": risk_analysis.get("anomalies", []),
                "token_usage": token_usage
            }

            completed = state.add_result(result)

            print(format_progress_line(transaction_num, result, token_usage, completed, 
                                     state.total_transactions, state.start_time))

            if completed % SAVE_INTERVAL == 0:
                state.save_results()
                print(f"💾 Sauvegarde intermédiaire: {completed} résultats")

            return result

        except json.JSONDecodeError as e:
            result = {
                "transaction_id": transaction_id,
                "risk_level": "error",
                "risk_score": -1,
                "reason": f"JSON parsing error: {str(e)}",
                "anomalies": [],
                "token_usage": token_usage
            }
            completed = state.add_result(result)
            print(f"❌ [{transaction_num:3d}] Erreur JSON: {transaction_id[:8]}... | Progress: {completed}/{state.total_transactions}")
            return result

        except Exception as e:
            if 'token_usage' not in locals():
                token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

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

            result = {
                "transaction_id": transaction_id,
                "risk_level": "error",
                "risk_score": -1,
                "reason": f"Analysis error: {error_summary}",
                "anomalies": [f"Error type: {error_type}"],
                "token_usage": token_usage
            }
            completed = state.add_result(result)

            print(f"❌ [{transaction_num:3d}] Erreur analyse: {transaction_id[:8]}... | {error_summary} | Progress: {completed}/{state.total_transactions}")

            if os.getenv('DEBUG_ERRORS') == '1':
                import traceback
                print(f"   Détails complets de l'erreur:")
                print(f"   {error_type}: {error_msg}")
                traceback.print_exc()

            return result