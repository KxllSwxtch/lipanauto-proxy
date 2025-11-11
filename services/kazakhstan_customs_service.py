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

            print(f"\n{'='*60}")
            print(f"🧮 KAZAKHSTAN CUSTOMS CALCULATION")
            print(f"{'='*60}")
            print(f"Vehicle: {request.manufacturer} {request.model} {request.year}")
            print(f"Engine: {request.engine_volume}L ({request.engine_volume * 1000:.0f}cc)")
            print(f"\n📊 EXCHANGE RATES:")
            print(f"  USD/KRW: {usd_krw_rate:,.2f}")
            print(f"  KZT/KRW: {kzt_krw_rate:.4f}")
            print(f"  USD/KZT: {usd_krw_rate / kzt_krw_rate:,.2f}")
            print(f"\n💰 KOREA EXPENSES:")
            print(f"  Car price (KRW): {request.price_krw:,.0f}")
            print(f"  Parking fee (KRW): {self.PARKING_FEE_KRW:,.0f}")
            print(f"  Transportation (KRW): {self.TRANSPORTATION_KOREA_KRW:,.0f}")
            print(f"  Export docs (KRW): {self.EXPORT_DOCS_KRW:,.0f}")
            print(f"  Freight (USD): ${self.FREIGHT_USD:,.0f} = {freight_krw:,.0f} KRW")
            print(f"  Total Korea (KRW): {total_korea_krw:,.0f}")
            print(f"  Total Korea (KZT): {total_korea_kzt:,.2f}")

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
            car_age = current_year - request.year
            registration_fee = self._calculate_registration_fee(car_age)

            print(f"\n🚢 CUSTOMS CALCULATION (calculator.ida.kz formula):")
            print(f"  Customs price (USD): ${customs_price_usd:,.2f}")
            print(f"  Customs price (KZT): {customs_price_kzt:,.2f}")
            print(f"  Customs duty (15%): {customs_duty:,.2f}")
            print(f"  Excise ({'>= 3000cc' if volume_cc >= 3000 else '< 3000cc'}): {excise:,.2f}")
            print(f"  VAT base: {customs_price_kzt:,.2f} + {self.CUSTOMS_FEE:,.0f} + {excise:,.2f}")
            print(f"  VAT (12%): {vat:,.2f}")
            print(f"  Utilization fee ({volume_cc:.0f}cc): {utilization_fee:,.2f}")
            print(f"  Registration fee (age {car_age}): {registration_fee:,.2f}")

            # === STEP 4: Total Customs ===
            total_customs = customs_duty + vat + excise
            total_expenses = total_customs + utilization_fee + registration_fee

            print(f"\n📋 TOTALS:")
            print(f"  Total customs (duty + VAT + excise): {total_customs:,.2f} KZT")
            print(f"  Total KZ expenses (customs + util + reg): {total_expenses:,.2f} KZT")

            # === STEP 5: Company Commission ===
            company_commission_kzt = self.COMPANY_COMMISSION_USD * (
                usd_krw_rate / kzt_krw_rate
            )

            print(f"\n💼 COMPANY COMMISSION:")
            print(f"  Commission (USD): ${self.COMPANY_COMMISSION_USD:,.0f}")
            print(f"  Commission (KZT): {company_commission_kzt:,.2f}")

            # === STEP 6: Final Turnkey Price ===
            # Note: customs_price_kzt is NOT added separately because customs duties
            # (calculated as 15% of customs_price_kzt) are already included in total_expenses
            # This matches calculator.ida.kz formula: final = base + duties + fees
            final_price_kzt = (
                total_korea_kzt + total_expenses + company_commission_kzt
            )
            final_price_usd = final_price_kzt / (usd_krw_rate / kzt_krw_rate)

            print(f"\n🎯 FINAL TURNKEY PRICE:")
            print(f"  Korea expenses: {total_korea_kzt:,.2f} KZT")
            print(f"  + KZ expenses: {total_expenses:,.2f} KZT")
            print(f"  + Commission: {company_commission_kzt:,.2f} KZT")
            print(f"  {'='*40}")
            print(f"  TOTAL (KZT): {final_price_kzt:,.2f} ₸")
            print(f"  TOTAL (USD): ${final_price_usd:,.2f}")
            print(f"{'='*60}\n")

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

        From calculator.ida.kz formula (EXACT match):
        - 1001-2000cc: 603,750 KZT
        - 2001-3000cc: 862,500 KZT
        - Other volumes (≤1000cc OR >3000cc): 1,983,750 KZT

        Note: Small engines (≤1000cc) and large engines (>3000cc)
        both have the highest recycling fee per Kazakhstan policy
        """
        if 1001 <= volume_cc <= 2000:
            return 603_750
        elif 2001 <= volume_cc <= 3000:
            return 862_500
        else:
            # All other volumes: ≤1000cc OR >3000cc
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
