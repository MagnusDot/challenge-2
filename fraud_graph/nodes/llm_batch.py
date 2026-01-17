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

STEP 1: Call get_transaction_aggregated_batch('{transaction_ids_json}') ONCE.
STEP 2: Analyze all transactions from the returned data.
STEP 3: Follow the output format specified in your instructions.

CRITICAL: Only ONE tool call to get_transaction_aggregated_batch. Use the batch endpoint."""
    
    prompt = f"""{system_prompt}

---

{user_prompt}"""
    
    user_message = types.Content(
        role='user',
        parts=[types.Part(text=prompt)]
    )
    
    response_text = ''
    tool_calls_count = 0
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
            response_text, token_usage, tool_calls_count = process_event(
                event, response_text, token_usage, tool_calls_count, batch_num
            )
        
        response_text = response_text.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])
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
        if response_text:
            for line in response_text.split('\n'):
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    transaction_id = parts[0].strip()
                    reasons_str = parts[1].strip()
                    
                    reasons = []
                    reasons_str = reasons_str.strip()
                    if reasons_str.startswith('[') and reasons_str.endswith(']'):
                        reasons_str = reasons_str[1:-1].strip()
                        if reasons_str:
                            reasons = [r.strip() for r in reasons_str.split(',') if r.strip()]
                    
                    if transaction_id and reasons:
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
