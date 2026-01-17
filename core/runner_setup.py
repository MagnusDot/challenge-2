import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from fraud_graph.Agent import create_fraud_agent, LangGraphRunner

logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

# Désactiver complètement le logging worker de LiteLLM pour éviter les warnings
os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "")
os.environ.setdefault("LITELLM_TURN_OFF_MESSAGE_LOGGING", "true")
os.environ.setdefault("LITELLM_TURN_OFF_LOGGING", "false")  # Garder les erreurs critiques

def setup_runner():
    """Crée un runner LangGraph pour l'agent de détection de fraude.
    
    Returns:
        LangGraphRunner: Runner compatible avec l'interface existante
    """
    # Modèle par défaut : Ministral 14B (économique)
    # Alternatives:
    # - openrouter/mistralai/ministral-14b-2512 (par défaut, économique)
    # - openrouter/openai/gpt-4.1 (plus performant mais plus cher)
    # - openrouter/openai/gpt-4-turbo (rapide)
    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
    print(f"\n🤖 Creating fraud agent with model: {model}")

    use_cache = os.getenv('LITELLM_CACHE', 'false').lower() == 'true'
    if use_cache:
        print("   📦 LiteLLM caching enabled (set LITELLM_CACHE=true)")

    agent = create_fraud_agent()
    print(f"✅ Agent LangGraph initialized!")

    print(f"🔧 Creating LangGraph Runner...")
    runner = LangGraphRunner(agent)
    print(f"✅ Runner configured!")

    return runner