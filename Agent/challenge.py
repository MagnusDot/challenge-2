"""
Challenge Agent - Financial data analyst with API tools
"""

import os
from pathlib import Path

from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from .tools import (
    get_transaction_aggregated,
    get_current_time,
)


def load_system_prompt() -> str:
    """Load the system prompt from markdown file.
    
    Returns:
        The system prompt as a string
    """
    prompt_path = Path(__file__).parent / "system_prompt.md"
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def create_challenge_agent(model: str = "openai/gpt-4.1") -> Agent:
    """Create and configure the challenge agent.
    
    Args:
        model: The model to use for the agent (default: openai/gpt-4.1)
               Use format: "openai/gpt-4.1", "openai/gpt-4", "openai/gpt-4-turbo", "openai/gpt-3.5-turbo"
               Or Gemini: "gemini-2.0-flash-exp", "gemini-1.5-pro"
        
    Returns:
        Configured Agent instance with comprehensive API tools
    """
    # Load system prompt from markdown file
    system_prompt = load_system_prompt()
    
    # Use LiteLLM for OpenAI and OpenRouter models, otherwise use model string directly
    if model.startswith("openai/") or model.startswith("openrouter/"):
        llm_model = LiteLlm(
            model=model,
            parallel_tool_calls=False,  # Enable parallel tool calls
            response_format={"type": "json_object"},  # Force JSON response
        )
    else:
        llm_model = model
    
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

