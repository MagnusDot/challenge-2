from Agent.helpers.http_client import make_api_request
from ..state import FraudState


async def fetch_all_data(state: FraudState) -> FraudState:
    transaction_id = state.get("current_transaction_id")
    
    if not transaction_id:
        return state
    
    try:
        endpoint = f"/transactions/{transaction_id}"
        data = await make_api_request("GET", endpoint, response_format="json")
        
        transaction = data.get("transaction", {})
        sender = data.get("sender", {})
        
        user_profile = sender
        
        sms_data = data.get("sender_sms", []) + data.get("recipient_sms", [])
        email_data = data.get("sender_emails", []) + data.get("recipient_emails", [])
        location_data = data.get("sender_locations", []) + data.get("recipient_locations", [])
        
        return {
            **state,
            "transaction": transaction,
            "user_profile": user_profile,
            "sms_data": sms_data,
            "email_data": email_data,
            "location_data": location_data,
        }
    except Exception as e:
        return {
            **state,
            "transaction": None,
            "user_profile": None,
            "sms_data": [],
            "email_data": [],
            "location_data": [],
        }
