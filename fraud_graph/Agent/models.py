"""Modèles Pydantic pour les outils de l'agent de détection de fraude."""

from pydantic import BaseModel, Field
from typing import List, Union


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
    
    transaction_ids: Union[str, List[str]] = Field(
        ...,
        description="JSON string containing a single UUID or a list of UUIDs, or a list of UUIDs directly"
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
