"""
Che168 API Schemas
Pydantic models for Chinese car marketplace data structures
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Che168ServiceType(str, Enum):
    """Service type codes for Che168"""

    ALL = ""  # 全部
    PLATFORM_SUBSIDY = "410"  # 平台补贴
    LIVE_PURCHASE = "480"  # 直播购
    DEALER_DIRECT = "27"  # 4S直卖
    NEW_ENERGY = "430"  # 新能源
    MEMBER_DEALER = "40"  # 会员商家
    SHOP = "306"  # 店铺
    INSTALLMENT = "330"  # 分期


class Che168CarTag(BaseModel):
    """Car tag/badge information"""

    title: str = Field(description="Tag title")
    bg_color: str = Field(description="Background color")
    bg_color_end: str = Field(description="Background end color")
    font_color: str = Field(description="Font color")
    border_color: str = Field(description="Border color")
    bg_color_direction: int = Field(description="Background direction")
    stype: str = Field(description="Style type")
    sort: int = Field(description="Sort order")
    icon: str = Field(description="Icon URL")
    url: str = Field(description="Link URL")
    image: str = Field(description="Image URL")
    imgheight: int = Field(description="Image height")
    imgwidth: int = Field(description="Image width")


class Che168CarTags(BaseModel):
    """Car tags container"""

    p1: List[Che168CarTag] = Field(default=[], description="Primary tags")
    p2: List[Che168CarTag] = Field(default=[], description="Secondary tags")
    p3: List[Che168CarTag] = Field(default=[], description="Tertiary tags")


class Che168CPCInfo(BaseModel):
    """CPC (Cost Per Click) advertising information"""

    adid: int = Field(description="Ad ID")
    platform: int = Field(description="Platform ID")
    cpctype: int = Field(description="CPC type")
    position: int = Field(description="Position")
    encryptinfo: str = Field(description="Encrypted info")


class Che168Consignment(BaseModel):
    """Consignment information"""

    isconsignment: int = Field(description="Is consignment (0/1)")
    endtime: int = Field(description="End time timestamp")
    imurl: str = Field(description="IM URL")
    isyouxin: int = Field(description="Is Youxin (0/1)")
    citytype: int = Field(description="City type")


class Che168CarListing(BaseModel):
    """Individual car listing from Che168"""

    infoid: int = Field(description="Car listing ID")
    carname: str = Field(description="Car name/model")
    cname: str = Field(description="City name")
    dealerid: int = Field(description="Dealer ID")
    mileage: str = Field(description="Mileage (万公里)")
    cityid: int = Field(description="City ID")
    seriesid: int = Field(description="Car series ID")
    specid: int = Field(description="Specification ID")
    sname: str = Field(description="Series name")
    syname: str = Field(description="Specification name")
    price: str = Field(description="Price (万元)")
    saveprice: str = Field(description="Save price")
    discount: str = Field(description="Discount")
    firstregyear: str = Field(description="First registration year")
    fromtype: int = Field(description="Source type")
    imageurl: str = Field(description="Main image URL")
    cartype: int = Field(description="Car type")
    bucket: int = Field(description="Bucket")
    isunion: int = Field(description="Is union (0/1)")
    isoutsite: int = Field(description="Is out site (0/1)")
    videourl: str = Field(description="Video URL")
    car_level: int = Field(description="Car level")
    dealer_level: str = Field(description="Dealer level info")
    downpayment: str = Field(description="Down payment (万元)")
    url: str = Field(description="Car detail URL")
    position: int = Field(description="Position in results")
    isnewly: int = Field(description="Is newly listed (0/1)")
    kindname: str = Field(description="Kind name")
    usc_adid: int = Field(description="USC ad ID")
    particularactivity: int = Field(description="Particular activity")
    livestatus: int = Field(description="Live status")
    stra: str = Field(description="Strategy info JSON")
    springid: str = Field(description="Spring ID")
    followcount: int = Field(description="Follow count")
    cxctype: int = Field(description="CXC type")
    isfqtj: int = Field(description="Is FQTJ (0/1)")
    isrelivedbuy: int = Field(description="Is relived buy (0/1)")
    photocount: int = Field(description="Photo count")
    isextwarranty: int = Field(description="Is extended warranty (0/1)")
    offertype: int = Field(description="Offer type")
    cpcinfo: Che168CPCInfo = Field(description="CPC information")
    displacement: str = Field(description="Engine displacement")
    environmental: str = Field(description="Environmental standard")
    liveurl: str = Field(description="Live URL")
    imuserid: str = Field(description="IM user ID")
    consignment: Che168Consignment = Field(description="Consignment info")
    pv_extstr: str = Field(description="PV extension string")
    act_discount: str = Field(description="Activity discount")
    cartags: Che168CarTags = Field(description="Car tags")


class Che168ServiceOption(BaseModel):
    """Service filter option"""

    title: str = Field(description="Service title")
    subtitle: str = Field(description="Service subtitle")
    key: str = Field(description="Service key")
    value: str = Field(description="Service value")
    icon: str = Field(description="Icon URL")
    iconfocus: str = Field(description="Focused icon URL")
    tag: str = Field(description="Tag")
    viewtype: int = Field(description="View type")
    iconwidth: int = Field(description="Icon width")
    badgetitle: str = Field(description="Badge title")
    headbgurl: str = Field(description="Header background URL")
    headsubbgurl: str = Field(description="Header sub background URL")
    titlecolorfocus: str = Field(description="Title color focus")
    titlecolor: str = Field(description="Title color")
    tabtype: int = Field(description="Tab type")
    linkurl: str = Field(description="Link URL")
    basevalue: str = Field(description="Base value")
    dtype: int = Field(description="Data type")
    subvalue: str = Field(description="Sub value")
    subspecname: str = Field(description="Sub spec name")
    needreddot: int = Field(description="Need red dot (0/1)")
    brandvalue: str = Field(description="Brand value")
    brandname: str = Field(description="Brand name")
    isgray: int = Field(description="Is gray (0/1)")


class Che168SearchResult(BaseModel):
    """Search result container"""

    totalcount: int = Field(description="Total number of cars")
    pagesize: int = Field(description="Page size")
    pageindex: int = Field(description="Current page index")
    pagecount: int = Field(description="Total page count")
    queryid: str = Field(description="Query ID")
    styletype: int = Field(description="Style type")
    showtype: int = Field(description="Show type")
    service: List[Che168ServiceOption] = Field(description="Service filters")
    subservice: List[Any] = Field(description="Sub service filters")
    filters: List[Any] = Field(description="Additional filters")
    carlist: List[Che168CarListing] = Field(description="Car listings")


class Che168ApiResponse(BaseModel):
    """Main API response wrapper"""

    returncode: int = Field(description="Return code (0 = success)")
    message: str = Field(description="Response message")
    result: Che168SearchResult = Field(description="Search results")


class Che168SearchResponse(BaseModel):
    """Standardized search response"""

    success: bool = True
    cars: List[Che168CarListing] = Field(default=[], description="Car listings")
    pagination: Dict[str, Any] = Field(description="Pagination info")
    service_filters: List[Che168ServiceOption] = Field(default=[], description="Available service filters")
    total_count: int = Field(description="Total cars count")
    meta: Optional[Dict[str, Any]] = None


class Che168Brand(BaseModel):
    """Individual car brand information"""

    bid: int = Field(description="Brand ID")
    name: str = Field(description="Brand name")
    py: str = Field(description="Pinyin abbreviation")
    icon: str = Field(description="Brand icon URL")
    price: str = Field(description="Starting price")
    on_sale_num: int = Field(description="Number of cars on sale")
    dtype: int = Field(default=0, description="Data type")
    url: str = Field(default="", description="Brand URL")


class Che168BrandGroup(BaseModel):
    """Brand group organized by letter"""

    letter: str = Field(description="First letter of brand names")
    brand: List[Che168Brand] = Field(description="List of brands starting with this letter")


class Che168BrandsApiResponse(BaseModel):
    """API response for brands endpoint"""

    returncode: int = Field(description="Return code (0 = success)")
    message: str = Field(description="Response message")
    result: Dict[str, List[Che168BrandGroup]] = Field(description="Brands grouped by letter")


class Che168BrandsResponse(BaseModel):
    """Standardized brands response"""

    success: bool = True
    brands: List[Che168Brand] = Field(default=[], description="All brands flattened")
    brand_groups: List[Che168BrandGroup] = Field(default=[], description="Brands grouped by letter")
    total_brands: int = Field(description="Total number of brands")
    meta: Optional[Dict[str, Any]] = None


class Che168ModelFilter(BaseModel):
    """Model filter extracted from search response"""

    title: str = Field(description="Model name")
    key: str = Field(description="Filter key (typically 'seriesid')")
    value: str = Field(description="Series ID")
    dtype: int = Field(description="Data type")
    subvalue: str = Field(default="", description="Sub values (spec IDs)")
    subspecname: str = Field(default="", description="Sub spec name")


class Che168ModelsResponse(BaseModel):
    """Response for models endpoint"""

    success: bool = True
    models: List[Che168ModelFilter] = Field(default=[], description="Available models")
    brand_id: int = Field(description="Brand ID these models belong to")
    total_models: int = Field(description="Total number of models")
    meta: Optional[Dict[str, Any]] = None


class Che168YearFilter(BaseModel):
    """Year filter extracted from search response"""

    title: str = Field(description="Year title (e.g., '2025款')")
    key: str = Field(description="Filter key (typically 'seriesyearid')")
    value: str = Field(description="Series year ID")
    dtype: int = Field(description="Data type")
    subvalue: str = Field(default="", description="Sub values (spec IDs)")
    subspecname: str = Field(default="", description="Sub spec name")


class Che168YearsResponse(BaseModel):
    """Response for years endpoint"""

    success: bool = True
    years: List[Che168YearFilter] = Field(default=[], description="Available years")
    brand_id: int = Field(description="Brand ID")
    series_id: int = Field(description="Series ID these years belong to")
    total_years: int = Field(description="Total number of years")
    meta: Optional[Dict[str, Any]] = None


class Che168SearchFilters(BaseModel):
    """Search filters for Che168 API"""

    pageindex: int = Field(default=1, description="Page number")
    pagesize: int = Field(default=10, description="Page size (max 20)")
    service: Optional[str] = Field(None, description="Service type filter")
    ishideback: int = Field(default=1, description="Hide back flag")
    srecom: int = Field(default=0, description="Recommendation flag")
    personalizedpush: int = Field(default=1, description="Personalized push")
    cid: int = Field(default=0, description="Category ID")
    iscxcshowed: int = Field(default=-1, description="CXC showed flag")
    scene_no: int = Field(default=12, description="Scene number")
    existtags: str = Field(default="2,5,7", description="Existing tags")
    pid: int = Field(default=0, description="PID")
    testtype: str = Field(default="X", description="Test type")
    test102223: str = Field(default="X", description="Test 102223")
    testnewcarspecid: str = Field(default="X", description="Test new car spec ID")
    test102797: str = Field(default="X", description="Test 102797")
    filtertype: int = Field(default=0, description="Filter type")
    ssnew: int = Field(default=1, description="SS new flag")
    userid: int = Field(default=0, description="User ID")
    s_pid: int = Field(default=0, description="S PID")
    s_cid: int = Field(default=0, description="S CID")
    appid: str = Field(default="2sc.m", description="App ID", alias="_appid")
    v: str = Field(default="11.41.5", description="Version")

    # New filter parameters for brand/model/year filtering
    brandid: Optional[int] = Field(None, description="Brand ID filter")
    seriesid: Optional[int] = Field(None, description="Series (model) ID filter")
    seriesyearid: Optional[int] = Field(None, description="Series year ID filter")
    specid: Optional[str] = Field(None, description="Specification IDs (comma-separated)")
    sort: Optional[int] = Field(None, description="Sort order (0=default, 1=price asc, 2=price desc, 3=mileage, 4=age, 5=time)")


class Che168CarDetailResponse(BaseModel):
    """Car detail response"""

    success: bool = True
    car: Optional[Che168CarListing] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class Che168FiltersResponse(BaseModel):
    """Available filters response"""

    success: bool = True
    service_types: List[Che168ServiceOption] = Field(default=[], description="Service type filters")
    meta: Optional[Dict[str, Any]] = None