import os
import sys
import logging
from pathlib import Path
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

sys.path.insert(0, str(Path(__file__).parent.parent))
from fraud_graph.Agent.agent import create_fraud_agent
from fraud_graph.utils.output_filter import setup_output_filter

setup_output_filter()

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "")

def setup_runner():

    # Modèle par défaut : GPT 4.1
    # Alternatives:
    # - openrouter/openai/gpt-4.1 (par défaut)
    # - openrouter/openai/gpt-4-turbo (rapide)
    # - openrouter/mistralai/ministral-14b-2512 (économique)
    model = os.getenv('MODEL', 'openrouter/openai/gpt-4.1')
    print(f"\n🤖 Creating fraud agent with model: {model}")

    use_cache = os.getenv('LITELLM_CACHE', 'false').lower() == 'true'
    if use_cache:
        print("   📦 LiteLLM caching enabled (set LITELLM_CACHE=true)")

    agent = create_fraud_agent()
    print(f"✅ Agent '{agent.name}' initialized with batch tool!")

    print(f"🔧 Creating Runner with session management...")
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="transaction_fraud_analysis",
        agent=agent,
        session_service=session_service,
    )
    print(f"✅ Runner configured!")

    return runner