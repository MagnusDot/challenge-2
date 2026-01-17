import json
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from google.adk.runners import Runner
from google.genai import types

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..state import FraudState
from core.runner_setup import setup_runner
from helpers.event_processor import process_event
from helpers.token_estimator import estimate_tokens

BATCH_SIZE = 5
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY_BASE = float(os.getenv('RETRY_DELAY_BASE', '2.0'))


def load_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent.parent / 'Agent' / 'system_prompt.md'
    if not prompt_path.exists():
        raise FileNotFoundError(f'System prompt file not found: {prompt_path}')
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


async def analyze_batch_with_agent_async(
    runner: Runner,
    transaction_ids: List[str],
    batch_num: int,
    user_id: str = 'fraud_analyst'
) -> Dict[str, Any]:
    batch_start_time = datetime.now()
    
    session = runner.session_service.create_session(
        app_name='transaction_fraud_analysis',
        user_id=user_id
    )
    
    transaction_ids_json = json.dumps(transaction_ids)
    
    system_prompt = load_system_prompt()
    
    user_prompt = f"""Analyze {len(transaction_ids)} transactions.

STEP 1: Call get_transaction_aggregated_batch('{transaction_ids_json}') ONCE to get all transaction data.
STEP 2: Analyze all transactions from the returned data.
STEP 3: For each transaction you identify as FRAUDULENT, call report_fraud(transaction_id, reasons) with:
   - transaction_id: The UUID of the fraudulent transaction
   - reasons: A comma-separated list of fraud indicators (e.g., "account_drained,time_correlation,new_merchant")

CRITICAL RULES:
- Only ONE tool call to get_transaction_aggregated_batch. Use the batch endpoint.
- Call report_fraud() for EACH fraudulent transaction you find (you can call it multiple times)
- If no frauds detected, do NOT call report_fraud() at all
- Do NOT output text - use the report_fraud tool instead"""
    
    prompt = f"""{system_prompt}

---

{user_prompt}"""
    
    user_message = types.Content(
        role='user',
        parts=[types.Part(text=prompt)]
    )
    
    response_text = ''
    tool_calls_count = 0
    fraud_reports = []
    token_usage = {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0
    }
    
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=user_message
        ):
            event_type = type(event).__name__
            
            if 'ToolCall' in event_type or 'tool_call' in event_type.lower():
                tool_name = getattr(event, 'function_name', getattr(event, 'name', getattr(event, 'function', None)))
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
                    elif hasattr(event, 'function_call'):
                        func_call = event.function_call
                        if hasattr(func_call, 'args'):
                            args = func_call.args
                        elif hasattr(func_call, 'arguments'):
                            if isinstance(func_call.arguments, dict):
                                args = func_call.arguments
                            elif isinstance(func_call.arguments, str):
                                try:
                                    args = json.loads(func_call.arguments)
                                except:
                                    pass
                    
                    if isinstance(args, dict):
                        transaction_id = args.get('transaction_id', '')
                        reasons_str = args.get('reasons', '')
                        if transaction_id:
                            fraud_reports.append({
                                'transaction_id': transaction_id,
                                'reasons': reasons_str
                            })
            
            response_text, token_usage, tool_calls_count = process_event(
                event, response_text, token_usage, tool_calls_count, batch_num
            )
        
        response_text = response_text.strip()
        
        if token_usage['total_tokens'] == 0:
            estimated_prompt = estimate_tokens(user_prompt)
            estimated_completion = estimate_tokens(response_text)
            estimated_tools = tool_calls_count * 100
            
            token_usage['prompt_tokens'] = estimated_prompt + estimated_tools
            token_usage['completion_tokens'] = estimated_completion
            token_usage['total_tokens'] = token_usage['prompt_tokens'] + token_usage['completion_tokens']
            token_usage['estimated'] = True
        else:
            token_usage['estimated'] = False
        
        frauds_detected = []
        
        for report in fraud_reports:
            transaction_id = report['transaction_id']
            reasons_str = report['reasons']
            
            reasons = []
            if reasons_str:
                reasons = [r.strip() for r in reasons_str.split(',') if r.strip()]
            
            if transaction_id:
                frauds_detected.append({
                    'transaction_id': transaction_id,
                    'risk_level': 'critical',
                    'risk_score': 100,
                    'reason': '; '.join(reasons) if reasons else 'Fraud detected',
                    'anomalies': reasons if reasons else ['Fraud detected']
                })
        
        batch_end_time = datetime.now()
        batch_duration = (batch_end_time - batch_start_time).total_seconds()
        
        return {
            'batch_num': batch_num,
            'transaction_ids': transaction_ids,
            'frauds_detected': frauds_detected,
            'token_usage': token_usage,
            'duration': batch_duration,
            'response_text': response_text
        }
        
    except Exception as e:
        batch_end_time = datetime.now()
        batch_duration = (batch_end_time - batch_start_time).total_seconds()
        
        return {
            'batch_num': batch_num,
            'transaction_ids': transaction_ids,
            'frauds_detected': [],
            'error': str(e),
            'token_usage': token_usage,
            'duration': batch_duration
        }
