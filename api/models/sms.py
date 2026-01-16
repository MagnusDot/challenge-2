"""
SMS model with Pydantic validation.
"""

from pydantic import BaseModel, Field


class SMS(BaseModel):
    """SMS message model with strict validation."""
    
    id_user: str = Field(..., description="User identifier", min_length=1)
    sms: str = Field(..., description="SMS content", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_user": "John_Doe",
                "sms": "From: Service\nTo: +1234567890\nDate: 2025-12-13 10:00:00\nMessage: Hello!"
            }
        }



