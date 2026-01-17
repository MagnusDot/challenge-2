import os
from Agent.challenge import create_challenge_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

def setup_runner():

    model = os.getenv('MODEL', 'openrouter/openai/gpt-5-mini')
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