from typing import Any, Dict

from Agent.helpers.http_client import make_api_request

async def get_transaction_aggregated(transaction_id: str) -> str:

    if not transaction_id or len(transaction_id) != 36:
        return f"Error: Invalid transaction_id (must be 36 chars UUID). Got: {transaction_id}"

    endpoint = f"/transactions/{transaction_id}"

    try:

        data = await make_api_request("GET", endpoint, response_format="toon")

        return data

    except Exception as e:
        error_msg = str(e)

        if "404" in error_msg:
            return f"Error: Transaction {transaction_id} not found"

        return f"Error: Failed to retrieve transaction {transaction_id}: {error_msg}"