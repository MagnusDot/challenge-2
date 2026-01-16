"""
Email model with Pydantic validation.
"""

from pydantic import BaseModel, Field


class Email(BaseModel):
    """Email message model with strict validation."""
    
    mail: str = Field(..., description="Full email content (RFC 822 format)", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "mail": "From: sender@example.com\nTo: recipient@example.com\nSubject: Test\n\nContent"
            }
        }



