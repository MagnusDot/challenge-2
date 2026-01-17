import json
import sys
import threading
from pathlib import Path
from typing import List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from Agent.helpers.http_client import make_api_request

_fraud_file_lock = threading.Lock()
FRAUD_FILE_PATH = Path(__file__).parent.parent / 'results' / 'final_fraud.json'


def report_fraud(transaction_id: str, reasons: str) -> str:
    """Report a fraudulent transaction.
    
    Call this tool when you have identified a transaction as fraudulent.
    You can call this tool multiple times if you find multiple fraudulent transactions.
    The fraud will be automatically saved to final_fraud.json.
    
    Args:
        transaction_id: The UUID of the fraudulent transaction (36 characters, format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        reasons: A comma-separated list of fraud indicators (e.g., "account_drained,time_correlation,new_merchant,location_anomaly")
    
    Returns:
        Confirmation message indicating the fraud was reported and saved
    """
    fraud_entry = {
        'transaction_id': transaction_id,
        'risk_level': 'critical',
        'risk_score': 100,
        'reason': reasons,
        'anomalies': [r.strip() for r in reasons.split(',') if r.strip()],
        'detected_at': datetime.now().isoformat()
    }
    
    _save_fraud_sync(fraud_entry)
    
    return f"Fraud reported and saved for transaction {transaction_id}: {reasons}"


def _save_fraud_sync(fraud_entry: dict) -> None:
    """Save fraud entry to final_fraud.json (thread-safe)."""
    with _fraud_file_lock:
        FRAUD_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        existing_frauds = []
        if FRAUD_FILE_PATH.exists():
            try:
                with open(FRAUD_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_frauds = data
                    elif isinstance(data, dict) and 'frauds' in data:
                        existing_frauds = data['frauds']
            except (json.JSONDecodeError, IOError):
                existing_frauds = []
        
        transaction_id = fraud_entry['transaction_id']
        existing_ids = {f.get('transaction_id') for f in existing_frauds if isinstance(f, dict)}
        
        if transaction_id not in existing_ids:
            existing_frauds.append(fraud_entry)
            
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'total_frauds': len(existing_frauds),
                'frauds': existing_frauds
            }
            
            with open(FRAUD_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)


async def get_transaction_aggregated_batch(transaction_ids: str) -> str:
    try:
        transaction_ids_list = json.loads(transaction_ids)
        if not isinstance(transaction_ids_list, list):
            transaction_ids_list = [transaction_ids_list]
    except (json.JSONDecodeError, TypeError):
        transaction_ids_list = [transaction_ids]
    
    if not transaction_ids_list:
        return 'Error: transaction_ids list cannot be empty'
    
    if len(transaction_ids_list) > 200:
        return f'Error: Maximum 200 transaction IDs allowed. Got: {len(transaction_ids_list)}'
    
    for tid in transaction_ids_list:
        if not isinstance(tid, str) or len(tid) != 36:
            return f'Error: Invalid transaction_id (must be 36 chars UUID). Got: {tid}'
    
    if len(transaction_ids_list) == 1:
        endpoint = f'/transactions/{transaction_ids_list[0]}'
        try:
            data = await make_api_request('GET', endpoint, response_format='toon')
            return data
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                return f'Error: Transaction {transaction_ids_list[0]} not found'
            return f'Error: Failed to retrieve transaction {transaction_ids_list[0]}: {error_msg}'
    else:
        endpoint = '/transactions/batch'
        try:
            data = await make_api_request('POST', endpoint, json_data=transaction_ids_list, response_format='toon')
            return data
        except Exception as e:
            error_msg = str(e)
            return f'Error: Failed to retrieve batch transactions: {error_msg}'


async def check_time_correlation(transaction_id: str, time_window_hours: float = 4.0) -> str:
    """Check if a transaction has time correlation with phishing emails/SMS.
    
    This tool checks if the transaction occurred within a time window after
    receiving suspicious emails or SMS messages that indicate phishing.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 4.0)
    
    Returns:
        JSON string with time correlation analysis
    """
    try:
        endpoint = '/fraud-tools/check-time-correlation'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check time correlation: {str(e)}'


async def check_new_merchant(transaction_id: str) -> str:
    """Check if a transaction is with a new merchant/recipient.
    
    This tool checks if the user has transacted with this merchant/recipient
    before by checking recipient_id, recipient_iban, and description in
    the user's transaction history.
    
    Args:
        transaction_id: The UUID of the transaction to check
    
    Returns:
        JSON string with new merchant analysis
    """
    try:
        endpoint = '/fraud-tools/check-new-merchant'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={'transaction_id': transaction_id},
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check new merchant: {str(e)}'


