import os
import sys
import logging
from pathlib import Path
from functools import lru_cache
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fraud_graph.utils.output_filter import setup_output_filter

from .tools import (
    get_transaction_aggregated_batch,
    report_fraud,
    check_time_correlation,
    check_new_merchant,
    check_location_anomaly,
    check_withdrawal_pattern,
    check_phishing_indicators,
)

setup_output_filter()

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "")


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    # Try optimized version first, fallback to full version
    prompt_file = os.getenv('FRAUD_AGENT_PROMPT_FILE', 'system_prompt_optimized.md')
    prompt_path = Path(__file__).parent / prompt_file
    
    # Fallback to system_prompt.md if optimized doesn't exist
    if not prompt_path.exists() and prompt_file == 'system_prompt_optimized.md':
        prompt_path = Path(__file__).parent / 'system_prompt.md'
    
    if not prompt_path.exists():
        raise FileNotFoundError(
            f'System prompt file not found: {prompt_path}\n'
            f'Set FRAUD_AGENT_PROMPT_FILE in .env to specify the prompt file.'
        )
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


@lru_cache(maxsize=1)
def create_fraud_agent() -> Agent:
    system_prompt = load_system_prompt()
    model = os.getenv('MODEL', 'openrouter/openai/gpt-4.1')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not openrouter_key:
        raise ValueError('OPENROUTER_API_KEY environment variable is required')
    
    models_no_json_format = ['mistral', 'mixtral', 'gemini']
    use_json_format = not any(no_json_model in model.lower() for no_json_model in models_no_json_format)
    
    llm_model_kwargs = {
        'model': model,
        'parallel_tool_calls': True,
        'timeout': 600,
    }
    
    if use_json_format:
        llm_model_kwargs['response_format'] = {'type': 'json_object'}
    
    llm_model = LiteLlm(**llm_model_kwargs)
    
    agent = Agent(
        model=llm_model,
        name='fraud_analyst',
        description='Financial fraud analyst with access to aggregated transaction data.',
        instruction=system_prompt,
        tools=[
            get_transaction_aggregated_batch,
            report_fraud,
            check_time_correlation,
            check_new_merchant,
            check_location_anomaly,
            check_withdrawal_pattern,
            check_phishing_indicators,
        ],
    )
    
    return agent
