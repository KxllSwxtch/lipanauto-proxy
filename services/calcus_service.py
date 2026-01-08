"""
Calcus.ru Russian Customs Calculator Service
Calculates Russian customs duties using the calcus.ru API

Key features:
- Uses year=2026 as required by new customs rules
- Requires HP (power) value for calculation
- No CAPTCHA needed (public API)
- Caches results for 24 hours
"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
import requests
from dataclasses import dataclass
import threading

from schemas.customs_russia import (
    CalcusCalculationRequest,
    CalcusCalculationResponse,
    CalcusCustomsBreakdown
)

logger = logging.getLogger(__name__)


@dataclass
class CachedCalcusResult:
    """Cached calcus.ru calculation result"""

    response: CalcusCalculationResponse
    created_at: datetime
    ttl_seconds: int = 86400  # 24 hours cache (customs rates rarely change)

    @property
    def is_expired(self) -> bool:
        """Check if cached result is expired"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)


class CalcusService:
    """
    Calcus.ru customs calculator service

    Features:
    - POST requests to calcus.ru/calculate/Customs
    - Uses year=2026 as required by new rules
    - Requires HP (power) parameter
    - Parses Russian-formatted numbers from response
    - Caches results for 24 hours
    """

    BASE_URL = "https://calcus.ru"
    CALCULATOR_ENDPOINT = "/calculate/Customs"

    # User-Agent pool
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
    ]

    # Engine type mapping
    ENGINE_TYPE_MAP = {
        'petrol': '1',
        'diesel': '2',
        'hybrid': '3',
        'electric': '4'
    }

    # Owner type mapping
    OWNER_TYPE_MAP = {
        'individual': '1',  # физическое лицо
        'legal': '2'        # юридическое лицо
    }

    def __init__(self):
        """Initialize Calcus service"""

        # Caching
        self.cache: Dict[str, CachedCalcusResult] = {}
        self.cache_lock = threading.Lock()

        # Session management
        self.session = requests.Session()
        self.current_user_agent_index = 0

        # Performance tracking
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_made': 0,
            'api_failures': 0,
            'successful_calculations': 0
        }

        self._setup_session()

    def _setup_session(self):
        """Setup HTTP session with proper headers"""

        user_agent = self.USER_AGENTS[self.current_user_agent_index]

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/rastamozhka-avto/',
            'User-Agent': user_agent,
            'X-Requested-With': 'XMLHttpRequest'
        }

        self.session.headers.update(headers)

    def _rotate_user_agent(self):
        """Rotate User-Agent for next request"""

        self.current_user_agent_index = (
            self.current_user_agent_index + 1
        ) % len(self.USER_AGENTS)

        user_agent = self.USER_AGENTS[self.current_user_agent_index]
        self.session.headers['User-Agent'] = user_agent

    def _get_cache_key(self, request: CalcusCalculationRequest) -> str:
        """Generate cache key for calculation request"""
        return (
            f"calcus_{request.car_id}_{request.price_krw}_{request.displacement}_"
            f"{request.year}_{request.power}_{request.engine_type}"
        )

    def _get_cached_result(self, request: CalcusCalculationRequest) -> Optional[CalcusCalculationResponse]:
        """Get cached result if valid"""

        cache_key = self._get_cache_key(request)

        with self.cache_lock:
            cached = self.cache.get(cache_key)
            if cached and not cached.is_expired:
                self.stats['cache_hits'] += 1
                logger.info(f"Cache hit for calcus calculation: {cache_key[:50]}...")
                return cached.response
            elif cached:
                del self.cache[cache_key]

        self.stats['cache_misses'] += 1
        return None

    def _cache_result(self, request: CalcusCalculationRequest, response: CalcusCalculationResponse):
        """Cache calculation result"""

        cache_key = self._get_cache_key(request)

        with self.cache_lock:
            self.cache[cache_key] = CachedCalcusResult(
                response=response,
                created_at=datetime.now()
            )

    def _calculate_age_category(self, year: int) -> str:
        """
        Calculate vehicle age category for customs

        Categories:
        - "0-3": 0 to 3 years old
        - "3-5": 3 to 5 years old
        - "5-7": 5 to 7 years old
        - "7-0": 7+ years old
        """

        current_year = datetime.now().year
        age = current_year - year

        if age < 3:
            return "0-3"
        elif age < 5:
            return "3-5"
        elif age < 7:
            return "5-7"
        else:
            return "7-0"

    def _parse_russian_number(self, value: str) -> Optional[float]:
        """
        Parse Russian-formatted number string

        Examples:
        - "1 234 567 ₽" -> 1234567.0
        - "1,234,567.00" -> 1234567.0
        - "123456.78" -> 123456.78
        """

        if not value:
            return None

        try:
            # Remove currency symbols and whitespace
            cleaned = re.sub(r'[₽$€\s]', '', value)

            # Handle Russian format (spaces as thousand separators, comma as decimal)
            # First try: spaces as separators
            if ' ' in cleaned:
                cleaned = cleaned.replace(' ', '')

            # Handle comma as decimal separator (Russian format)
            if ',' in cleaned and '.' not in cleaned:
                cleaned = cleaned.replace(',', '.')
            elif ',' in cleaned and '.' in cleaned:
                # If both exist, comma is probably thousand separator
                cleaned = cleaned.replace(',', '')

            return float(cleaned)

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse number '{value}': {e}")
            return None

    def _build_request_data(self, request: CalcusCalculationRequest) -> Dict[str, str]:
        """Build form data for calcus.ru API request"""

        age_category = self._calculate_age_category(request.year)
        engine_type = self.ENGINE_TYPE_MAP.get(request.engine_type, '1')
        owner_type = self.OWNER_TYPE_MAP.get(request.owner_type, '1')

        return {
            'owner': owner_type,
            'age': age_category,
            'engine': engine_type,
            'power': str(request.power),           # HP value (REQUIRED for 2026 rules)
            'power_unit': '1',                     # 1 = HP, 2 = kW
            'value': str(request.displacement),   # Engine volume in cc
            'price': str(request.price_krw),      # Price in source currency
            'curr': 'KRW',                        # Currency code
            'year': '2026'                        # IMPORTANT: Fixed to 2026 for new rules
        }

    async def calculate_customs(
        self,
        request: CalcusCalculationRequest,
        force_refresh: bool = False
    ) -> CalcusCalculationResponse:
        """
        Calculate Russian customs duties via calcus.ru API

        Args:
            request: Calculation request with car details and HP
            force_refresh: Skip cache and force fresh calculation

        Returns:
            CalcusCalculationResponse with customs breakdown or error
        """

        # Validate HP
        if not request.power or request.power < 1:
            return CalcusCalculationResponse(
                success=False,
                car_id=request.car_id,
                error="HP (power) value is required for customs calculation"
            )

        # Check cache first
        if not force_refresh:
            cached = self._get_cached_result(request)
            if cached:
                return cached

        # Make API request
        try:
            result = await self._fetch_from_api(request)

            # Cache successful result
            if result.success:
                self._cache_result(request, result)
                self.stats['successful_calculations'] += 1

            return result

        except Exception as e:
            self.stats['api_failures'] += 1
            logger.error(f"Calcus.ru calculation failed: {str(e)}")

            return CalcusCalculationResponse(
                success=False,
                car_id=request.car_id,
                error=f"Calculation failed: {str(e)}"
            )

    async def _fetch_from_api(self, request: CalcusCalculationRequest) -> CalcusCalculationResponse:
        """Make actual API request to calcus.ru"""

        # Rotate user agent
        self._rotate_user_agent()

        # Small delay to be polite
        delay = random.uniform(0.5, 1.5)
        await asyncio.sleep(delay)

        url = f"{self.BASE_URL}{self.CALCULATOR_ENDPOINT}"
        data = self._build_request_data(request)

        logger.info(
            f"Calculating customs via calcus.ru: "
            f"price={request.price_krw} KRW, displacement={request.displacement}cc, "
            f"HP={request.power}, year={request.year}"
        )

        try:
            response = self.session.post(url, data=data, timeout=20)
            self.stats['api_calls_made'] += 1

            if response.status_code == 200:
                return self._parse_response(request, response.json())

            else:
                logger.warning(f"Calcus.ru API returned status {response.status_code}")
                return CalcusCalculationResponse(
                    success=False,
                    car_id=request.car_id,
                    error=f"Calcus.ru API error: HTTP {response.status_code}"
                )

        except requests.Timeout:
            logger.warning("Timeout calling calcus.ru API")
            return CalcusCalculationResponse(
                success=False,
                car_id=request.car_id,
                error="Request timeout"
            )

        except requests.RequestException as e:
            logger.error(f"Request error calling calcus.ru: {str(e)}")
            raise

    def _parse_response(
        self,
        request: CalcusCalculationRequest,
        data: dict
    ) -> CalcusCalculationResponse:
        """
        Parse calcus.ru API response

        Expected response format:
        {
            "total": "1 234 567 ₽",
            "total2": "1 345 678 ₽",
            "sborStr": "11 746 ₽",
            "poshlinaStr": "880 140 ₽",
            "utilStr": "2 640 000 ₽",
            "akcizStr": "0 ₽",
            "ndsStr": "0 ₽",
            ...
        }
        """

        try:
            # Parse individual components
            clearance_cost = self._parse_russian_number(data.get('sborStr', '0'))
            customs_duty = self._parse_russian_number(data.get('poshlinaStr', '0'))
            utilization_fee = self._parse_russian_number(data.get('utilStr', '0'))
            excise = self._parse_russian_number(data.get('akcizStr', '0'))
            vat = self._parse_russian_number(data.get('ndsStr', '0'))

            # Parse totals
            total_str = data.get('total', '0')
            total = self._parse_russian_number(total_str)

            # Validate we got meaningful data
            if total is None or total == 0:
                # Try alternative total
                total2_str = data.get('total2', '0')
                total = self._parse_russian_number(total2_str)

            if total is None:
                logger.warning("Failed to parse total from calcus.ru response")
                return CalcusCalculationResponse(
                    success=False,
                    car_id=request.car_id,
                    error="Failed to parse calculation result"
                )

            # Build customs breakdown
            customs = CalcusCustomsBreakdown(
                clearance_cost=clearance_cost or 0,
                utilization_fee=utilization_fee or 0,
                customs_duty=customs_duty or 0,
                excise=excise or 0,
                vat=vat or 0,
                total=total
            )

            logger.info(
                f"Parsed calcus.ru result: "
                f"clearance={customs.clearance_cost}, "
                f"util={customs.utilization_fee}, "
                f"duty={customs.customs_duty}, "
                f"total={customs.total}"
            )

            return CalcusCalculationResponse(
                success=True,
                car_id=request.car_id,
                customs=customs,
                input_params={
                    'price_krw': request.price_krw,
                    'displacement': request.displacement,
                    'year': request.year,
                    'power': request.power,
                    'engine_type': request.engine_type,
                    'calculation_year': '2026'
                },
                meta={
                    'source': 'calcus.ru',
                    'calculated_at': datetime.now().isoformat(),
                    'raw_total': total_str
                }
            )

        except Exception as e:
            logger.error(f"Error parsing calcus.ru response: {str(e)}")
            return CalcusCalculationResponse(
                success=False,
                car_id=request.car_id,
                error=f"Failed to parse response: {str(e)}"
            )

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""

        return {
            **self.stats,
            'cache_size': len(self.cache)
        }

    def clear_cache(self):
        """Clear all cached results"""

        with self.cache_lock:
            self.cache.clear()
            logger.info("Calcus.ru cache cleared")


# Singleton instance
_calcus_service_instance: Optional[CalcusService] = None


def get_calcus_service() -> CalcusService:
    """Get or create calcus.ru service singleton"""

    global _calcus_service_instance

    if _calcus_service_instance is None:
        _calcus_service_instance = CalcusService()

    return _calcus_service_instance
