"""
Response formatter for API endpoints.

Supports both JSON and TOON formats based on Accept header or query parameter.
"""

from typing import Any, Optional
from fastapi import Response
from fastapi.responses import JSONResponse, PlainTextResponse
from api.utils.toon_formatter import format_response_as_toon
import json


class TOONResponse(PlainTextResponse):
    """Custom response class for TOON format."""
    
    media_type = "text/plain"
    
    def render(self, content: Any) -> bytes:
        """Render content as TOON format."""
        if isinstance(content, str):
            return content.encode("utf-8")
        
        toon_str = format_response_as_toon(content)
        return toon_str.encode("utf-8")


def format_response(
    data: Any,
    response_format: str = "json",
    status_code: int = 200
) -> Response:
    """
    Format API response in requested format.
    
    Args:
        data: Response data
        response_format: Either "json" or "toon"
        status_code: HTTP status code
        
    Returns:
        FastAPI Response object
    """
    if response_format.lower() == "toon":
        return TOONResponse(
            content=data,
            status_code=status_code
        )
    else:
        # Default to JSON
        return JSONResponse(
            content=data if not hasattr(data, '__dict__') else json.loads(
                json.dumps(data, default=lambda o: o.__dict__)
            ),
            status_code=status_code
        )



