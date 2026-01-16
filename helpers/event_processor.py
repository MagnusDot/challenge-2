import os
from typing import Dict, Any, Tuple

def process_event(event: Any, response_text: str, token_usage: Dict[str, int], tool_calls_count: int, transaction_num: int) -> Tuple[str, Dict[str, int], int]:
    event_type = type(event).__name__
    
    if transaction_num == 1 and os.getenv('DEBUG_TOKENS') == '1':
        print(f"\n[DEBUG] Event type: {event_type}")
        print(f"[DEBUG] Event attributes: {dir(event)}")
        if hasattr(event, '__dict__'):
            print(f"[DEBUG] Event dict: {event.__dict__}")
    
    if hasattr(event, 'usage') and event.usage is not None:
        usage = event.usage
        if hasattr(usage, 'prompt_tokens'):
            token_usage["prompt_tokens"] += getattr(usage, 'prompt_tokens', 0)
        if hasattr(usage, 'completion_tokens'):
            token_usage["completion_tokens"] += getattr(usage, 'completion_tokens', 0)
        if hasattr(usage, 'total_tokens'):
            token_usage["total_tokens"] += getattr(usage, 'total_tokens', 0)
    
    if hasattr(event, 'usage_metadata') and event.usage_metadata is not None:
        metadata = event.usage_metadata
        if hasattr(metadata, 'prompt_token_count'):
            token_usage["prompt_tokens"] += getattr(metadata, 'prompt_token_count', 0)
        if hasattr(metadata, 'candidates_token_count'):
            token_usage["completion_tokens"] += getattr(metadata, 'candidates_token_count', 0)
        if hasattr(metadata, 'total_token_count'):
            token_usage["total_tokens"] += getattr(metadata, 'total_token_count', 0)
    
    if hasattr(event, 'prompt_tokens') and event.prompt_tokens:
        token_usage["prompt_tokens"] += event.prompt_tokens
    if hasattr(event, 'completion_tokens') and event.completion_tokens:
        token_usage["completion_tokens"] += event.completion_tokens
    if hasattr(event, 'total_tokens') and event.total_tokens:
        token_usage["total_tokens"] += event.total_tokens
    
    if hasattr(event, 'content'):
        if hasattr(event.content, 'parts'):
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
        elif hasattr(event.content, 'text'):
            response_text += event.content.text
        elif isinstance(event.content, str):
            response_text += event.content
    elif hasattr(event, 'text') and event.text:
        response_text += event.text
    elif hasattr(event, 'message'):
        if hasattr(event.message, 'content'):
            response_text += str(event.message.content)
    
    if 'ToolCall' in event_type or 'tool_call' in event_type.lower():
        tool_calls_count += 1
    
    return response_text, token_usage, tool_calls_count
