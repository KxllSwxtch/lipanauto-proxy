"""
Schemas for Russian customs calculation via pan-auto.ru and calcus.ru

This module provides Pydantic models for:
1. Pan-Auto.ru API responses (pre-calculated customs with HP)
2. Calcus.ru API requests/responses (manual calculation with HP input)
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


# =============================================================================
# PAN-AUTO.RU SCHEMAS
# =============================================================================

class PanAutoCostsRUB(BaseModel):
    """Cost breakdown from pan-auto.ru in RUB"""
    carPriceEncar: float = Field(..., description="Original price in KRW from Encar")
    carPrice: float = Field(..., description="Car price converted to RUB")
    clearanceCost: float = Field(..., description="Customs clearance fee (Таможенный сбор)")
    utilizationFee: float = Field(..., description="Utilization fee (Утилизационный сбор)")
    customsDuty: float = Field(..., description="Customs duty (Таможенная пошлина)")
    deliveryRate: Optional[float] = Field(None, description="Delivery rate per unit")
    deliveryCost: float = Field(..., description="Total delivery cost to Vladivostok")
    vladivostokServices: float = Field(..., description="Services in Vladivostok")
    totalFees: float = Field(..., description="Total fees (customs + other)")
    finalCost: float = Field(..., description="Final turnkey cost in RUB")
    dealerCost: Optional[float] = Field(0.0, description="Dealer markup if any")


class PanAutoCostsUSD(BaseModel):
    """Cost breakdown from pan-auto.ru in USD"""
    carPriceEncar: float
    carPrice: float
    clearanceCost: float
    utilizationFee: float
    customsDuty: float
    deliveryRate: Optional[float] = None
    deliveryCost: float
    vladivostokServices: float
    totalFees: float
    finalCost: float
    dealerCost: Optional[float] = 0.0


class PanAutoExchangeRates(BaseModel):
    """Exchange rates from pan-auto.ru"""
    russiaUsdBuyRate: Optional[float] = None
    russiaEuroBuyRate: Optional[float] = None
    russiaCnyBuyRate: Optional[float] = None
    koreaUsdBuyRate: Optional[float] = None
    koreaEuroRate: Optional[float] = None
    koreaRubRate: Optional[float] = None
    koreaUsdRate: Optional[float] = None
    koreaCnyRate: Optional[float] = None
    deliveryRate: Optional[float] = None


class PanAutoCosts(BaseModel):
    """Complete costs structure from pan-auto.ru"""
    RUB: Optional[PanAutoCostsRUB] = None
    USD: Optional[PanAutoCostsUSD] = None
    exchangeRatesManual: Optional[PanAutoExchangeRates] = None


class PanAutoManufacturer(BaseModel):
    """Manufacturer info from pan-auto.ru"""
    id: int
    name: str
    translation: Optional[str] = None
    value: Optional[str] = None
    query: Optional[str] = None


class PanAutoModel(BaseModel):
    """Model info from pan-auto.ru"""
    id: int
    name: str
    translation: Optional[str] = None
    value: Optional[str] = None
    query: Optional[str] = None


class PanAutoGeneration(BaseModel):
    """Generation info from pan-auto.ru"""
    id: int
    name: str
    translation: Optional[str] = None
    value: Optional[str] = None
    model_start_date: Optional[str] = None
    model_end_date: Optional[str] = None
    query: Optional[str] = None


class PanAutoCarData(BaseModel):
    """Full car data structure from pan-auto.ru API"""
    id: str
    hp: Optional[int] = Field(None, description="Engine horsepower - key field for customs")
    displacement: Optional[int] = Field(None, description="Engine displacement in cc")
    mileage: Optional[int] = None
    year: Optional[str] = Field(None, description="Year string like 'Апрель, 2017 год'")
    formYear: Optional[str] = Field(None, description="Formatted year like '2017'")
    fuelType: Optional[str] = None
    color: Optional[str] = None
    badge: Optional[str] = None
    badgeDetail: Optional[str] = None
    vin: Optional[str] = None
    AWD: Optional[bool] = None

    manufacturer: Optional[PanAutoManufacturer] = None
    model: Optional[PanAutoModel] = None
    generation: Optional[PanAutoGeneration] = None
    costs: Optional[PanAutoCosts] = None

    photos: Optional[List[str]] = None
    accidentCnt: Optional[int] = None
    reserved: Optional[bool] = None
    views: Optional[int] = None
    dealer: Optional[bool] = None

    # Allow extra fields
    class Config:
        extra = "allow"


class PanAutoCarResponse(BaseModel):
    """Response from our pan-auto.ru proxy endpoint"""
    success: bool
    car_id: str
    hp: Optional[int] = Field(None, description="Engine horsepower")
    displacement: Optional[int] = Field(None, description="Engine displacement in cc")
    year: Optional[str] = Field(None, description="Year string")
    form_year: Optional[str] = Field(None, description="Formatted year (e.g., '2017')")
    fuel_type: Optional[str] = None
    mileage: Optional[int] = None

    # Customs breakdown (if available)
    costs_rub: Optional[PanAutoCostsRUB] = None

    # Additional metadata
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    badge: Optional[str] = None
    vin: Optional[str] = None

    # Status flags
    has_hp: bool = Field(default=False, description="Whether HP data is available")
    has_customs: bool = Field(default=False, description="Whether customs data is available")

    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# CALCUS.RU SCHEMAS
# =============================================================================

class CalcusCalculationRequest(BaseModel):
    """Request for calcus.ru customs calculation"""
    car_id: str = Field(..., description="Car identifier for tracking")
    price_krw: int = Field(..., description="Car price in Korean Won", ge=1)
    displacement: int = Field(..., description="Engine displacement in cm³", ge=1)
    year: int = Field(..., description="Manufacturing year", ge=1990, le=2030)
    power: int = Field(..., description="Engine power in HP (REQUIRED)", ge=1, le=2000)
    engine_type: str = Field(default="petrol", description="Engine type: petrol/diesel/hybrid/electric")
    owner_type: str = Field(default="individual", description="Owner type: individual/legal")

    @validator("engine_type")
    def validate_engine_type(cls, v):
        allowed = ["petrol", "diesel", "hybrid", "electric"]
        if v.lower() not in allowed:
            raise ValueError(f"engine_type must be one of: {allowed}")
        return v.lower()

    @validator("owner_type")
    def validate_owner_type(cls, v):
        allowed = ["individual", "legal"]
        if v.lower() not in allowed:
            raise ValueError(f"owner_type must be one of: {allowed}")
        return v.lower()


class CalcusCustomsBreakdown(BaseModel):
    """Customs breakdown from calcus.ru calculation"""
    clearance_cost: float = Field(..., description="Таможенный сбор (sbor)")
    utilization_fee: float = Field(..., description="Утилизационный сбор (util)")
    customs_duty: float = Field(..., description="Таможенная пошлина (tax/duty)")
    excise: Optional[float] = Field(0.0, description="Excise tax if applicable")
    vat: Optional[float] = Field(0.0, description="VAT if applicable")
    total: float = Field(..., description="Total customs payments")


class CalcusCalculationResponse(BaseModel):
    """Response from our calcus.ru proxy endpoint"""
    success: bool
    car_id: str
    customs: Optional[CalcusCustomsBreakdown] = None

    # Input parameters echoed back for verification
    input_params: Optional[Dict[str, Any]] = None

    # Exchange rates used in calculation
    exchange_rates: Optional[Dict[str, float]] = None

    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# UNIFIED RESPONSE SCHEMA (for frontend consumption)
# =============================================================================

class RussianCustomsUnified(BaseModel):
    """
    Unified customs response that can come from either pan-auto.ru or calcus.ru
    Used by frontend for consistent handling
    """
    success: bool
    source: str = Field(..., description="Data source: 'pan-auto' or 'calcus'")
    car_id: str

    # Customs breakdown
    clearance_cost: Optional[float] = Field(None, description="Таможенный сбор")
    utilization_fee: Optional[float] = Field(None, description="Утилизационный сбор")
    customs_duty: Optional[float] = Field(None, description="Таможенная пошлина")
    total_customs: Optional[float] = Field(None, description="Total customs")

    # Full turnkey price (from pan-auto.ru only)
    final_cost_rub: Optional[float] = Field(None, description="Final turnkey cost in RUB")

    # Metadata
    hp: Optional[int] = None
    calculation_date: Optional[str] = None

    # Status
    requires_manual_input: bool = Field(default=False, description="True if HP input is needed")
    error: Optional[str] = None
