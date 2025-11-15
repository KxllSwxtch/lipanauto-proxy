"""
Kazakhstan Customs Calculation Schemas
Pydantic models for Kazakhstan turnkey price calculations
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class KZCalculationRequest(BaseModel):
    """Request parameters for Kazakhstan customs calculation"""

    # Car identification
    manufacturer: str = Field(..., description="Car manufacturer (e.g., Hyundai, Kia)")
    model: str = Field(..., description="Car model (e.g., Sonata, K5)")

    # Vehicle parameters
    price_krw: float = Field(..., description="Car price in Korean Won (KRW)", gt=0)
    year: int = Field(..., description="Manufacturing year", ge=1990, le=2030)
    engine_volume: float = Field(..., description="Engine displacement in liters (e.g., 2.0)", gt=0)

    # Optional: if not provided, will be looked up from kz-table.xlsx
    price_usd_for_customs: Optional[float] = Field(
        None,
        description="USD price for customs calculation (from kz-table.xlsx). If not provided, will be looked up automatically."
    )

    @validator("engine_volume")
    def validate_volume(cls, v):
        """Validate engine volume is reasonable"""
        if v < 0.5 or v > 10.0:
            raise ValueError("Engine volume must be between 0.5L and 10.0L")
        return v


class KZCalculationBreakdown(BaseModel):
    """Detailed breakdown of Kazakhstan costs"""

    # Korea expenses (in KRW)
    car_price_krw: float = Field(..., description="Car price in Korea (KRW)")
    parking_fee_krw: float = Field(..., description="Стояночные (Комиссия площадки) - 440,000 KRW")
    transportation_korea_krw: float = Field(..., description="Перегон по Корее - 300,000 KRW")
    export_docs_krw: float = Field(..., description="Подготовка экспортных док. - 60,000 KRW")
    freight_usd: float = Field(..., description="Фрахт - $2,600")
    freight_krw: float = Field(..., description="Freight converted to KRW")

    # Total Korea expenses
    total_korea_krw: float = Field(..., description="Total expenses in Korea (KRW)")
    total_korea_kzt: float = Field(..., description="Total Korea expenses in KZT")

    # Customs calculation inputs
    customs_price_usd: float = Field(..., description="Price used for customs calculation (USD)")
    customs_price_kzt: float = Field(..., description="Customs price in KZT")

    # Customs duties (from calculator.ida.kz formula)
    customs_duty: float = Field(..., description="Таможенная пошлина (15%)")
    excise: float = Field(..., description="Акциз (based on engine volume)")
    vat: float = Field(..., description="НДС (12%)")
    utilization_fee: float = Field(..., description="Утильсбор (based on volume)")
    registration_fee: float = Field(..., description="Первичная регистрация")

    # Totals
    total_customs: float = Field(..., description="Total customs duties (customs + vat + excise)")
    total_expenses: float = Field(..., description="Total expenses (customs + util + registration)")

    # Final price
    company_commission_usd: float = Field(..., description="LipAuto commission ($300)")
    company_commission_kzt: float = Field(..., description="Commission in KZT")

    final_price_kzt: float = Field(..., description="Final turnkey price in Almaty (KZT)")
    final_price_usd: float = Field(..., description="Final turnkey price in USD")

    # Exchange rates used
    usd_krw_rate: float = Field(..., description="USD to KRW exchange rate")
    kzt_krw_rate: float = Field(..., description="KZT to KRW exchange rate")


class KZCalculationResponse(BaseModel):
    """Complete Kazakhstan calculation response"""

    success: bool = Field(..., description="Whether calculation was successful")

    # Main result
    turnkey_price_kzt: Optional[float] = Field(
        None, description="Total turnkey price in Almaty (KZT)"
    )
    turnkey_price_usd: Optional[float] = Field(
        None, description="Total turnkey price in USD"
    )

    # Detailed breakdown
    breakdown: Optional[KZCalculationBreakdown] = Field(
        None, description="Detailed cost breakdown"
    )

    # Error handling
    error: Optional[str] = Field(None, description="Error message if failed")

    # Metadata
    vehicle_info: dict = Field(
        default_factory=dict, description="Input vehicle parameters"
    )
    calculation_date: Optional[str] = Field(None, description="When calculation was performed")


class ExchangeRatesResponse(BaseModel):
    """Response for exchange rates endpoint"""

    success: bool = Field(..., description="Whether rates were fetched successfully")

    usd_krw: Optional[float] = Field(None, description="USD to KRW rate (from Google Sheets K7)")
    kzt_krw: Optional[float] = Field(None, description="KZT to KRW rate (from Google Sheets K8)")

    timestamp: Optional[float] = Field(None, description="Unix timestamp of rates")
    is_fallback: bool = Field(
        default=False,
        description="Whether fallback rates were used (Google Sheets unavailable)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class CNYRatesData(BaseModel):
    """CNY currency rates data"""

    cnyToUsd: float = Field(..., description="CNY to USD rate (1 CNY = X USD)")
    cnyToRub: float = Field(..., description="CNY to RUB rate (1 CNY = X RUB)")
    cnyToKzt: float = Field(..., description="CNY to KZT rate (1 CNY = X KZT)")


class CNYRatesResponse(BaseModel):
    """Response for CNY currency rates endpoint"""

    success: bool = Field(..., description="Whether rates were fetched successfully")
    data: Optional[CNYRatesData] = Field(None, description="CNY exchange rates")
    timestamp: Optional[float] = Field(None, description="Unix timestamp of rates")
    is_fallback: bool = Field(
        default=False,
        description="Whether fallback rates were used (Google Sheets unavailable)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class KZPriceLookupRequest(BaseModel):
    """Request for KZ price table lookup"""

    manufacturer: str = Field(..., description="Car manufacturer")
    model: str = Field(..., description="Car model")
    volume: float = Field(..., description="Engine volume in liters")
    year: int = Field(..., description="Manufacturing year")


class KZPriceLookupResponse(BaseModel):
    """Response from KZ price table lookup"""

    success: bool = Field(..., description="Whether lookup was successful")

    price_usd: Optional[float] = Field(None, description="Price in USD from kz-table.xlsx")

    error: Optional[str] = Field(None, description="Error message if not found")
    match_type: Optional[str] = Field(
        None,
        description="Type of match (exact, fuzzy_year, closest)"
    )
