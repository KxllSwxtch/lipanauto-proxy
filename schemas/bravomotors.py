"""
BravoMotors Schema Definitions
Data models for Chinese car marketplace integration via bravomotors.com
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class BravoMotorsCarListing(BaseModel):
    """Individual car listing from BravoMotors search results"""
    id: str = Field(..., description="Unique car identifier")
    title: str = Field(..., description="Car title in Chinese")
    title_translated: Optional[str] = Field(None, description="Car title translated to English")
    price: Optional[float] = Field(None, description="Car price")
    currency: str = Field(default="CNY", description="Price currency")
    year: Optional[int] = Field(None, description="Manufacturing year")
    mileage: Optional[int] = Field(None, description="Mileage in kilometers")
    location: Optional[str] = Field(None, description="Car location")
    images: List[str] = Field(default_factory=list, description="Car image URLs")
    thumbnail: Optional[str] = Field(None, description="Main thumbnail image")
    engine_volume: Optional[float] = Field(None, description="Engine volume in liters")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    drivetrain: Optional[str] = Field(None, description="Drivetrain type")
    color: Optional[str] = Field(None, description="Car color")
    manufacturer: Optional[str] = Field(None, description="Car manufacturer")
    model: Optional[str] = Field(None, description="Car model")
    url: Optional[str] = Field(None, description="Car detail page URL")
    source_platform: str = Field(default="bravomotors", description="Source platform")

    class Config:
        extra = "allow"


class BravoMotorsCarDetail(BaseModel):
    """Detailed car information"""
    id: str = Field(..., description="Unique car identifier")
    basic_info: Dict[str, Any] = Field(default_factory=dict, description="Basic car parameters")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications")
    features: List[str] = Field(default_factory=list, description="Car features list")
    condition_info: Dict[str, Any] = Field(default_factory=dict, description="Car condition details")
    seller_info: Dict[str, Any] = Field(default_factory=dict, description="Seller information")
    inspection_info: Dict[str, Any] = Field(default_factory=dict, description="Inspection details")

    class Config:
        extra = "allow"


class BravoMotorsSearchFilters(BaseModel):
    """Search filters for BravoMotors cars"""
    manufacturer: Optional[str] = Field(None, description="Car manufacturer")
    model: Optional[str] = Field(None, description="Car model")
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    year_min: Optional[int] = Field(None, description="Minimum year")
    year_max: Optional[int] = Field(None, description="Maximum year")
    mileage_min: Optional[int] = Field(None, description="Minimum mileage")
    mileage_max: Optional[int] = Field(None, description="Maximum mileage")
    fuel_type: Optional[str] = Field(None, description="Fuel type filter")
    transmission: Optional[str] = Field(None, description="Transmission filter")
    location: Optional[str] = Field(None, description="Location filter")
    sort_by: Optional[str] = Field(None, description="Sort criteria")
    page: int = Field(default=1, description="Page number")
    per_page: int = Field(default=20, description="Items per page")

    class Config:
        extra = "allow"


class BravoMotorsSearchResponse(BaseModel):
    """Response from BravoMotors search API"""
    success: bool = Field(..., description="Request success status")
    cars: List[BravoMotorsCarListing] = Field(default_factory=list, description="List of car listings")
    total_count: int = Field(default=0, description="Total number of cars found")
    page: int = Field(default=1, description="Current page number")
    per_page: int = Field(default=20, description="Items per page")
    total_pages: int = Field(default=0, description="Total number of pages")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied search filters")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        extra = "allow"


class BravoMotorsCarDetailResponse(BaseModel):
    """Response for individual car details"""
    success: bool = Field(..., description="Request success status")
    car: Optional[BravoMotorsCarDetail] = Field(None, description="Car details")
    translated_data: Optional[Dict[str, Any]] = Field(None, description="Translated content")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        extra = "allow"


class TranslationRequest(BaseModel):
    """Translation request model"""
    text: str = Field(..., description="Text to translate")
    target_language: str = Field(default="en", description="Target language code")
    source_language: str = Field(default="zh-cn", description="Source language code")
    type: str = Field(default="analysis", description="Translation type")


class TranslationResponse(BaseModel):
    """Translation response model"""
    original_text: str = Field(..., description="Original text")
    translated_text: str = Field(..., description="Translated text")
    source_language: str = Field(..., description="Source language")
    target_language: str = Field(..., description="Target language")
    type: str = Field(..., description="Translation type")
    is_static: bool = Field(default=False, description="Is static translation")
    is_cached: bool = Field(default=False, description="Is cached translation")
    success: bool = Field(..., description="Translation success status")


class BravoMotorsFiltersResponse(BaseModel):
    """Available filters for BravoMotors search"""
    manufacturers: List[Dict[str, str]] = Field(default_factory=list, description="Available manufacturers")
    models: List[Dict[str, str]] = Field(default_factory=list, description="Available models")
    years: List[int] = Field(default_factory=list, description="Available years")
    fuel_types: List[str] = Field(default_factory=list, description="Available fuel types")
    transmissions: List[str] = Field(default_factory=list, description="Available transmissions")
    locations: List[str] = Field(default_factory=list, description="Available locations")
    price_ranges: List[Dict[str, float]] = Field(default_factory=list, description="Suggested price ranges")

    class Config:
        extra = "allow"


# Service configuration models
class BravoMotorsServiceType(BaseModel):
    """Service type configuration"""
    name: str = Field(..., description="Service name")
    enabled: bool = Field(default=True, description="Service enabled status")
    translation_enabled: bool = Field(default=True, description="Translation enabled")
    rate_limit: int = Field(default=30, description="Requests per minute")

    class Config:
        extra = "allow"