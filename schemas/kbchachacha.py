"""
KBChaChaCha API Schemas
Pydantic models for Korean car marketplace data structures
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class FuelType(str, Enum):
    """Fuel type codes for KBChaChaCha"""

    GASOLINE = "004001"  # 가솔린
    DIESEL = "004002"  # 디젤
    LPG = "004003"  # LPG
    HYBRID_LPG = "004004"  # 하이브리드(LPG)
    HYBRID_GASOLINE = "004005"  # 하이브리드(가솔린)
    HYBRID_DIESEL = "004011"  # 하이브리드(디젤)
    CNG = "004006"  # CNG
    ELECTRIC = "004007"  # 전기
    OTHER = "004008"  # 기타
    GASOLINE_LPG = "004010"  # 가솔린+LPG


class KBMaker(BaseModel):
    """Car manufacturer model"""

    countryCode: str = Field(description="Country code (수입/국산)")
    makerOrder: int = Field(description="Sort order")
    makerName: str = Field(description="Manufacturer name")
    makerCode: str = Field(description="Manufacturer unique code")
    count: int = Field(description="Number of cars available")


class KBMakersResponse(BaseModel):
    """Response for manufacturers list"""

    success: bool = True
    domestic: List[KBMaker] = Field(default=[], description="Domestic manufacturers")
    imported: List[KBMaker] = Field(default=[], description="Imported manufacturers")
    total_count: int = Field(description="Total manufacturers count")
    meta: Optional[Dict[str, Any]] = None


class KBCarModel(BaseModel):
    """Car model/class information"""

    useCode: str = Field(description="Usage type code")
    useCodeName: str = Field(description="Usage type name (대형, SUV, etc.)")
    countryOrder: int = Field(description="Country order")
    makerOrder: int = Field(description="Manufacturer order")
    makerName: str = Field(description="Manufacturer name")
    makerCode: str = Field(description="Manufacturer code")
    classOrder: int = Field(description="Class order")
    modelName: str = Field(description="Model name (그랜저, 아반떼, etc.)")
    classCode: str = Field(description="Class/model unique code")
    carCode: str = Field(description="Car code")


class KBModelsResponse(BaseModel):
    """Response for car models list"""

    success: bool = True
    models: List[KBCarModel] = Field(default=[], description="Car models")
    total_count: int = Field(description="Total models count")
    meta: Optional[Dict[str, Any]] = None


class KBGeneration(BaseModel):
    """Car generation/variant information"""

    codeModel: str = Field(description="Model code")
    nameModel: str = Field(description="Model full name")
    modelYear: Optional[str] = Field(description="Model year range")
    count: int = Field(description="Number of cars available")


class KBGenerationsResponse(BaseModel):
    """Response for car generations list"""

    success: bool = True
    generations: List[KBGeneration] = Field(default=[], description="Car generations")
    total_count: int = Field(description="Total generations count")
    meta: Optional[Dict[str, Any]] = None


class KBConfiguration(BaseModel):
    """Car configuration information"""

    codeModel: str = Field(description="Configuration code")
    nameModel: str = Field(description="Configuration name")
    count: int = Field(description="Number of cars available")


class KBTrim(BaseModel):
    """Car trim/grade information"""

    codeGrade: str = Field(description="Trim/grade code")
    nameGrade: str = Field(description="Trim/grade name")
    count: int = Field(description="Number of cars available")


class KBConfigsTrimsResponse(BaseModel):
    """Response for configurations and trims"""

    success: bool = True
    configurations: List[KBConfiguration] = Field(
        default=[], description="Car configurations"
    )
    trims: List[KBTrim] = Field(default=[], description="Car trims/grades")
    total_count: int = Field(description="Total configurations and trims count")
    meta: Optional[Dict[str, Any]] = None


class KBCarListing(BaseModel):
    """Individual car listing from search results"""

    carSeq: str = Field(description="Car sequence ID")
    title: str = Field(description="Car title/name")
    maker: str = Field(description="Manufacturer")
    model: str = Field(description="Model name")
    year: Optional[str] = Field(description="Model year")
    mileage: Optional[str] = Field(description="Mileage")
    location: Optional[str] = Field(description="Location")
    price: int = Field(description="Price in 만원")
    price_text: str = Field(description="Formatted price text")
    images: List[str] = Field(default=[], description="Car images URLs")
    tags: List[str] = Field(
        default=[], description="Car tags (실차주, 헛걸음보상, etc.)"
    )
    badges: List[str] = Field(default=[], description="Car badges (인증, 진단, etc.)")
    url: str = Field(description="Detail page URL")
    thumbnail_info: Optional[str] = Field(description="Thumbnail bottom info")


class KBSearchFilters(BaseModel):
    """Search filters for car listings"""

    page: int = Field(default=1, description="Page number")
    sort: str = Field(default="-orderDate", description="Sort order")
    makerCode: Optional[str] = Field(None, description="Manufacturer code")
    classCode: Optional[str] = Field(None, description="Model class code")
    carCode: Optional[str] = Field(None, description="Car code")
    modelCode: Optional[str] = Field(None, description="Model code")
    modelGradeCode: Optional[str] = Field(None, description="Model grade codes")

    # Year filter (연식)
    year_from: Optional[int] = Field(
        None, description="Minimum year (e.g., 2020)", ge=1990, le=2030
    )
    year_to: Optional[int] = Field(
        None, description="Maximum year (e.g., 2025)", ge=1990, le=2030
    )

    # Mileage filter (주행거리) - in kilometers
    mileage_from: Optional[int] = Field(None, description="Minimum mileage in km", ge=0)
    mileage_to: Optional[int] = Field(None, description="Maximum mileage in km", ge=0)

    # Price filter (가격) - in 만원 (10,000 KRW units)
    price_from: Optional[int] = Field(None, description="Minimum price in 만원", ge=0)
    price_to: Optional[int] = Field(None, description="Maximum price in 만원", ge=0)

    # Fuel type filter (연료)
    fuel_types: Optional[List[FuelType]] = Field(None, description="Fuel types list")

    # Legacy filters for backward compatibility
    priceFrom: Optional[int] = Field(None, description="Minimum price")
    priceTo: Optional[int] = Field(None, description="Maximum price")
    yearFrom: Optional[int] = Field(None, description="Minimum year")
    yearTo: Optional[int] = Field(None, description="Maximum year")
    mileageFrom: Optional[int] = Field(None, description="Minimum mileage")
    mileageTo: Optional[int] = Field(None, description="Maximum mileage")


class KBSearchResponse(BaseModel):
    """Response for car search with listings"""

    success: bool = True
    listings: List[KBCarListing] = Field(default=[], description="Car listings")
    total_count: int = Field(description="Total listings found")
    page: int = Field(description="Current page")
    has_next_page: bool = Field(description="Whether more pages available")
    star_pick_count: int = Field(default=0, description="KB Star Pick count")
    certified_count: int = Field(default=0, description="Certified/diagnosed count")
    meta: Optional[Dict[str, Any]] = None


class KBDefaultListResponse(BaseModel):
    """Response for default car listings"""

    success: bool = True
    star_pick_listings: List[KBCarListing] = Field(
        default=[], description="KB Star Pick cars"
    )
    certified_listings: List[KBCarListing] = Field(
        default=[], description="Certified/diagnosed cars"
    )
    total_count: int = Field(description="Total listings count")
    meta: Optional[Dict[str, Any]] = None


class KBCarSpecification(BaseModel):
    """Car technical specifications"""

    license_plate: Optional[str] = Field(None, description="License plate number")
    model_year: Optional[str] = Field(
        None, description="Model year (e.g., 12년06월(13년형))"
    )
    mileage: Optional[str] = Field(None, description="Mileage (e.g., 124,413km)")
    fuel_type: Optional[str] = Field(None, description="Fuel type (e.g., 가솔린)")
    transmission: Optional[str] = Field(
        None, description="Transmission type (e.g., 오토)"
    )
    car_class: Optional[str] = Field(None, description="Car class (e.g., 준중형)")
    engine_displacement: Optional[str] = Field(
        None, description="Engine displacement (e.g., 1,591cc)"
    )
    color: Optional[str] = Field(None, description="Car color (e.g., 흰색)")
    fuel_efficiency: Optional[str] = Field(None, description="Fuel efficiency rating")
    drivetrain: Optional[str] = Field(None, description="Drivetrain type")
    seating_capacity: Optional[str] = Field(None, description="Number of seats")


class KBCarPricing(BaseModel):
    """Car pricing information"""

    current_price: int = Field(description="Current selling price in KRW")
    current_price_text: str = Field(
        description="Formatted current price (e.g., 520만원)"
    )
    market_price_range: Optional[str] = Field(
        None, description="Market price range (e.g., 408~607만원)"
    )
    market_price_confidence: Optional[str] = Field(
        None, description="Market price confidence indicator"
    )
    residual_value_percentage: Optional[str] = Field(
        None, description="Residual value percentage"
    )
    new_car_price: Optional[str] = Field(None, description="Original new car price")


class KBCarCondition(BaseModel):
    """Car condition and inspection information"""

    accident_history: Optional[str] = Field(None, description="Accident history status")
    inspection_status: Optional[str] = Field(None, description="KB inspection status")
    warranty_info: Optional[str] = Field(None, description="Warranty information")
    mileage_analysis: Optional[str] = Field(None, description="Mileage analysis result")
    performance_check: Optional[str] = Field(
        None, description="Performance check status"
    )


class KBCarOptions(BaseModel):
    """Car options and features"""

    safety_options: List[str] = Field(default=[], description="Safety options")
    convenience_options: List[str] = Field(
        default=[], description="Convenience options"
    )
    exterior_options: List[str] = Field(default=[], description="Exterior options")
    interior_options: List[str] = Field(default=[], description="Interior options")
    multimedia_options: List[str] = Field(default=[], description="Multimedia options")
    other_options: List[str] = Field(default=[], description="Other options")


class KBSellerInfo(BaseModel):
    """Seller information"""

    seller_name: Optional[str] = Field(None, description="Seller name")
    seller_type: Optional[str] = Field(None, description="Seller type (딜러, 개인 등)")
    contact_info: Optional[str] = Field(None, description="Contact information")
    location: Optional[str] = Field(None, description="Seller location")
    business_hours: Optional[str] = Field(None, description="Business hours")
    seller_description: Optional[str] = Field(None, description="Seller description")


class KBCarDetailResponse(BaseModel):
    """Detailed car information response"""

    success: bool = True
    car_seq: str = Field(description="Car sequence ID")

    # Basic information
    title: str = Field(description="Car title/name")
    brand: str = Field(description="Car brand")
    model: str = Field(description="Car model")
    full_name: str = Field(description="Full car name")

    # Images
    images: List[str] = Field(default=[], description="Car images URLs")
    main_image: Optional[str] = Field(None, description="Main image URL")

    # Technical specifications
    specifications: KBCarSpecification = Field(description="Technical specifications")

    # Pricing
    pricing: KBCarPricing = Field(description="Pricing information")

    # Condition
    condition: KBCarCondition = Field(description="Car condition and inspection")

    # Options
    options: KBCarOptions = Field(description="Car options and features")

    # Seller
    seller: KBSellerInfo = Field(description="Seller information")

    # Additional info
    description: Optional[str] = Field(None, description="Car description")
    tags: List[str] = Field(default=[], description="Car tags")
    badges: List[str] = Field(default=[], description="Car badges")

    # URL
    detail_url: str = Field(description="Detail page URL")

    # Metadata
    meta: Optional[Dict[str, Any]] = None