async def check_location_anomaly(transaction_id: str, use_city_fallback: bool = True) -> str:
    """Check if a transaction has location anomaly.
    
    This tool checks if the transaction location is far from the user's
    residence or recent locations. Uses GPS coordinates if available,
    otherwise falls back to city-based comparison.
    
    Args:
        transaction_id: The UUID of the transaction to check
        use_city_fallback: Use city-based comparison if GPS unavailable (default: True)
    
    Returns:
        JSON string with location anomaly analysis
    """
    try:
        endpoint = '/fraud-tools/check-location-anomaly'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'use_city_fallback': use_city_fallback
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check location anomaly: {str(e)}'


async def check_withdrawal_pattern(transaction_id: str, time_window_hours: float = 2.0) -> str:
    """Check if a transaction is part of a multiple withdrawals pattern.
    
    This tool checks if there are multiple withdrawals within a time window,
    which is a strong indicator of identity verification scams.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 2.0)
    
    Returns:
        JSON string with withdrawal pattern analysis
    """
    try:
        endpoint = '/fraud-tools/check-withdrawal-pattern'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check withdrawal pattern: {str(e)}'


async def check_phishing_indicators(transaction_id: str, time_window_hours: float = 4.0) -> str:
    """Check for phishing indicators in emails/SMS related to a transaction.
    
    This tool analyzes emails and SMS messages to detect phishing indicators
    and categorizes them (parcel_customs, identity_verification, bank_fraud, etc.).
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 4.0)
    
    Returns:
        JSON string with phishing indicators analysis
    """
    try:
        endpoint = '/fraud-tools/check-phishing-indicators'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check phishing indicators: {str(e)}'


async def check_time_correlation(transaction_id: str, time_window_hours: float = 4.0) -> str:
    """Check if a transaction has time correlation with phishing emails/SMS.
    
    This tool checks if the transaction occurred within a time window after
    receiving suspicious emails or SMS messages that indicate phishing.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 4.0)
    
    Returns:
        JSON string with time correlation analysis
    """
    try:
        endpoint = '/fraud-tools/check-time-correlation'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check time correlation: {str(e)}'


async def check_new_merchant(transaction_id: str) -> str:
    """Check if a transaction is with a new merchant/recipient.
    
    This tool checks if the user has transacted with this merchant/recipient
    before by checking recipient_id, recipient_iban, and description in
    the user's transaction history.
    
    Args:
        transaction_id: The UUID of the transaction to check
    
    Returns:
        JSON string with new merchant analysis
    """
    try:
        endpoint = '/fraud-tools/check-new-merchant'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={'transaction_id': transaction_id},
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check new merchant: {str(e)}'


async def check_location_anomaly(transaction_id: str, use_city_fallback: bool = True) -> str:
    """Check if a transaction has location anomaly.
    
    This tool checks if the transaction location is far from the user's
    residence or recent locations. Uses GPS coordinates if available,
    otherwise falls back to city-based comparison.
    
    Args:
        transaction_id: The UUID of the transaction to check
        use_city_fallback: Use city-based comparison if GPS unavailable (default: True)
    
    Returns:
        JSON string with location anomaly analysis
    """
    try:
        endpoint = '/fraud-tools/check-location-anomaly'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'use_city_fallback': use_city_fallback
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check location anomaly: {str(e)}'


async def check_withdrawal_pattern(transaction_id: str, time_window_hours: float = 2.0) -> str:
    """Check if a transaction is part of a multiple withdrawals pattern.
    
    This tool checks if there are multiple withdrawals within a time window,
    which is a strong indicator of identity verification scams.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 2.0)
    
    Returns:
        JSON string with withdrawal pattern analysis
    """
    try:
        endpoint = '/fraud-tools/check-withdrawal-pattern'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check withdrawal pattern: {str(e)}'


async def check_phishing_indicators(transaction_id: str, time_window_hours: float = 4.0) -> str:
    """Check for phishing indicators in emails/SMS related to a transaction.
    
    This tool analyzes emails and SMS messages to detect phishing indicators
    and categorizes them (parcel_customs, identity_verification, bank_fraud, etc.).
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours (default: 4.0)
    
    Returns:
        JSON string with phishing indicators analysis
    """
    try:
        endpoint = '/fraud-tools/check-phishing-indicators'
        data = await make_api_request(
            'POST',
            endpoint,
            json_data={
                'transaction_id': transaction_id,
                'time_window_hours': time_window_hours
            },
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check phishing indicators: {str(e)}'
