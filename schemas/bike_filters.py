"""
Pydantic schemas for bobaedream.co.kr bike filter system
Supports hierarchical filters with category, manufacturer, and model levels
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class FilterOption(BaseModel):
    """Single filter option with ID, name and count"""

    sno: str = Field(..., description="Filter option ID")
    cname: str = Field(..., description="Filter option name (Korean)")
    cnt: str = Field(..., description="Number of available items")
    chk: Optional[str] = Field(default="", description="Check status")


class FilterLevel(BaseModel):
    """Filter level response containing multiple options"""

    success: bool = Field(default=True)
    options: List[FilterOption] = Field(..., description="Available filter options")
    level: int = Field(
        ..., description="Filter level (0=category, 1=manufacturer, 3=model)"
    )
    meta: Dict[str, Any] = Field(default_factory=dict)


class FilterValues(BaseModel):
    """Available values for specific filter types"""

    fuel_types: List[FilterOption] = Field(
        default_factory=list, description="Available fuel types"
    )
    transmission_types: List[FilterOption] = Field(
        default_factory=list, description="Available transmission types"
    )
    colors: List[FilterOption] = Field(
        default_factory=list, description="Available colors"
    )
    selling_methods: List[FilterOption] = Field(
        default_factory=list, description="Available selling methods"
    )
    provinces: List[FilterOption] = Field(
        default_factory=list, description="Available provinces"
    )
    engine_sizes: List[FilterOption] = Field(
        default_factory=list, description="Available engine sizes"
    )
    price_ranges: List[FilterOption] = Field(
        default_factory=list, description="Available price ranges"
    )
    mileage_ranges: List[FilterOption] = Field(
        default_factory=list, description="Available mileage ranges"
    )
    year_ranges: List[FilterOption] = Field(
        default_factory=list, description="Available year ranges"
    )


class BikeSearchFilters(BaseModel):
    """Complete bike search filter parameters"""

    # Basic filters
    ifnew: Optional[str] = Field(default="N", description="N=Used, Y=New bikes")
    gubun: Optional[str] = Field(default=None, description="K=Korean, I=Imported")
    tab: Optional[str] = Field(
        default=None, description="2=Verified, 3=Premium, 4=Quick sale"
    )

    # Category and manufacturer filters
    ftype1: Optional[str] = Field(
        default=None, description="Category type (1=스쿠터, 2=비지니스, etc.)"
    )
    maker_no: Optional[str] = Field(default=None, description="Manufacturer ID")
    model_no: Optional[str] = Field(default=None, description="Model ID")
    level_no: Optional[str] = Field(default=None, description="Sub-model level")

    # Multi-select model variations
    level_no2: Optional[List[str]] = Field(
        default=None, description="Multiple model variations"
    )

    # Year filters - Updated with proper validation
    buy_year1_1: Optional[str] = Field(default=None, description="Year from (YYYY)")
    buy_year1_2: Optional[str] = Field(default="0", description="Month from (1-12)")
    buy_year2_1: Optional[str] = Field(default=None, description="Year to (YYYY)")
    buy_year2_2: Optional[str] = Field(default="0", description="Month to (1-12)")

    # Technical filters - Updated with validation
    fuel: Optional[str] = Field(
        default=None,
        description="Fuel type: 휘발유(gasoline), 전기(electric), 경유(diesel), 기타(other)",
    )
    method: Optional[str] = Field(
        default=None,
        description="Transmission: 3단리턴, 4단리턴, 5단리턴, 6단리턴, 7단리턴, 자동(automatic), etc.",
    )
    cc: Optional[str] = Field(
        default=None,
        description="Engine displacement: 50, 125, 250, 400, 600, 750, 900, 1000, 1300, 2000 (cc이하)",
    )

    # Price and mileage - Updated with validation
    price1: Optional[str] = Field(
        default=None,
        description="Price from (만원): 1, 50, 100, 200, 300, 400, 500, etc.",
    )
    price2: Optional[str] = Field(
        default=None, description="Price to (만원): 50, 100, 200, 300, 400, 500, etc."
    )
    km: Optional[str] = Field(
        default=None,
        description="Mileage filter: 1000(1천km이하), 5000(5천km이하), 10000(1만km이하), etc.",
    )

    # Location and seller - Updated
    addr_1: Optional[str] = Field(
        default=None,
        description="Province/City: 서울, 경기, 인천, 대전, 대구, 울산, 부산, 광주, 강원, etc.",
    )
    addr_2: Optional[str] = Field(
        default=None, description="District (depends on addr_1)"
    )
    sell_way: Optional[str] = Field(
        default=None,
        description="Selling method: 현금판매, 리스신규발생가능, 리스승계차량, 할부신규발생가능, etc.",
    )

    # Color filter - New
    car_color: Optional[str] = Field(
        default=None,
        description="Color: 흰색, 검정색, 빨강색, 파랑색, 은색, 회색, etc.",
    )

    # Special features - New (checkbox filters)
    chk_point: Optional[List[str]] = Field(
        default=None,
        description="Special features: 1=확인매물, 3=보증가능매물, 4=개인매물, 6=사진있는매물, 8=사이버매장등록매물",
    )

    # Display and sorting options
    order: Optional[str] = Field(
        default="update_time desc",
        description="Sort order: update_time desc/asc, car_price desc/asc, count desc, buy_year desc/asc, km desc/asc",
    )
    view_size: Optional[str] = Field(
        default="30", description="Items per page: 30, 50, 70"
    )

    # Search position (for form submission)
    x: Optional[str] = Field(default="35", description="Search button X coordinate")
    y: Optional[str] = Field(default="4", description="Search button Y coordinate")

    # Search text filters - New
    search_field: Optional[str] = Field(
        default=None,
        description="Search field type: car_name (매물명), user_name (판매자)",
    )
    search_str: Optional[str] = Field(
        default=None, description="Search string for car_name or user_name"
    )

    @validator("buy_year1_1", "buy_year2_1")
    def validate_year(cls, v):
        if v is not None:
            try:
                year = int(v)
                if year < 1950 or year > 2030:
                    raise ValueError("Year must be between 1950 and 2030")
            except ValueError:
                raise ValueError("Year must be a valid integer")
        return v

    @validator("buy_year1_2", "buy_year2_2")
    def validate_month(cls, v):
        if v is not None and v != "0":
            try:
                month = int(v)
                if month < 1 or month > 12:
                    raise ValueError("Month must be between 1 and 12")
            except ValueError:
                raise ValueError("Month must be a valid integer")
        return v

    @validator("price1", "price2")
    def validate_price(cls, v):
        if v is not None:
            try:
                price = int(v)
                if price < 0:
                    raise ValueError("Price must be positive")
            except ValueError:
                raise ValueError("Price must be a valid integer")
        return v

    @validator("view_size")
    def validate_view_size(cls, v):
        if v is not None and v not in ["30", "50", "70"]:
            raise ValueError("view_size must be 30, 50, or 70")
        return v


class FilterInfo(BaseModel):
    """Information about available filters"""

    categories: List[FilterOption] = Field(..., description="Available bike categories")
    manufacturers: List[FilterOption] = Field(
        ..., description="Available manufacturers"
    )
    filter_values: Optional[FilterValues] = Field(
        default=None, description="Available values for various filter types"
    )
    popular_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Popular filter combinations and metadata"
    )

    class Config:
        schema_extra = {
            "example": {
                "categories": [
                    {"sno": "1", "cname": "스쿠터", "cnt": "483", "chk": ""},
                    {"sno": "4", "cname": "레플리카", "cnt": "82", "chk": ""},
                    {"sno": "5", "cname": "네이키드", "cnt": "62", "chk": ""},
                ],
                "manufacturers": [
                    {"sno": "5", "cname": "혼다", "cnt": "206", "chk": ""},
                    {"sno": "6", "cname": "야마하", "cnt": "115", "chk": ""},
                    {"sno": "10", "cname": "대림", "cnt": "56", "chk": ""},
                ],
                "filter_values": {
                    "fuel_types": [
                        {"sno": "휘발유", "cname": "휘발유", "cnt": "800", "chk": ""},
                        {"sno": "전기", "cname": "전기", "cnt": "25", "chk": ""},
                    ],
                    "colors": [
                        {"sno": "흰색", "cname": "흰색", "cnt": "150", "chk": ""},
                        {"sno": "검정색", "cname": "검정색", "cnt": "120", "chk": ""},
                    ],
                },
                "popular_filters": {
                    "popular_categories": ["1", "4", "5"],
                    "popular_manufacturers": ["5", "6", "10", "11"],
                },
            }
        }


class FilterSearchParams(BaseModel):
    """Parameters for fetching specific filter level"""

    dep: int = Field(
        ...,
        description="Filter depth (0=category, 1=manufacturer, 2=models, 3=submodels)",
    )
    parval: Optional[str] = Field(default="", description="Parent value")
    selval: Optional[str] = Field(default="", description="Selected value")
    ifnew: str = Field(default="N", description="New/Used filter")
    level_no2: int = Field(default=0, description="Level number 2")

    class Config:
        schema_extra = {
            "example": {
                "dep": 1,
                "parval": "",
                "selval": "",
                "ifnew": "N",
                "level_no2": 0,
            }
        }
