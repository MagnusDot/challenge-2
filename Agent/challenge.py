import os
from pathlib import Path
from functools import lru_cache

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from .tools import (
    get_transaction_aggregated,
    get_current_time,
)

@lru_cache(maxsize=1)
def load_system_prompt() -> str:

    prompt_file = os.getenv('SYSTEM_PROMPT_FILE', 'system_prompt_compact.md')
    prompt_path = Path(__file__).parent / prompt_file

    if not prompt_path.exists() and prompt_file == 'system_prompt_compact.md':
        prompt_path = Path(__file__).parent / "system_prompt.md"

    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_challenge_agent(model: str = "openrouter/mistralai/mistral-small-3.2-24b-instruct") -> Agent:

    system_prompt = load_system_prompt()

    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    # Certains modèles ne supportent pas json response format with tools
    # Liste des modèles qui ne supportent PAS json_format avec tools
    models_no_json_format = ['mistral', 'mixtral', 'gemini']
    use_json_format = not any(no_json_model in model.lower() for no_json_model in models_no_json_format)
    
    llm_model_kwargs = {
        "model": model,
        "parallel_tool_calls": True,
        "timeout": 600,
    }
    
    if use_json_format:
        llm_model_kwargs["response_format"] = {"type": "json_object"}
    
    llm_model = LiteLlm(**llm_model_kwargs)

    agent = Agent(
        model=llm_model,
        name='challenge_agent',
        description="Financial data analyst with access to aggregated transaction data including users, locations, SMS, and emails.",
        instruction=system_prompt,
        tools=[
            get_transaction_aggregated,
            get_current_time,
        ],
    )
    return agent