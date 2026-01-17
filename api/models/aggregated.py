from typing import Optional, List
from pydantic import BaseModel, Field

from api.models.transaction import Transaction
from api.models.user import User
from api.models.email import Email
from api.models.sms import SMS
from api.models.location import Location

class UserWithTransactions(User):

    other_transactions: List[Transaction] = Field(
        default_factory=list,
        description="Other transactions involving this user's IBAN within ±3 hours of current transaction (excluding current transaction)"
    )

class AggregatedTransaction(BaseModel):

    transaction: Transaction = Field(..., description="Transaction data")

    sender: Optional[UserWithTransactions] = Field(None, description="Complete sender information with other transactions")
    recipient: Optional[UserWithTransactions] = Field(None, description="Complete recipient information with other transactions")

    sender_emails: List[Email] = Field(
        default_factory=list,
        description="Sender's emails"
    )
    recipient_emails: List[Email] = Field(
        default_factory=list,
        description="Recipient's emails"
    )
    sender_sms: List[SMS] = Field(
        default_factory=list,
        description="Sender's SMS messages"
    )
    recipient_sms: List[SMS] = Field(
        default_factory=list,
        description="Recipient's SMS messages"
    )

    sender_locations: List[Location] = Field(
        default_factory=list,
        description="Sender's locations near transaction date"
    )
    recipient_locations: List[Location] = Field(
        default_factory=list,
        description="Recipient's locations near transaction date"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "transaction": {
                    "transaction_id": "7634023d-5751-4940-a2c9-36b97274f366",
                    "sender_id": "PRZO-LTZE-7C1-CAS-0",
                    "recipient_id": "RCPT-XYZ-123",
                    "transaction_type": "bonifico",
                    "amount": 150.0,
                    "location": "Torino",
                    "payment_method": "virement",
                    "sender_iban": "IT36R2842854847916572043908",
                    "recipient_iban": "IT22O9006594634442096506948136",
                    "balance_after": 69.34,
                    "description": "Payment for services",
                    "timestamp": "2025-11-17T01:07:01.657810",
                    "is_fake_recipient": ""
                },
                "sender": {
                    "first_name": "Mario",
                    "last_name": "Rossi",
                    "birth_year": 1985,
                    "salary": 45000,
                    "job": "Software Engineer",
                    "iban": "IT36R2842854847916572043908",
                    "residence": {
                        "city": "Torino",
                        "lat": "45.0703",
                        "lng": "7.6869"
                    },
                    "other_transactions": []
                },
                "recipient": None,
                "sender_emails": [],
                "recipient_emails": [],
                "sender_sms": [],
                "recipient_sms": [],
                "sender_locations": [],
                "recipient_locations": []
            }
        }