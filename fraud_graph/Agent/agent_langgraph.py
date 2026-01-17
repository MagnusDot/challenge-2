"""Agent de détection de fraude avec LangGraph et create_agent/create_react_agent."""

import os
import sys
import logging
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .langchain_tools import get_all_tools

logger = logging.getLogger(__name__)

# Réduire le bruit des logs
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_TURN_OFF_MESSAGE_LOGGING", "true")


def load_system_prompt() -> str:
    """Charge le prompt système."""
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


def create_llm():
    """Crée le modèle LLM selon la configuration."""
    model_name = os.getenv('MODEL', 'openrouter/openai/gpt-4.1')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not openrouter_key:
        raise ValueError('OPENROUTER_API_KEY environment variable is required')
    
    # Utiliser LiteLLM via OpenAI pour OpenRouter
    if 'openrouter' in model_name.lower():
        # Extraire le modèle réel (ex: openrouter/openai/gpt-4.1 -> gpt-4.1)
        model_parts = model_name.split('/')
        if len(model_parts) >= 3:
            actual_model = '/'.join(model_parts[1:])  # openai/gpt-4.1
        else:
            actual_model = model_parts[-1]
        
        llm = ChatOpenAI(
            model=actual_model,
            openai_api_key=openrouter_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
            timeout=600,
        )
    elif 'gemini' in model_name.lower() or 'google' in model_name.lower():
        google_key = os.getenv('GOOGLE_API_KEY')
        if not google_key:
            raise ValueError('GOOGLE_API_KEY environment variable is required for Gemini')
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            timeout=600,
        )
    else:
        # Par défaut, utiliser OpenAI
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            timeout=600,
        )
    
    return llm


def _should_continue(state: MessagesState) -> str:
    """Détermine si l'agent doit continuer ou terminer."""
    messages = state["messages"]
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    # Si le dernier message est un AIMessage avec tool_calls, on continue
    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    # Sinon, on termine
    return "end"


def _call_model(state: MessagesState, llm, system_prompt: str):
    """Appelle le modèle LLM."""
    messages = state["messages"]
    
    # Ajouter le prompt système si ce n'est pas déjà fait
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SystemMessage(content=system_prompt)] + messages
    
    response = llm.invoke(messages)
    return {"messages": [response]}


@lru_cache(maxsize=1)
def create_fraud_agent():
    """Crée l'agent de détection de fraude avec LangGraph (ReAct pattern)."""
    system_prompt = load_system_prompt()
    llm = create_llm()
    tools = get_all_tools()
    
    # Bind les outils au LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Créer le graph
    workflow = StateGraph(MessagesState)
    
    # Node pour appeler le modèle
    workflow.add_node("agent", lambda state: _call_model(state, llm_with_tools, system_prompt))
    
    # Node pour exécuter les outils
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    # Point d'entrée
    workflow.set_entry_point("agent")
    
    # Edges conditionnels
    workflow.add_conditional_edges(
        "agent",
        _should_continue,
        {
            "continue": "tools",
            "end": END,
        }
    )
    
    # Edge de retour après les outils
    workflow.add_edge("tools", "agent")
    
    # Compiler le graph
    agent = workflow.compile()
    
    logger.info(f"✅ Agent LangGraph créé avec {len(tools)} outils")
    
    return agent


def create_fraud_agent_with_checkpoint():
    """Crée l'agent avec support de checkpoint pour la persistance."""
    agent = create_fraud_agent()
    
    # Ajouter le checkpoint memory
    memory = MemorySaver()
    
    # Compiler le graph avec checkpoint
    compiled_agent = agent.compile(checkpointer=memory)
    
    return compiled_agent, memory


async def run_agent_async(
    agent: Any,
    message: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Exécute l'agent de manière asynchrone.
    
    Args:
        agent: L'agent LangGraph
        message: Le message utilisateur
        config: Configuration optionnelle (thread_id, etc.)
    
    Returns:
        Le résultat de l'exécution
    """
    if config is None:
        config = {}
    
    # Si pas de thread_id, en créer un
    if 'configurable' not in config:
        config['configurable'] = {}
    
    if 'thread_id' not in config['configurable']:
        import uuid
        config['configurable']['thread_id'] = str(uuid.uuid4())
    
    result = None
    events = []
    
    try:
        from langchain_core.messages import HumanMessage
        
        async for event in agent.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config
        ):
            events.append(event)
            # Le dernier événement contient généralement le résultat
            if event:
                result = event
        
        return {
            'result': result,
            'events': events,
            'success': True
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de l'agent: {e}", exc_info=True)
        return {
            'result': None,
            'events': events,
            'success': False,
            'error': str(e)
        }


def run_agent_sync(
    agent: Any,
    message: str,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Exécute l'agent de manière synchrone.
    
    Args:
        agent: L'agent LangGraph
        message: Le message utilisateur
        config: Configuration optionnelle (thread_id, etc.)
    
    Returns:
        Le résultat de l'exécution
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(run_agent_async(agent, message, config))
