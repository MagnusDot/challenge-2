"""
HTTP client utilities for API tools.
"""

import asyncio
import httpx
from typing import Any, Dict, Optional, Union


async def make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    base_url: str = "http://localhost:8000",
    timeout: float = 30.0,
    response_format: str = "toon"
) -> Union[Dict[str, Any], str]:
    """
    Make an asynchronous API request to the FastAPI backend.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        params: Query parameters
        json_data: JSON body data
        base_url: Base URL of the API
        timeout: Request timeout in seconds
        response_format: Response format: "json" or "toon" (default: "toon" for token efficiency)
        
    Returns:
        Dict containing the response data (if json) or TOON-formatted string (if toon)
        
    Raises:
        httpx.HTTPError: If request fails
    """
    url = f"{base_url}{endpoint}"
    
    # Remove None values from params
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    
    # Add format parameter to request TOON format from API
    if params is None:
        params = {}
    params['format'] = response_format
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        
        # Petit délai pour éviter les rate limits (0.1s = 600 requêtes/min max)
        await asyncio.sleep(0.1)
        
        # Return based on requested format
        if response_format == "toon":
            return response.text
        else:
            return response.json()


def format_filters_description(params: Dict[str, Any]) -> str:
    """
    Format filters used in a human-readable way.
    
    Args:
        params: Dictionary of parameters used
        
    Returns:
        String describing the filters
    """
    if not params or all(v is None for v in params.values()):
        return "No filters applied"
    
    filters = []
    for key, value in params.items():
        if value is not None and key not in ['skip', 'limit']:
            filters.append(f"{key}={value}")
    
    if not filters:
        return "No filters applied"
    
    return "Filters: " + ", ".join(filters)

