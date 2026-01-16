"""
User model with Pydantic validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserResidence(BaseModel):
    """User residence information."""
    
    city: str = Field(..., description="City name", min_length=1)
    lat: str = Field(..., description="Latitude", pattern=r"^-?\d+\.?\d*$")
    lng: str = Field(..., description="Longitude", pattern=r"^-?\d+\.?\d*$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "Paris",
                "lat": "48.8566",
                "lng": "2.3522"
            }
        }


class User(BaseModel):
    """User model with strict validation."""
    
    first_name: str = Field(..., description="First name", min_length=1, max_length=100)
    last_name: str = Field(..., description="Last name", min_length=1, max_length=100)
    birth_year: int = Field(..., description="Birth year", ge=1900, le=2024)
    salary: int = Field(..., description="Annual salary in euros", ge=0)
    job: str = Field(..., description="Job title", min_length=1, max_length=200)
    iban: str = Field(..., description="IBAN code", min_length=15, max_length=34)
    residence: UserResidence = Field(..., description="Residence information")
    
    @field_validator('iban')
    @classmethod
    def validate_iban(cls, v: str) -> str:
        """Validate IBAN format."""
        if not v or len(v) < 15:
            raise ValueError('IBAN must be at least 15 characters')
        # Basic IBAN format check (2 letters + 2 digits + alphanumeric)
        if not (v[:2].isalpha() and v[2:4].isdigit()):
            raise ValueError('IBAN must start with 2 letters followed by 2 digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "birth_year": 1990,
                "salary": 50000,
                "job": "Software Engineer",
                "iban": "FR7630006000011234567890189",
                "residence": {
                    "city": "Paris",
                    "lat": "48.8566",
                    "lng": "2.3522"
                }
            }
        }



