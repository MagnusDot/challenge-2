"""Outils LangChain pour l'agent de détection de fraude."""

import json
import sys
import threading
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from functools import wraps
from datetime import datetime

from langchain_core.tools import tool
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

# Configuration pour la sauvegarde des fraudes
_fraud_file_lock = threading.Lock()
FRAUD_FILE_PATH = Path(__file__).parent.parent / 'results' / 'final_fraud.json'


# ============================================================================
# Fonctions utilitaires
# ============================================================================

def safe_tool_execution(func: Callable) -> Callable:
    """Wrapper pour garantir que les outils retournent toujours une chaîne valide.
    
    Tous les outils doivent retourner une valeur, même en cas d'erreur.
    Ce wrapper capture toutes les exceptions et retourne un message d'erreur formaté.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # S'assurer que le résultat est toujours une chaîne
            if result is None:
                return f"Tool {func.__name__} returned None"
            if not isinstance(result, str):
                return json.dumps(result, indent=2, ensure_ascii=False)
            return result
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Retourner toujours une chaîne, même en cas d'erreur
            return f"Error: {error_msg}"
    
    return wrapper


def _make_api_request_sync(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    base_url: str = "http://localhost:8000",
    timeout: float = 300.0,
    response_format: str = "toon"
) -> Union[Dict[str, Any], str]:
    """Synchronous version of make_api_request using requests."""
    url = f"{base_url}{endpoint}"
    
    if params is None:
        params = {}
    else:
        params = {k: v for k, v in params.items() if v is not None}
    
    params['format'] = response_format
    
    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            timeout=timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        if response_format == "toon":
            return response.text
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")


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


# ============================================================================
# Fonctions métier (implémentations)
# ============================================================================

@safe_tool_execution
def _report_fraud_impl(transaction_id: str, reasons: str) -> str:
    """Report a fraudulent transaction (implémentation)."""
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


@safe_tool_execution
def _get_transaction_aggregated_batch_impl(transaction_ids: str) -> str:
    """Get aggregated transaction data (implémentation)."""
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
            data = _make_api_request_sync('GET', endpoint, response_format='toon')
            return data
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                return f'Error: Transaction {transaction_ids_list[0]} not found'
            return f'Error: Failed to retrieve transaction {transaction_ids_list[0]}: {error_msg}'
    else:
        endpoint = '/transactions/batch'
        try:
            data = _make_api_request_sync('POST', endpoint, json_data=transaction_ids_list, response_format='toon')
            return data
        except Exception as e:
            error_msg = str(e)
            return f'Error: Failed to retrieve batch transactions: {error_msg}'


@safe_tool_execution
def _check_time_correlation_impl(transaction_id: str, time_window_hours: float) -> str:
    """Check time correlation (implémentation)."""
    try:
        endpoint = '/fraud-tools/check-time-correlation'
        data = _make_api_request_sync(
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


@safe_tool_execution
def _check_new_merchant_impl(transaction_id: str) -> str:
    """Check new merchant (implémentation)."""
    try:
        endpoint = '/fraud-tools/check-new-merchant'
        data = _make_api_request_sync(
            'POST',
            endpoint,
            json_data={'transaction_id': transaction_id},
            response_format='json'
        )
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f'Error: Failed to check new merchant: {str(e)}'


@safe_tool_execution
def _check_location_anomaly_impl(transaction_id: str, use_city_fallback: bool) -> str:
    """Check location anomaly (implémentation)."""
    try:
        endpoint = '/fraud-tools/check-location-anomaly'
        data = _make_api_request_sync(
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


@safe_tool_execution
def _check_withdrawal_pattern_impl(transaction_id: str, time_window_hours: float) -> str:
    """Check withdrawal pattern (implémentation)."""
    try:
        endpoint = '/fraud-tools/check-withdrawal-pattern'
        data = _make_api_request_sync(
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


@safe_tool_execution
def _check_phishing_indicators_impl(transaction_id: str, time_window_hours: float) -> str:
    """Check phishing indicators (implémentation)."""
    try:
        endpoint = '/fraud-tools/check-phishing-indicators'
        data = _make_api_request_sync(
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


# ============================================================================
# Modèles Pydantic pour les outils
# ============================================================================

class ReportFraudInput(BaseModel):
    """Input pour l'outil report_fraud."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the fraudulent transaction (36 characters, format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
    )
    reasons: str = Field(
        ...,
        description="A comma-separated list of fraud indicators (e.g., 'account_drained,time_correlation,new_merchant,location_anomaly')"
    )


class GetTransactionAggregatedBatchInput(BaseModel):
    """Input pour l'outil get_transaction_aggregated_batch."""
    
    transaction_ids: str = Field(
        ...,
        description="JSON string containing a single UUID or a list of UUIDs"
    )


