"""
Kazakhstan Customs Calculation Service
Implements turnkey price calculation for Kazakhstan (Almaty)
Based on formula from KAZAKHSTAN.md
"""

from datetime import datetime
from typing import Optional
from schemas.kazakhstan import (
    KZCalculationRequest,
    KZCalculationResponse,
    KZCalculationBreakdown,
)
from services.exchange_rate_service import exchange_rate_service
from services.kz_price_table_service import kz_price_table_service


class KazakhstanCustomsService:
    """
    Service for Kazakhstan customs and turnkey price calculations

    Calculation formula based on KAZAKHSTAN.md:
    1. Car price + Korea expenses (parking, transport, export docs)
    2. Freight ($2,600)
    3. Convert to KZT using Google Sheets rates
    4. Customs duties (calculator.ida.kz formula)
    5. Company commission ($300)
    """

    # Fixed costs in KRW (Korea expenses)
    PARKING_FEE_KRW = 440_000  # Стояночные (Комиссия площадки)
    TRANSPORTATION_KOREA_KRW = 300_000  # Перегон по Корее
    EXPORT_DOCS_KRW = 60_000  # Подготовка экспортных док.

    # Fixed costs in USD
    FREIGHT_USD = 2_600  # Фрахт (shipping)
    COMPANY_COMMISSION_USD = 300  # LipanAuto commission

    # Customs constants (from calculator.ida.kz)
    CUSTOMS_DUTY_RATE = 0.15  # 15% таможенная пошлина
    VAT_RATE = 0.12  # 12% НДС
    CUSTOMS_FEE = 20_000  # 20,000 KZT таможенный сбор

    def __init__(self):
        self.exchange_service = exchange_rate_service
        self.price_table_service = kz_price_table_service

    def calculate_turnkey_price(
        self, request: KZCalculationRequest
    ) -> KZCalculationResponse:
        """
        Calculate complete turnkey price for Kazakhstan

        Args:
            request: KZCalculationRequest with vehicle parameters

        Returns:
            KZCalculationResponse with detailed breakdown
        """
        try:
            # Get exchange rates
            rates = self.exchange_service.get_exchange_rates()
            usd_krw_rate = rates["usd_krw"]
            kzt_krw_rate = rates["kzt_krw"]

            # Get customs price (USD) from kz-table.xlsx if not provided
            customs_price_usd = request.price_usd_for_customs
            if customs_price_usd is None:
                customs_price_usd = self.price_table_service.lookup_price(
                    manufacturer=request.manufacturer,
                    model=request.model,
                    volume=request.engine_volume,
                    year=request.year,
                )

                if customs_price_usd is None:
                    return KZCalculationResponse(
                        success=False,
                        error=(
                            f"Could not find price for {request.manufacturer} {request.model} "
                            f"{request.engine_volume}L {request.year} in KZ price table"
                        ),
                        vehicle_info=request.dict(),
                    )

            # === STEP 1: Korea Expenses (KRW) ===
            freight_krw = self.FREIGHT_USD * usd_krw_rate

            total_korea_krw = (
                request.price_krw
                + self.PARKING_FEE_KRW
                + self.TRANSPORTATION_KOREA_KRW
                + self.EXPORT_DOCS_KRW
                + freight_krw
            )

            # === STEP 2: Convert Korea expenses to KZT ===
            total_korea_kzt = total_korea_krw / kzt_krw_rate

            # === STEP 3: Customs Calculation (calculator.ida.kz formula) ===
            customs_price_kzt = customs_price_usd * (usd_krw_rate / kzt_krw_rate)

            # Customs duty = price * 15%
            customs_duty = customs_price_kzt * self.CUSTOMS_DUTY_RATE

            # Excise = IF(volume >= 3000cc, volume * 100, 0)
            volume_cc = request.engine_volume * 1000
            excise = volume_cc * 100 if volume_cc >= 3000 else 0

            # VAT = (price + customs_fee + excise) * 12%
            vat = (customs_price_kzt + self.CUSTOMS_FEE + excise) * self.VAT_RATE

            # Utilization fee (based on volume)
            utilization_fee = self._calculate_utilization_fee(volume_cc)

            # Registration fee (based on car age)
            current_year = datetime.now().year
            registration_fee = self._calculate_registration_fee(
                current_year - request.year
            )

            # === STEP 4: Total Customs ===
            total_customs = customs_duty + vat + excise
            total_expenses = total_customs + utilization_fee + registration_fee

            # === STEP 5: Company Commission ===
            company_commission_kzt = self.COMPANY_COMMISSION_USD * (
                usd_krw_rate / kzt_krw_rate
            )

            # === STEP 6: Final Turnkey Price ===
            final_price_kzt = (
                total_korea_kzt + customs_price_kzt + total_expenses + company_commission_kzt
            )
            final_price_usd = final_price_kzt / (usd_krw_rate / kzt_krw_rate)

            # Build detailed breakdown
            breakdown = KZCalculationBreakdown(
                # Korea expenses
                car_price_krw=request.price_krw,
                parking_fee_krw=self.PARKING_FEE_KRW,
                transportation_korea_krw=self.TRANSPORTATION_KOREA_KRW,
                export_docs_krw=self.EXPORT_DOCS_KRW,
                freight_usd=self.FREIGHT_USD,
                freight_krw=freight_krw,
                total_korea_krw=total_korea_krw,
                total_korea_kzt=total_korea_kzt,
                # Customs
                customs_price_usd=customs_price_usd,
                customs_price_kzt=customs_price_kzt,
                customs_duty=customs_duty,
                excise=excise,
                vat=vat,
                utilization_fee=utilization_fee,
                registration_fee=registration_fee,
                total_customs=total_customs,
                total_expenses=total_expenses,
                # Company commission
                company_commission_usd=self.COMPANY_COMMISSION_USD,
                company_commission_kzt=company_commission_kzt,
                # Final
                final_price_kzt=final_price_kzt,
                final_price_usd=final_price_usd,
                # Rates
                usd_krw_rate=usd_krw_rate,
                kzt_krw_rate=kzt_krw_rate,
            )

            return KZCalculationResponse(
                success=True,
                turnkey_price_kzt=round(final_price_kzt, 2),
                turnkey_price_usd=round(final_price_usd, 2),
                breakdown=breakdown,
                vehicle_info=request.dict(),
                calculation_date=datetime.now().isoformat(),
            )

        except Exception as e:
            return KZCalculationResponse(
                success=False,
                error=f"Calculation failed: {str(e)}",
                vehicle_info=request.dict(),
            )

    def _calculate_utilization_fee(self, volume_cc: float) -> float:
        """
        Calculate utilization fee based on engine volume

        From KAZAKHSTAN.md formula:
        - 1001-2000cc: 603,750 KZT
        - 2001-3000cc: 862,500 KZT
        - 3001+cc: 1,983,750 KZT
        """
        if volume_cc <= 1000:
            return 0
        elif volume_cc <= 2000:
            return 603_750
        elif volume_cc <= 3000:
            return 862_500
        else:
            return 1_983_750

    def _calculate_registration_fee(self, age: int) -> float:
        """
        Calculate first-time registration fee based on car age

        From KAZAKHSTAN.md formula:
        - age < 2: 863 KZT
        - age <= 3: 172,500 KZT
        - age > 3: 1,725,000 KZT
        """
        if age < 2:
            return 863
        elif age <= 3:
            return 172_500
        else:
            return 1_725_000


# Global singleton instance
kazakhstan_customs_service = KazakhstanCustomsService()
