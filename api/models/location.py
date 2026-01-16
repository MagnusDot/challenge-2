"""
Location model with Pydantic validation.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Location tracking model with strict validation."""
    
    biotag: str = Field(..., description="User biotag identifier", min_length=1)
    datetime: str = Field(..., description="Timestamp (ISO 8601)")
    lat: float = Field(..., description="Latitude", ge=-90, le=90)
    lng: float = Field(..., description="Longitude", ge=-180, le=180)
    
    @field_validator('datetime')
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        """Validate ISO 8601 datetime."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('datetime must be valid ISO 8601 format')
        return v
    
    @field_validator('biotag')
    @classmethod
    def validate_biotag(cls, v: str) -> str:
        """Validate biotag format."""
        if not v or len(v) < 3:
            raise ValueError('biotag must be at least 3 characters')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "biotag": "SNDV-BRYN-7C8-MUN-0",
                "datetime": "2027-01-01T15:16:46",
                "lat": 42.2693,
                "lng": -88.0296
            }
        }

