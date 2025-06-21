"""
Schemas for customs duty calculation
Pydantic models for TKS.ru customs calculator integration
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator


class CustomsCalculationRequest(BaseModel):
    """Request parameters for customs duty calculation"""

    # Vehicle parameters
    cost: int = Field(..., description="Vehicle cost in original currency", ge=1)
    volume: int = Field(..., description="Engine displacement in cm³", ge=1)
    currency: int = Field(
        default=410, description="Currency code (410=KRW, 840=USD, 978=EUR)"
    )
    power: int = Field(..., description="Engine power", ge=1)
    power_edizm: str = Field(
        default="ls", description="Power unit (ls=horsepower, kw=kilowatt)"
    )

    # Vehicle characteristics
    country: str = Field(
        default="noru", description="Country of origin (noru=non-Russia)"
    )
    engine_type: str = Field(
        default="petrol", description="Engine type (petrol, diesel, electric)"
    )
    age: int = Field(..., description="Vehicle age in years", ge=0, le=50)

    # Legal entity type
    face: str = Field(
        default="jur", description="Entity type (jur=legal, fiz=individual)"
    )

    # Vehicle type and classification
    ts_type: str = Field(
        default="06_8711", description="Vehicle type code for motorcycles"
    )
    mass: Optional[int] = Field(default=None, description="Vehicle mass in kg")
    chassis: str = Field(default="shs", description="Chassis type")

    # Additional flags
    forwarder: bool = Field(default=False, description="Using forwarder services")
    caravan: bool = Field(default=False, description="Is caravan/trailer")
    offroad: bool = Field(default=False, description="Off-road vehicle")
    buscap: str = Field(default="lt120", description="Bus capacity if applicable")
    mdvs_gt_m30ed: bool = Field(default=True, description="MDVS greater than 30 units")
    sequential: bool = Field(default=False, description="Sequential import")
    boat_sea: Optional[str] = Field(default=None, description="Sea vessel type")
    sh2017: Optional[str] = Field(default=None, description="2017 classification")
    bus_municipal_cb: Optional[str] = Field(
        default=None, description="Municipal bus checkbox"
    )

    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency codes"""
        valid_currencies = {410: "KRW", 840: "USD", 978: "EUR", 643: "RUB"}
        if v not in valid_currencies:
            raise ValueError(
                f"Invalid currency code. Valid codes: {list(valid_currencies.keys())}"
            )
        return v

    @validator("engine_type")
    def validate_engine_type(cls, v):
        """Validate engine type"""
        valid_types = ["petrol", "diesel", "electric", "hybrid"]
        if v not in valid_types:
            raise ValueError(f"Invalid engine type. Valid types: {valid_types}")
        return v

    @validator("face")
    def validate_face(cls, v):
        """Validate entity type"""
        valid_faces = ["jur", "fiz"]
        if v not in valid_faces:
            raise ValueError(f"Invalid entity type. Valid types: {valid_faces}")
        return v


class CustomsPayment(BaseModel):
    """Individual customs payment item"""

    name: str = Field(..., description="Payment name in Russian")
    name_en: str = Field(..., description="Payment name in English")
    rate: Optional[str] = Field(None, description="Tax rate (e.g., '15%', 'нет')")
    amount_rub: float = Field(..., description="Amount in Russian rubles")
    amount_usd: Optional[float] = Field(None, description="Amount in USD")


class ExchangeRates(BaseModel):
    """Exchange rates used in calculation"""

    eur_rate: float = Field(..., description="EUR to RUB exchange rate")
    usd_rate: float = Field(..., description="USD to RUB exchange rate")
    currency_rate: float = Field(..., description="Original currency to RUB rate")
    currency_code: str = Field(..., description="Original currency code (e.g., 'KRW')")
    currency_unit: int = Field(
        default=1, description="Currency unit (e.g., 1000 for KRW)"
    )


class CustomsCalculationResult(BaseModel):
    """Complete customs calculation result"""

    # Main payments
    customs_clearance: CustomsPayment = Field(..., description="Customs clearance fee")
    duty: CustomsPayment = Field(..., description="Customs duty")
    excise: CustomsPayment = Field(..., description="Excise tax")
    vat: CustomsPayment = Field(..., description="VAT (НДС)")
    utilization_fee: CustomsPayment = Field(..., description="Utilization fee")

    # Totals
    total_without_utilization: float = Field(
        ..., description="Total without utilization fee (RUB)"
    )
    total_with_utilization: float = Field(
        ..., description="Total with utilization fee (RUB)"
    )
    total_usd: Optional[float] = Field(None, description="Total amount in USD")

    # Exchange rates
    exchange_rates: ExchangeRates = Field(..., description="Exchange rates used")

    # Metadata
    calculation_date: str = Field(..., description="Calculation date")
    vehicle_info: dict = Field(..., description="Original vehicle parameters")


class CustomsCalculationResponse(BaseModel):
    """API response for customs calculation"""

    success: bool = Field(..., description="Whether calculation was successful")
    result: Optional[CustomsCalculationResult] = Field(
        None, description="Calculation result"
    )
    error: Optional[str] = Field(None, description="Error message if failed")

    meta: dict = Field(default_factory=dict, description="Metadata about the request")


class CaptchaSolutionRequest(BaseModel):
    """Request for solving captcha via CapSolver"""

    task_type: str = Field(
        default="ReCaptchaV2TaskProxyLess", description="Captcha task type"
    )
    website_key: str = Field(..., description="reCAPTCHA site key")
    website_url: str = Field(..., description="Website URL where captcha is located")
    proxy: Optional[str] = Field(None, description="Proxy for captcha solving")


class CaptchaSolutionResponse(BaseModel):
    """Response from captcha solving service"""

    success: bool = Field(..., description="Whether captcha was solved successfully")
    solution: Optional[str] = Field(None, description="Captcha solution token")
    error: Optional[str] = Field(None, description="Error message if failed")
    task_id: Optional[str] = Field(None, description="Task ID for tracking")
    solving_time: Optional[float] = Field(
        None, description="Time taken to solve in seconds"
    )
