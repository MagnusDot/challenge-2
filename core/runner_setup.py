import os
from Agent.challenge import create_challenge_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

def setup_runner():

    # Modèle par défaut : Mistral Ministral 14B (version 2512)
    # Alternatives pas chères avec support JSON:
    # - openrouter/mistralai/mistral-small-3.2-24b-instruct (recommandé, très bon marché)
    # - openrouter/deepseek/deepseek-chat (excellent pour JSON avec format strict)
    # - openrouter/openai/gpt-3.5-turbo (classique, fiable)
    # - openrouter/google/gemini-flash-1.5 (ultra pas cher)
    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
    print(f"\n🤖 Creating challenge agent with model: {model}")

    use_cache = os.getenv('LITELLM_CACHE', 'false').lower() == 'true'
    if use_cache:
        print("   📦 LiteLLM caching enabled (set LITELLM_CACHE=true)")

    agent = create_challenge_agent(model=model)
    print(f"✅ Agent '{agent.name}' initialized!")

    print(f"🔧 Creating Runner with session management...")
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="transaction_fraud_analysis",
        agent=agent,
        session_service=session_service,
    )
    print(f"✅ Runner configured!")

    return runner