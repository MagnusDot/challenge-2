"""
Pydantic models for API tool inputs validation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class GetUsersToolInput(BaseModel):
    """Input model for get_users tool."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")
    iban: Optional[str] = Field(None, description="Filter by IBAN")
    city: Optional[str] = Field(None, description="Filter by city")
    first_name: Optional[str] = Field(None, description="Filter by first name")
    last_name: Optional[str] = Field(None, description="Filter by last name")
    job: Optional[str] = Field(None, description="Filter by job title")
    min_salary: Optional[int] = Field(None, ge=0, description="Minimum salary")
    max_salary: Optional[int] = Field(None, ge=0, description="Maximum salary")


class GetTransactionsToolInput(BaseModel):
    """Input model for get_transactions tool."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")
    transaction_id: Optional[str] = Field(None, description="Filter by transaction ID")
    sender_id: Optional[str] = Field(None, description="Filter by sender ID")
    recipient_id: Optional[str] = Field(None, description="Filter by recipient ID")
    transaction_type: Optional[str] = Field(None, description="Filter by type")
    location: Optional[str] = Field(None, description="Filter by location")
    payment_method: Optional[str] = Field(None, description="Filter by payment method")
    min_amount: Optional[float] = Field(None, ge=0, description="Minimum amount")
    max_amount: Optional[float] = Field(None, ge=0, description="Maximum amount")
    is_fraud: Optional[bool] = Field(None, description="Filter by fraud status")
    sort_by: Optional[str] = Field(None, description="Sort by field")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc/desc)")


class GetLocationsToolInput(BaseModel):
    """Input model for get_locations tool."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")
    biotag: Optional[str] = Field(None, description="Filter by biotag")
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601)")
    min_lat: Optional[float] = Field(None, ge=-90, le=90, description="Minimum latitude")
    max_lat: Optional[float] = Field(None, ge=-90, le=90, description="Maximum latitude")
    min_lng: Optional[float] = Field(None, ge=-180, le=180, description="Minimum longitude")
    max_lng: Optional[float] = Field(None, ge=-180, le=180, description="Maximum longitude")


class GetSmsToolInput(BaseModel):
    """Input model for get_sms tool."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")
    id_user: Optional[str] = Field(None, description="Filter by user ID")
    search: Optional[str] = Field(None, description="Search in SMS content")
    contains: Optional[str] = Field(None, description="Filter SMS containing text")


class GetEmailsToolInput(BaseModel):
    """Input model for get_emails tool."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(5, ge=1, le=50, description="Maximum records to return")
    search: Optional[str] = Field(None, description="Search in email content")
    from_contains: Optional[str] = Field(None, description="Filter by From field")
    to_contains: Optional[str] = Field(None, description="Filter by To field")
    subject_contains: Optional[str] = Field(None, description="Filter by Subject")
    is_html: Optional[bool] = Field(None, description="Filter HTML emails")

