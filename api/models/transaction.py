"""
Transaction model with Pydantic validation.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    """Transaction model with strict validation."""
    
    transaction_id: str = Field(..., description="UUID of transaction", min_length=36, max_length=36)
    sender_id: Optional[str] = Field(default="", description="Sender ID")
    recipient_id: Optional[str] = Field(default="", description="Recipient ID")
    transaction_type: Optional[str] = Field(
        default="",
        description="Transaction type"
    )
    amount: float = Field(..., description="Transaction amount", ge=0)
    location: Optional[str] = Field(default="", description="Transaction location")
    payment_method: Optional[str] = Field(default="", description="Payment method")
    sender_iban: Optional[str] = Field(default="", description="Sender IBAN")
    recipient_iban: Optional[str] = Field(default="", description="Recipient IBAN")
    balance_after: Optional[float] = Field(default=0.0, description="Balance after transaction")
    description: Optional[str] = Field(default="", description="Transaction description")
    timestamp: Optional[str] = Field(default="", description="Transaction timestamp (ISO 8601)")
    is_fake_recipient: Optional[str] = Field(default="", description="Fraud indicator")
    
    @field_validator('transaction_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate UUID format."""
        if not v:
            return v
        import uuid
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('transaction_id must be a valid UUID')
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp."""
        if not v:
            return v
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            # If timestamp is invalid, return empty string instead of raising error
            return ""
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "7634023d-5751-4940-a2c9-36b97274f366",
                "sender_id": "PRZO-LTZE-7C1-CAS-0",
                "recipient_id": "",
                "transaction_type": "prelievo",
                "amount": 150.0,
                "location": "Torino",
                "payment_method": "carta fisica",
                "sender_iban": "IT36R2842854847916572043908",
                "recipient_iban": "IT22O9006594634442096506948136",
                "balance_after": 69.34,
                "description": "",
                "timestamp": "2025-11-17T01:07:01.657810",
                "is_fake_recipient": ""
            }
        }




