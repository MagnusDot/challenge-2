import os
from Agent.challenge import create_challenge_agent
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.sessions.in_memory_session_service import InMemorySessionService

def setup_app():

    model = os.getenv('MODEL', 'openrouter/mistralai/ministral-14b-2512')
    print(f"\n🤖 Creating challenge agent with model: {model}")

    agent = create_challenge_agent(model=model)
    print(f"✅ Agent '{agent.name}' initialized!")

    context_cache_config = None
    if model.startswith("gemini-2") or "gemini" in model.lower():
        min_tokens = int(os.getenv('CONTEXT_CACHE_MIN_TOKENS', '2048'))
        ttl_seconds = int(os.getenv('CONTEXT_CACHE_TTL_SECONDS', '600'))
        cache_intervals = int(os.getenv('CONTEXT_CACHE_INTERVALS', '5'))

        context_cache_config = ContextCacheConfig(
            min_tokens=min_tokens,
            ttl_seconds=ttl_seconds,
            cache_intervals=cache_intervals
        )
        print(f"   📦 Context caching: min_tokens={min_tokens}, TTL={ttl_seconds}s, intervals={cache_intervals}")
    else:
        print(f"   ⚠️  Context caching only works with Gemini 2.0+ models")
        print(f"   💡 Current model: {model}")

    print(f"🔧 Creating App with context caching...")
    session_service = InMemorySessionService()

    app = App(
        name="transaction_fraud_analysis",
        root_agent=agent,
        session_service=session_service,
        context_cache_config=context_cache_config,
    )
    print(f"✅ App configured with context caching!")

    return app