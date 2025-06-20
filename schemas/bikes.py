"""
Pydantic schemas for bike data structures from bobaedream.co.kr
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BikeItem(BaseModel):
    """Single bike listing from bobaedream.co.kr"""

    id: str = Field(..., description="Bike ID from URL")
    title: str = Field(..., description="Bike title/model")
    price: Optional[str] = Field(None, description="Price in Korean Won")
    year: Optional[str] = Field(None, description="Manufacturing year")
    mileage: Optional[str] = Field(None, description="Mileage in km")
    transmission: Optional[str] = Field(None, description="Transmission type")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    color: Optional[str] = Field(None, description="Color")
    engine_cc: Optional[str] = Field(None, description="Engine displacement")
    seller_type: Optional[str] = Field(None, description="Seller type (개인/업체)")
    location: Optional[str] = Field(None, description="Location")
    image_url: Optional[str] = Field(None, description="Main image URL")
    detail_url: Optional[str] = Field(None, description="Detail page URL")


class BikeDetail(BaseModel):
    """Detailed bike information from detail page"""

    # Basic Information
    id: str = Field(..., description="Bike ID")
    title: str = Field(..., description="Full bike model name")
    price: str = Field(..., description="Selling price")

    # Technical Specifications
    year: Optional[str] = Field(None, description="Year and month of manufacture")
    mileage: Optional[str] = Field(None, description="Mileage in km")
    engine_cc: Optional[str] = Field(None, description="Engine displacement")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    color: Optional[str] = Field(None, description="Color")
    bike_type: Optional[str] = Field(None, description="Bike type (스쿠터, etc)")
    license_plate: Optional[str] = Field(None, description="License plate number")

    # Condition Information
    accident_history: Optional[str] = Field(None, description="Accident history")
    tuning_status: Optional[str] = Field(None, description="Tuning status")
    purchase_route: Optional[str] = Field(None, description="Purchase route")
    warranty: Optional[str] = Field(None, description="A/S warranty status")

    # Documents and Sales Method
    documents: List[str] = Field(
        default_factory=list, description="Available documents"
    )
    payment_methods: List[str] = Field(
        default_factory=list, description="Available payment methods"
    )

    # Seller Information
    seller_name: Optional[str] = Field(None, description="Seller name")
    seller_type: Optional[str] = Field(None, description="Seller type (개인/업체)")
    seller_phone: Optional[str] = Field(None, description="Seller phone number")
    seller_mobile: Optional[str] = Field(None, description="Seller mobile number")
    seller_email: Optional[str] = Field(None, description="Seller email")
    seller_location: Optional[str] = Field(None, description="Seller location")
    seller_address: Optional[str] = Field(None, description="Detailed address")
    company_name: Optional[str] = Field(None, description="Company name if business")
    business_number: Optional[str] = Field(
        None, description="Business registration number"
    )

    # Images
    main_image: Optional[str] = Field(None, description="Main image URL")
    images: List[str] = Field(default_factory=list, description="All image URLs")
    image_count: Optional[int] = Field(None, description="Total number of images")

    # Metadata
    registration_date: Optional[str] = Field(None, description="Registration date")
    view_count: Optional[int] = Field(None, description="View count")
    today_views: Optional[int] = Field(None, description="Today's views")
    favorites_count: Optional[int] = Field(None, description="Number of favorites")
    seller_total_listings: Optional[int] = Field(
        None, description="Seller's total listings"
    )

    # Location and Navigation
    navi_address: Optional[str] = Field(None, description="Navigation address")
    public_transport: Optional[str] = Field(None, description="Public transport info")


class BikeSearchParams(BaseModel):
    """Search parameters for bike listings"""

    ifnew: str = Field(default="N", description="N=Used, Y=New")
    gubun: Optional[str] = Field(None, description="K=Korean, I=Imported")
    tab: Optional[str] = Field(None, description="2=Verified, 3=Premium, 4=Quick sale")
    page: Optional[int] = Field(default=1, description="Page number")
    sort: Optional[str] = Field(None, description="Sort order")


class BikeSearchResponse(BaseModel):
    """Response structure for bike search results"""

    success: bool = Field(..., description="Operation success status")
    bikes: List[BikeItem] = Field(default_factory=list, description="List of bikes")
    total_count: Optional[int] = Field(None, description="Total number of results")
    current_page: Optional[int] = Field(None, description="Current page number")
    total_pages: Optional[int] = Field(None, description="Total number of pages")
    meta: dict = Field(default_factory=dict, description="Additional metadata")


class BikeDetailResponse(BaseModel):
    """Response structure for bike detail"""

    success: bool = Field(..., description="Operation success status")
    bike: Optional[BikeDetail] = Field(None, description="Detailed bike information")
    meta: dict = Field(default_factory=dict, description="Additional metadata")
