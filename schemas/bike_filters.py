"""
Pydantic schemas for bobaedream.co.kr bike filter system
Supports hierarchical filters with category, manufacturer, and model levels
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


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


class BikeSearchFilters(BaseModel):
    """Complete bike search filter parameters"""

    # Basic filters
    ifnew: Optional[str] = Field(default="N", description="N=Used, Y=New bikes")
    gubun: Optional[str] = Field(default=None, description="K=Korean, I=Imported")

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

    # Year filters
    buy_year1_1: Optional[str] = Field(default=None, description="Year from")
    buy_year1_2: Optional[str] = Field(default="0", description="Year from type")
    buy_year2_1: Optional[str] = Field(default=None, description="Year to")
    buy_year2_2: Optional[str] = Field(default="0", description="Year to type")

    # Technical filters
    fuel: Optional[str] = Field(default=None, description="Fuel type")
    method: Optional[str] = Field(default=None, description="Transmission type")
    cc: Optional[str] = Field(default=None, description="Engine displacement")

    # Price and mileage
    price1: Optional[str] = Field(default=None, description="Price from (만원)")
    price2: Optional[str] = Field(default=None, description="Price to (만원)")
    km: Optional[str] = Field(default=None, description="Mileage filter")

    # Location and seller
    addr_1: Optional[str] = Field(default=None, description="Province/City")
    addr_2: Optional[str] = Field(default=None, description="District")
    sell_way: Optional[str] = Field(default=None, description="Selling method")

    # Display options
    order: Optional[str] = Field(default="update_time desc", description="Sort order")
    view_size: Optional[str] = Field(default="30", description="Items per page")
    car_color: Optional[str] = Field(default=None, description="Color filter")

    # Search position (for form submission)
    x: Optional[str] = Field(default="35", description="Search button X coordinate")
    y: Optional[str] = Field(default="4", description="Search button Y coordinate")


class FilterInfo(BaseModel):
    """Information about available filters"""

    categories: List[FilterOption] = Field(..., description="Available bike categories")
    manufacturers: List[FilterOption] = Field(
        ..., description="Available manufacturers"
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
                "popular_filters": {
                    "popular_categories": ["1", "4", "5"],
                    "popular_manufacturers": ["5", "6", "10", "11"],
                },
            }
        }


class FilterSearchParams(BaseModel):
    """Parameters for fetching specific filter level"""

    dep: int = Field(
        ..., description="Filter depth (0=category, 1=manufacturer, 3=model)"
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
