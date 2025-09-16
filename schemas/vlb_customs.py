"""
VLB Broker Customs Calculation Schemas
Pydantic models for VLB broker customs duty calculations
"""

from typing import Optional
from pydantic import BaseModel, Field


class VLBCustomsRequest(BaseModel):
    """Request model for VLB customs calculation"""

    strategy: str = Field(default="moto_japan", description="Calculation strategy")
    price: int = Field(..., description="Vehicle price in source currency")
    currency: str = Field(default="KRW", description="Price currency (KRW/USD/EUR)")
    year: int = Field(..., description="Vehicle manufacturing year")
    engine_volume: int = Field(..., description="Engine displacement in CC")
    vehicle_type: str = Field(default="b", description="Vehicle type (b=bike)")

    # Additional parameters for API compatibility
    html: int = Field(default=1, description="Request HTML response")
    nt: int = Field(default=1, description="New calculation flag")
    p: int = Field(default=1, description="Private person flag")
    fiz: int = Field(default=1, description="Physical person flag")
    marka_j: str = Field(default="", description="Japanese brand")
    model_j: str = Field(default="", description="Japanese model")
    marka_k: str = Field(default="", description="Korean brand")
    model_k: str = Field(default="", description="Korean model")
    emin: int = Field(default=1, description="Engine minimum flag")
    ptype: int = Field(default=1, description="Person type")
    ptype_e: int = Field(default=1, description="Person type extended")


class VLBCustomsBreakdown(BaseModel):
    """Customs breakdown from VLB response"""

    customs_processing_fee: int = Field(..., description="Customs processing fee in RUB")
    duty: int = Field(..., description="Import duty in RUB")
    duty_rate: Optional[str] = Field(None, description="Duty rate percentage")
    vat: int = Field(..., description="VAT in RUB")
    vat_rate: Optional[str] = Field(None, description="VAT rate percentage")
    total: int = Field(..., description="Total customs cost in RUB")


class VLBCustomsResponse(BaseModel):
    """Response model for VLB customs calculation"""

    success: bool = Field(..., description="Calculation success status")
    customs: Optional[VLBCustomsBreakdown] = Field(None, description="Customs breakdown")
    currency_rates: Optional[dict] = Field(None, description="Exchange rates used")
    error: Optional[str] = Field(None, description="Error message if failed")
    cached: bool = Field(default=False, description="Whether result was cached")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")


class TurnkeyPriceComponents(BaseModel):
    """Components for turnkey price calculation"""

    base_price_krw: int = Field(..., description="Base bike price in KRW")
    base_price_rub: int = Field(..., description="Base bike price in RUB")
    markup_10_percent: int = Field(..., description="10% markup in RUB")
    documents_fee: int = Field(default=60000, description="Documents fee in RUB")
    korea_logistics_krw: int = Field(default=520000, description="Korea logistics in KRW")
    korea_logistics_rub: int = Field(..., description="Korea logistics in RUB")
    vladivostok_logistics_usd: int = Field(default=550, description="Vladivostok logistics in USD")
    vladivostok_logistics_rub: int = Field(..., description="Vladivostok logistics in RUB")
    packaging_krw: int = Field(default=500000, description="Packaging in KRW")
    packaging_rub: int = Field(..., description="Packaging in RUB")
    customs_total: int = Field(..., description="Total customs in RUB")


class TurnkeyPriceResponse(BaseModel):
    """Response model for turnkey price calculation"""

    success: bool = Field(..., description="Calculation success status")
    bike_id: str = Field(..., description="Bike ID")
    components: Optional[TurnkeyPriceComponents] = Field(None, description="Price components")
    total_turnkey_price_rub: Optional[int] = Field(None, description="Total turnkey price in RUB")
    customs_breakdown: Optional[VLBCustomsBreakdown] = Field(None, description="Customs details")
    exchange_rates: Optional[dict] = Field(None, description="Exchange rates used")
    error: Optional[str] = Field(None, description="Error message if failed")
    cached: bool = Field(default=False, description="Whether customs was cached")


class BikeCustomsRequest(BaseModel):
    """Request for bike customs calculation"""

    force_refresh: bool = Field(default=False, description="Force refresh cached data")


class VLBServiceConfig(BaseModel):
    """VLB service configuration"""

    base_url: str = Field(default="https://vlb-broker.ru", description="VLB base URL")
    calculator_endpoint: str = Field(
        default="/bitrix/templates/main/classes/calculator/actions/calculate.php",
        description="Calculator endpoint"
    )
    referer_url: str = Field(
        default="https://vlb-broker.ru/tamozhennyy-kalkulyator/",
        description="Referer URL"
    )
    max_requests_per_minute: int = Field(default=10, description="Rate limit")
    session_rotation_requests: int = Field(default=50, description="Session rotation frequency")
    cache_ttl_seconds: int = Field(default=86400, description="Cache TTL (24 hours)")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")