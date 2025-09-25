"""
Che168.com API schemas for Chinese car marketplace integration

This module defines the Pydantic models for handling data from che168.com API,
including car listings, brands, detailed specifications, and search filters.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class Che168Brand(BaseModel):
    """Car brand model from che168.com brands API"""
    bid: int = Field(..., description="Brand ID")
    name: str = Field(..., description="Brand name in Chinese")
    py: str = Field(..., description="Pinyin name")
    icon: Optional[str] = Field(None, description="Brand icon URL")
    sid: int = Field(default=0, description="Series ID")
    sname: str = Field(default="", description="Series name")
    sicon: str = Field(default="", description="Series icon")
    dtype: int = Field(default=0, description="Display type")
    url: Optional[str] = Field(None, description="Brand URL")
    price: str = Field(default="", description="Price info")
    on_sale_num: int = Field(default=0, description="Number of cars on sale")


class Che168BrandGroup(BaseModel):
    """Brand group model for alphabetical grouping"""
    letter: str = Field(..., description="Alphabetical letter")
    brand: List[Che168Brand] = Field(..., description="Brands starting with this letter")
    on_sale_num: int = Field(default=0, description="Total cars on sale for this group")


class Che168BrandsResponse(BaseModel):
    """Response model for brands API call"""
    returncode: int = Field(..., description="Return code (0 = success)")
    message: str = Field(..., description="Response message")
    result: Dict[str, Union[List[Che168BrandGroup], List[Che168Brand], bool]] = Field(..., description="Brands grouped by type or flags")


class Che168FilterItem(BaseModel):
    """Filter item model for search filters"""
    title: str = Field(..., description="Filter display title")
    subtitle: str = Field(default="", description="Filter subtitle")
    key: str = Field(..., description="Filter parameter key")
    value: str = Field(..., description="Filter value")
    icon: str = Field(default="", description="Filter icon URL")
    iconfocus: str = Field(default="", description="Focused icon URL")
    tag: str = Field(default="", description="Filter tag")
    viewtype: int = Field(default=100, description="Display type")
    iconwidth: int = Field(default=0, description="Icon width")
    badgetitle: str = Field(default="", description="Badge title")
    headbgurl: str = Field(default="", description="Header background URL")
    headsubbgurl: str = Field(default="", description="Header sub background URL")
    titlecolorfocus: str = Field(default="", description="Focused title color")
    titlecolor: str = Field(default="", description="Title color")
    tabtype: int = Field(default=0, description="Tab type")
    linkurl: str = Field(default="", description="Link URL")
    basevalue: str = Field(default="", description="Base value")
    dtype: int = Field(default=0, description="Data type")
    subvalue: str = Field(default="", description="Sub value")
    subspecname: str = Field(default="", description="Sub spec name")
    needreddot: int = Field(default=0, description="Red dot indicator")
    brandvalue: str = Field(default="", description="Brand value")
    brandname: str = Field(default="", description="Brand name")
    isgray: int = Field(default=0, description="Gray state")


class Che168CarListing(BaseModel):
    """Car listing model from search API"""
    infoid: int = Field(..., description="Car listing ID")
    carname: str = Field(..., description="Car name")
    carname_translated: Optional[str] = Field(None, description="Translated car name in Russian")
    cname: str = Field(..., description="City name")
    dealerid: int = Field(..., description="Dealer ID")
    mileage: str = Field(..., description="Mileage in km")
    cityid: int = Field(..., description="City ID")
    seriesid: int = Field(..., description="Series ID")
    specid: int = Field(..., description="Specification ID")
    sname: str = Field(default="", description="Series name")
    syname: str = Field(default="", description="Series year name")
    price: str = Field(..., description="Price in 万元 (10k CNY)")
    price_rub: Optional[float] = Field(None, description="Price in Russian Rubles")
    saveprice: str = Field(default="", description="Saved price")
    discount: str = Field(default="", description="Discount info")
    firstregyear: str = Field(..., description="First registration year")
    fromtype: int = Field(..., description="Source type")
    imageurl: str = Field(..., description="Main image URL")
    cartype: int = Field(..., description="Car type")
    bucket: int = Field(default=0, description="Bucket flag")
    isunion: int = Field(default=0, description="Union flag")


class Che168SearchFilters(BaseModel):
    """Search filters for che168 API"""
    pageindex: int = Field(default=1, description="Page index")
    pagesize: int = Field(default=12, description="Page size")
    appid: str = Field(default="2sc.m", description="App ID", alias="_appid")
    ishideback: int = Field(default=1, description="Hide back flag")
    srecom: int = Field(default=2, description="Recommendation flag")
    personalizedpush: int = Field(default=1, description="Personalized push flag")
    cid: int = Field(default=0, description="Category ID")
    pid: int = Field(default=0, description="Province ID")
    iscxcshowed: int = Field(default=-1, description="CXC show flag")
    filtertype: int = Field(default=0, description="Filter type")
    ssnew: int = Field(default=1, description="New flag")
    userid: int = Field(default=0, description="User ID")
    s_pid: int = Field(default=0, description="Search province ID")
    s_cid: int = Field(default=0, description="Search city ID")
    v: str = Field(default="11.41.5", description="Version")
    pvareaid: int = Field(default=111478, description="Area ID")
    scene_no: int = Field(default=12, description="Scene number")
    sort: int = Field(default=0, description="Sort type")

    # Main filter parameters
    service: Optional[str] = Field(None, description="Service type filter")
    brandid: Optional[int] = Field(None, description="Brand ID")
    seriesid: Optional[int] = Field(None, description="Series ID")
    seriesyearid: Optional[int] = Field(None, description="Series year ID")
    specid: Optional[str] = Field(None, description="Specification ID")
    price: Optional[str] = Field(None, description="Price range (e.g., '15-20')")
    agerange: Optional[str] = Field(None, description="Age range (e.g., '5-7')")
    mileage: Optional[str] = Field(None, description="Mileage range (e.g., '3-6')")
    fueltype: Optional[int] = Field(None, description="Fuel type (1=gasoline, 2=diesel, etc.)")
    displacement: Optional[str] = Field(None, description="Engine displacement (e.g., '1.1-1.6')")
    transmission: Optional[str] = Field(None, description="Transmission type")

    # Additional parameters that might be referenced in service
    existtags: Optional[str] = Field(None, description="Existing tags")
    testtype: Optional[str] = Field(None, description="Test type")

    class Config:
        extra = "allow"


class Che168SearchResponse(BaseModel):
    """Response model for car search API"""
    returncode: int = Field(..., description="Return code (0 = success)")
    message: str = Field(..., description="Response message")
    result: Dict[str, Any] = Field(..., description="Search results")

    # Parsed convenience properties
    cars: List[Che168CarListing] = Field(default_factory=list, description="List of car listings")
    total_count: int = Field(default=0, description="Total number of cars")
    page_count: int = Field(default=0, description="Total pages")
    current_page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=12, description="Page size")
    filters: List[Che168FilterItem] = Field(default_factory=list, description="Available filters")
    success: bool = Field(default=False, description="Request success status")


class Che168CarDetailItem(BaseModel):
    """Individual car detail item"""
    name: str = Field(..., description="Detail name in Chinese")
    name_translated: Optional[str] = Field(None, description="Translated name in Russian")
    content: str = Field(..., description="Detail content")
    countline: int = Field(default=0, description="Count line")


class Che168CarDetailSection(BaseModel):
    """Car detail section (engine, body, etc.)"""
    title: str = Field(..., description="Section title in Chinese")
    title_translated: Optional[str] = Field(None, description="Translated title in Russian")
    data: List[Che168CarDetailItem] = Field(..., description="Section data items")


class Che168CarDetailResponse(BaseModel):
    """Response model for car detail API"""
    returncode: int = Field(default=0, description="Return code")
    message: str = Field(default="", description="Response message")
    result: List[Che168CarDetailSection] = Field(default_factory=list, description="Car detail sections")
    success: bool = Field(default=False, description="Request success status")


class TranslationRequest(BaseModel):
    """Translation request model"""
    text: str = Field(..., description="Text to translate")
    target_language: str = Field(default="ru", description="Target language code")
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


class Che168FiltersResponse(BaseModel):
    """Response model for available filters"""
    brands: List[Che168Brand] = Field(default_factory=list, description="Available brands")
    price_ranges: List[Dict[str, str]] = Field(default_factory=list, description="Price ranges")
    age_ranges: List[Dict[str, str]] = Field(default_factory=list, description="Age ranges")
    mileage_ranges: List[Dict[str, str]] = Field(default_factory=list, description="Mileage ranges")
    fuel_types: List[Dict[str, Any]] = Field(default_factory=list, description="Fuel types")
    transmissions: List[Dict[str, str]] = Field(default_factory=list, description="Transmission types")
    displacements: List[Dict[str, str]] = Field(default_factory=list, description="Engine displacements")
    success: bool = Field(default=True, description="Request success status")


class Che168HealthResponse(BaseModel):
    """Health check response for che168 service"""
    status: str = Field(..., description="Service status")
    che168_api: Dict[str, Any] = Field(..., description="API status info")
    translation_service: Dict[str, Any] = Field(..., description="Translation service info")
    proxy_status: Dict[str, Any] = Field(..., description="Proxy status info")
    service: str = Field(default="che168_chinese_marketplace", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    error: Optional[str] = Field(None, description="Error message if any")


# =============================================================================
# LEGACY BRAVOMOTORS SCHEMAS (DEPRECATED - Use Che168 instead)
# =============================================================================


class BravoMotorsSearchFilters(BaseModel):
    """Legacy BravoMotors search filters - use Che168SearchFilters instead"""
    page: int = Field(default=1, description="Page number")
    per_page: int = Field(default=12, description="Items per page")
    translate: bool = Field(default=True, description="Enable translation")


class BravoMotorsCarListing(BaseModel):
    """Legacy BravoMotors car listing - use Che168CarListing instead"""
    id: str = Field(..., description="Car ID")
    title: str = Field(..., description="Car title")
    price: str = Field(..., description="Car price")
    image_url: str = Field(..., description="Car image URL")


class BravoMotorsSearchResponse(BaseModel):
    """Legacy BravoMotors search response - use Che168SearchResponse instead"""
    cars: List[BravoMotorsCarListing] = Field(default_factory=list, description="Car listings")
    total_count: int = Field(default=0, description="Total cars found")
    success: bool = Field(default=False, description="Request success")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class BravoMotorsCarDetailResponse(BaseModel):
    """Legacy BravoMotors car detail response - use Che168CarDetailResponse instead"""
    car: Optional[BravoMotorsCarListing] = Field(None, description="Car details")
    success: bool = Field(default=False, description="Request success")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class BravoMotorsFiltersResponse(BaseModel):
    """Legacy BravoMotors filters response - use Che168FiltersResponse instead"""
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Available filters")
    success: bool = Field(default=False, description="Request success")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata")