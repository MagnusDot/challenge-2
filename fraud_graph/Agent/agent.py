import os
import logging
from pathlib import Path
from functools import lru_cache
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

from .tools import get_transaction_aggregated_batch

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    prompt_file = os.getenv('FRAUD_AGENT_PROMPT_FILE', 'prompt.md')
    prompt_path = Path(__file__).parent / prompt_file
    
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
    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
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
        ],
    )
    
    return agent
