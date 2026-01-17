import os
from pathlib import Path
from functools import lru_cache
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from ..state import FraudState
from ..utils.tools import get_transaction_aggregated

@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    prompt_file = os.getenv('SYSTEM_PROMPT_FILE', 'system_prompt.md')
    prompt_path = Path(__file__).parent.parent.parent / 'Agent' / prompt_file
    if not prompt_path.exists():
        raise FileNotFoundError(f'System prompt file not found: {prompt_path}\nSet SYSTEM_PROMPT_FILE in .env to specify the prompt file.')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

@lru_cache(maxsize=1)
def create_fraud_agent() -> Agent:
    system_prompt = load_system_prompt()
    model = os.getenv('MODEL', 'openrouter/openai/gpt-5-mini')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_key:
        raise ValueError('OPENROUTER_API_KEY environment variable is required')
    models_no_json_format = ['mistral', 'mixtral', 'gemini']
    use_json_format = not any((no_json_model in model.lower() for no_json_model in models_no_json_format))
    llm_model_kwargs = {'model': model, 'parallel_tool_calls': True, 'timeout': 600}
    if use_json_format:
        llm_model_kwargs['response_format'] = {'type': 'json_object'}
    llm_model = LiteLlm(**llm_model_kwargs)
    agent = Agent(model=llm_model, name='fraud_analyst', description='Financial fraud analyst with access to aggregated transaction data.', instruction=system_prompt, tools=[get_transaction_aggregated])
    return agent

async def llm_analysis(state: FraudState) -> FraudState:
    transaction_id = state.get('current_transaction_id')
    if not transaction_id:
        return {**state, 'decision': 'ERROR', 'llm_result': {'error': 'No transaction_id provided'}, 'explanation': 'Erreur: transaction_id manquant'}
    try:
        agent = create_fraud_agent()
        prompt = f'Transaction ID: {transaction_id}'
        response = agent.run(prompt)
        if isinstance(response, str):
            if '|' in response:
                parts = response.split('|', 1)
                decision = 'FRAUDULENT' if parts[1].strip() else 'LEGITIMATE'
                explanation = parts[1].strip() if len(parts) > 1 else ''
            else:
                decision = 'LEGITIMATE' if not response.strip() else 'FRAUDULENT'
                explanation = response.strip()
        else:
            decision = response.get('decision', 'LEGITIMATE')
            explanation = response.get('explanation', '')
        return {**state, 'llm_result': {'raw_response': str(response), 'decision': decision, 'explanation': explanation}, 'decision': decision, 'explanation': explanation}
    except Exception as e:
        return {**state, 'decision': 'ERROR', 'llm_result': {'error': str(e)}, 'explanation': f"Erreur lors de l'analyse LLM: {str(e)}"}