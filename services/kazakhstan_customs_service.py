"""
Kazakhstan Turnkey Price Calculation Service
Calculates simple turnkey price for Kazakhstan (Almaty)
Formula: Korea expenses (car + parking + transport + freight + docs) + company commission
"""

from datetime import datetime
from schemas.kazakhstan import (
    KZCalculationRequest,
    KZCalculationResponse,
    KZCalculationBreakdown,
)
from services.exchange_rate_service import exchange_rate_service


class KazakhstanCustomsService:
    """
    Service for Kazakhstan turnkey price calculations

    Simplified calculation formula:
    1. Korea expenses (car price + parking + transport + freight + docs)
    2. Company commission ($300)
    3. Final price = Korea expenses + commission

    Note: Does NOT include Kazakhstan customs duties, taxes, or fees.
    Customer is responsible for customs clearance in Kazakhstan.
    """

    # Fixed costs in KRW (Korea expenses)
    PARKING_FEE_KRW = 440_000  # Стояночные (Комиссия площадки)
    TRANSPORTATION_KOREA_KRW = 300_000  # Перегон по Корее
    EXPORT_DOCS_KRW = 60_000  # Подготовка экспортных док.

    # Fixed costs in USD
    FREIGHT_USD = 1_450  # Фрахт (shipping)
    COMPANY_COMMISSION_USD = 300  # LipanAuto commission

    def __init__(self):
        self.exchange_service = exchange_rate_service

    def calculate_turnkey_price(
        self, request: KZCalculationRequest
    ) -> KZCalculationResponse:
        """
        Calculate turnkey price for Kazakhstan (Korea expenses + commission only)

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

            # === STEP 3: Company Commission ===
            company_commission_kzt = self.COMPANY_COMMISSION_USD * (
                usd_krw_rate / kzt_krw_rate
            )

            # === STEP 4: Final Turnkey Price ===
            final_price_kzt = total_korea_kzt + company_commission_kzt
            final_price_usd = final_price_kzt / (usd_krw_rate / kzt_krw_rate)

            # Print calculation details
            print(f"\n{'='*60}")
            print(f"🧮 KAZAKHSTAN TURNKEY PRICE CALCULATION")
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
            print(f"\n💼 COMPANY COMMISSION:")
            print(f"  Commission (USD): ${self.COMPANY_COMMISSION_USD:,.0f}")
            print(f"  Commission (KZT): {company_commission_kzt:,.2f}")
            print(f"\n🎯 FINAL TURNKEY PRICE (Delivered to Kazakhstan):")
            print(f"  Korea expenses: {total_korea_kzt:,.2f} KZT")
            print(f"  + Commission: {company_commission_kzt:,.2f} KZT")
            print(f"  {'='*40}")
            print(f"  TOTAL (KZT): {final_price_kzt:,.2f} ₸")
            print(f"  TOTAL (USD): ${final_price_usd:,.2f}")
            print(f"\n⚠️  NOTE: Price does NOT include Kazakhstan customs duties/taxes")
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


# Global singleton instance
kazakhstan_customs_service = KazakhstanCustomsService()
