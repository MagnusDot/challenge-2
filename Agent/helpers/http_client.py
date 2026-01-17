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

    url = f"{base_url}{endpoint}"

    if params:
        params = {k: v for k, v in params.items() if v is not None}

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

        await asyncio.sleep(0.1)

        if response_format == "toon":
            return response.text
        else:
            return response.json()

def format_filters_description(params: Dict[str, Any]) -> str:

    if not params or all(v is None for v in params.values()):
        return "No filters applied"

    filters = []
    for key, value in params.items():
        if value is not None and key not in ['skip', 'limit']:
            filters.append(f"{key}={value}")

    if not filters:
        return "No filters applied"

    return "Filters: " + ", ".join(filters)