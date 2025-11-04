"""
Exchange Rate Service for Kazakhstan Calculations
Fetches USD/KRW and KZT/KRW rates from Google Sheets
"""
import os
import time
from typing import Dict, Optional
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class ExchangeRateService:
    """
    Service to fetch exchange rates from Google Sheets

    Fetches:
    - USD/KRW rate from cell K7
    - KZT/KRW rate from cell K8

    Google Sheets URL:
    https://docs.google.com/spreadsheets/d/1i3Kj3rA0PVTJrNPL5fzEuN8qjRiOkLgrOpet16r2X5A/edit
    """

    def __init__(self):
        self.spreadsheet_id = "1i3Kj3rA0PVTJrNPL5fzEuN8qjRiOkLgrOpet16r2X5A"
        self.sheet_name = "Sheet1"  # Adjust if needed
        self.cache: Dict[str, any] = {}
        self.cache_ttl = 900  # 15 minutes in seconds
        self.last_fetch_time = 0

        # Initialize Google Sheets API
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Sheets API service"""
        try:
            # Method 1: Using API Key (simpler, read-only access)
            api_key = os.getenv("GOOGLE_SHEETS_API_KEY")

            if api_key:
                self.service = build('sheets', 'v4', developerKey=api_key)
                print("✅ Google Sheets API initialized with API key")
            else:
                # Method 2: Using Service Account (if API key not available)
                credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
                if credentials_path and os.path.exists(credentials_path):
                    creds = service_account.Credentials.from_service_account_file(
                        credentials_path,
                        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                    )
                    self.service = build('sheets', 'v4', credentials=creds)
                    print("✅ Google Sheets API initialized with service account")
                else:
                    print("⚠️  No Google Sheets credentials found. Exchange rates will use fallback values.")

        except Exception as e:
            print(f"❌ Failed to initialize Google Sheets API: {e}")
            self.service = None

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        return (
            self.cache and
            'timestamp' in self.cache and
            (time.time() - self.cache['timestamp']) < self.cache_ttl
        )

    def get_exchange_rates(self) -> Dict[str, float]:
        """
        Fetch exchange rates from Google Sheets

        Returns:
            Dict with keys:
            - usd_krw: USD to KRW rate (from K7)
            - kzt_krw: KZT to KRW rate (from K8)
            - timestamp: When rates were fetched
        """
        # Return cached data if valid
        if self._is_cache_valid():
            print("📦 Using cached exchange rates")
            return {
                'usd_krw': self.cache['usd_krw'],
                'kzt_krw': self.cache['kzt_krw'],
                'timestamp': self.cache['timestamp']
            }

        # Fetch fresh data
        try:
            if not self.service:
                # Fallback rates if API not available
                print("⚠️  Using fallback exchange rates (API not configured)")
                return self._get_fallback_rates()

            # Fetch cells K7 and K8
            # Note: Using A1 notation
            range_name = f"{self.sheet_name}!K7:K8"

            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])

            if not values or len(values) < 2:
                print("⚠️  Invalid data from Google Sheets. Using fallback rates.")
                return self._get_fallback_rates()

            # Extract rates
            usd_krw = float(values[0][0]) if values[0] else 1350.0  # K7
            kzt_krw = float(values[1][0]) if len(values) > 1 and values[1] else 2.7  # K8

            # Update cache
            self.cache = {
                'usd_krw': usd_krw,
                'kzt_krw': kzt_krw,
                'timestamp': time.time()
            }

            print(f"✅ Exchange rates fetched: USD/KRW={usd_krw}, KZT/KRW={kzt_krw}")

            return {
                'usd_krw': usd_krw,
                'kzt_krw': kzt_krw,
                'timestamp': self.cache['timestamp']
            }

        except Exception as e:
            print(f"❌ Error fetching exchange rates: {e}")
            return self._get_fallback_rates()

    def _get_fallback_rates(self) -> Dict[str, float]:
        """
        Return fallback exchange rates if Google Sheets fetch fails

        These should be updated manually or use a different API
        """
        return {
            'usd_krw': 1350.0,  # Approximate USD to KRW rate
            'kzt_krw': 2.7,     # Approximate KZT to KRW rate
            'timestamp': time.time(),
            'fallback': True
        }

    def get_usd_krw_rate(self) -> float:
        """Get USD to KRW exchange rate"""
        rates = self.get_exchange_rates()
        return rates['usd_krw']

    def get_kzt_krw_rate(self) -> float:
        """Get KZT to KRW exchange rate"""
        rates = self.get_exchange_rates()
        return rates['kzt_krw']

    def convert_krw_to_kzt(self, krw_amount: float) -> float:
        """
        Convert KRW amount to KZT

        Args:
            krw_amount: Amount in Korean Won

        Returns:
            Amount in Kazakhstani Tenge
        """
        kzt_krw_rate = self.get_kzt_krw_rate()
        return krw_amount / kzt_krw_rate

    def convert_usd_to_krw(self, usd_amount: float) -> float:
        """
        Convert USD amount to KRW

        Args:
            usd_amount: Amount in US Dollars

        Returns:
            Amount in Korean Won
        """
        usd_krw_rate = self.get_usd_krw_rate()
        return usd_amount * usd_krw_rate

    def convert_usd_to_kzt(self, usd_amount: float) -> float:
        """
        Convert USD amount to KZT (via KRW)

        Args:
            usd_amount: Amount in US Dollars

        Returns:
            Amount in Kazakhstani Tenge
        """
        krw_amount = self.convert_usd_to_krw(usd_amount)
        return self.convert_krw_to_kzt(krw_amount)


# Global singleton instance
exchange_rate_service = ExchangeRateService()