class CheckTimeCorrelationInput(BaseModel):
    """Input pour l'outil check_time_correlation."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the transaction to check"
    )
    time_window_hours: float = Field(
        ...,
        description="Time window in hours"
    )


class CheckNewMerchantInput(BaseModel):
    """Input pour l'outil check_new_merchant."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the transaction to check"
    )


class CheckLocationAnomalyInput(BaseModel):
    """Input pour l'outil check_location_anomaly."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the transaction to check"
    )
    use_city_fallback: bool = Field(
        True,
        description="Use city-based comparison if GPS unavailable"
    )


class CheckWithdrawalPatternInput(BaseModel):
    """Input pour l'outil check_withdrawal_pattern."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the transaction to check"
    )
    time_window_hours: float = Field(
        ...,
        description="Time window in hours"
    )


class CheckPhishingIndicatorsInput(BaseModel):
    """Input pour l'outil check_phishing_indicators."""
    
    transaction_id: str = Field(
        ...,
        description="The UUID of the transaction to check"
    )
    time_window_hours: float = Field(
        ...,
        description="Time window in hours"
    )


# ============================================================================
# Outils LangChain
# ============================================================================

@tool("report_fraud", args_schema=ReportFraudInput)
def report_fraud_tool(transaction_id: str, reasons: str) -> str:
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
    return _report_fraud_impl(transaction_id, reasons)


@tool("get_transaction_aggregated_batch", args_schema=GetTransactionAggregatedBatchInput)
def get_transaction_aggregated_batch_tool(transaction_ids: str) -> str:
    """Get aggregated transaction data for one or multiple transactions.
    
    Args:
        transaction_ids: JSON string containing a single UUID or a list of UUIDs
    
    Returns:
        Transaction data in toon format
    """
    return _get_transaction_aggregated_batch_impl(transaction_ids)


@tool("check_time_correlation", args_schema=CheckTimeCorrelationInput)
def check_time_correlation_tool(transaction_id: str, time_window_hours: float) -> str:
    """Check if a transaction has time correlation with phishing emails/SMS.
    
    This tool checks if the transaction occurred within a time window after
    receiving suspicious emails or SMS messages that indicate phishing.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours
    
    Returns:
        JSON string with time correlation analysis
    """
    return _check_time_correlation_impl(transaction_id, time_window_hours)


@tool("check_new_merchant", args_schema=CheckNewMerchantInput)
def check_new_merchant_tool(transaction_id: str) -> str:
    """Check if a transaction is with a new merchant/recipient.
    
    This tool checks if the user has transacted with this merchant/recipient
    before by checking recipient_id, recipient_iban, and description in
    the user's transaction history.
    
    Args:
        transaction_id: The UUID of the transaction to check
    
    Returns:
        JSON string with new merchant analysis
    """
    return _check_new_merchant_impl(transaction_id)


@tool("check_location_anomaly", args_schema=CheckLocationAnomalyInput)
def check_location_anomaly_tool(transaction_id: str, use_city_fallback: bool = True) -> str:
    """Check if a transaction has location anomaly.
    
    This tool checks if the transaction location is far from the user's
    residence or recent locations. Uses GPS coordinates if available,
    otherwise falls back to city-based comparison.
    
    Args:
        transaction_id: The UUID of the transaction to check
        use_city_fallback: Use city-based comparison if GPS unavailable
    
    Returns:
        JSON string with location anomaly analysis
    """
    return _check_location_anomaly_impl(transaction_id, use_city_fallback)


@tool("check_withdrawal_pattern", args_schema=CheckWithdrawalPatternInput)
def check_withdrawal_pattern_tool(transaction_id: str, time_window_hours: float) -> str:
    """Check if a transaction is part of a multiple withdrawals pattern.
    
    This tool checks if there are multiple withdrawals within a time window,
    which is a strong indicator of identity verification scams.
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours
    
    Returns:
        JSON string with withdrawal pattern analysis
    """
    return _check_withdrawal_pattern_impl(transaction_id, time_window_hours)


@tool("check_phishing_indicators", args_schema=CheckPhishingIndicatorsInput)
def check_phishing_indicators_tool(transaction_id: str, time_window_hours: float) -> str:
    """Check for phishing indicators in emails/SMS related to a transaction.
    
    This tool analyzes emails and SMS messages to detect phishing indicators
    and categorizes them (parcel_customs, identity_verification, bank_fraud, etc.).
    
    Args:
        transaction_id: The UUID of the transaction to check
        time_window_hours: Time window in hours
    
    Returns:
        JSON string with phishing indicators analysis
    """
    return _check_phishing_indicators_impl(transaction_id, time_window_hours)


def get_all_tools():
    """Retourne tous les outils LangChain."""
    return [
        report_fraud_tool,
        get_transaction_aggregated_batch_tool,
        check_time_correlation_tool,
        check_new_merchant_tool,
        check_location_anomaly_tool,
        check_withdrawal_pattern_tool,
        check_phishing_indicators_tool,
    ]
