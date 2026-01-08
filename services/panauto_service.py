"""
Pan-Auto.ru Car Data Service
Fetches car data including HP and pre-calculated customs from pan-auto.ru API

The pan-auto.ru API provides:
- HP (horsepower) values
- Pre-calculated customs duties for 2026 rules
- Full cost breakdowns in RUB and USD
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import requests
from dataclasses import dataclass
import threading

from schemas.customs_russia import (
    PanAutoCarData,
    PanAutoCarResponse,
    PanAutoCostsRUB
)

logger = logging.getLogger(__name__)


@dataclass
class CachedPanAutoResult:
    """Cached pan-auto.ru car data"""

    response: PanAutoCarResponse
    created_at: datetime
    ttl_seconds: int = 3600  # 1 hour cache

    @property
    def is_expired(self) -> bool:
        """Check if cached result is expired"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)


class PanAutoService:
    """
    Pan-Auto.ru car data service

    Features:
    - Fetches car data from zefir.pan-auto.ru API
    - Extracts HP and pre-calculated customs
    - Caches results for 1 hour
    - Handles errors gracefully
    - Returns structured response for frontend
    """

    BASE_URL = "https://zefir.pan-auto.ru"
    API_ENDPOINT = "/api/cars/{car_id}/"

    # User-Agent pool for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    ]

    def __init__(self):
        """Initialize Pan-Auto service"""

        # Caching
        self.cache: Dict[str, CachedPanAutoResult] = {}
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
            'cars_with_hp': 0,
            'cars_without_hp': 0
        }

        self._setup_session()

    def _setup_session(self):
        """Setup HTTP session with proper headers"""

        user_agent = self.USER_AGENTS[self.current_user_agent_index]

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5',
            'Connection': 'keep-alive',
            'Origin': 'https://pan-auto.ru',
            'Referer': 'https://pan-auto.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': user_agent,
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }

        self.session.headers.update(headers)

    def _rotate_user_agent(self):
        """Rotate User-Agent for next request"""

        self.current_user_agent_index = (
            self.current_user_agent_index + 1
        ) % len(self.USER_AGENTS)

        user_agent = self.USER_AGENTS[self.current_user_agent_index]
        self.session.headers['User-Agent'] = user_agent

    def _get_cache_key(self, car_id: str) -> str:
        """Generate cache key for car ID"""
        return f"panauto_car_{car_id}"

    def _get_cached_result(self, car_id: str) -> Optional[PanAutoCarResponse]:
        """Get cached result if valid"""

        cache_key = self._get_cache_key(car_id)

        with self.cache_lock:
            cached = self.cache.get(cache_key)
            if cached and not cached.is_expired:
                self.stats['cache_hits'] += 1
                logger.info(f"Cache hit for car {car_id}")
                return cached.response
            elif cached:
                # Remove expired cache entry
                del self.cache[cache_key]

        self.stats['cache_misses'] += 1
        return None

    def _cache_result(self, car_id: str, response: PanAutoCarResponse):
        """Cache car data result"""

        cache_key = self._get_cache_key(car_id)

        with self.cache_lock:
            self.cache[cache_key] = CachedPanAutoResult(
                response=response,
                created_at=datetime.now()
            )

    async def get_car_data(self, car_id: str, force_refresh: bool = False) -> PanAutoCarResponse:
        """
        Fetch car data from pan-auto.ru API

        Args:
            car_id: Encar car ID
            force_refresh: Skip cache and force fresh fetch

        Returns:
            PanAutoCarResponse with HP and customs data (if available)
        """

        # Check cache first
        if not force_refresh:
            cached = self._get_cached_result(car_id)
            if cached:
                return cached

        # Make API request
        try:
            result = await self._fetch_from_api(car_id)

            # Cache successful result
            if result.success:
                self._cache_result(car_id, result)

                # Update stats
                if result.has_hp:
                    self.stats['cars_with_hp'] += 1
                else:
                    self.stats['cars_without_hp'] += 1

            return result

        except Exception as e:
            self.stats['api_failures'] += 1
            logger.error(f"Failed to fetch car data for {car_id}: {str(e)}")

            return PanAutoCarResponse(
                success=False,
                car_id=car_id,
                has_hp=False,
                has_customs=False,
                error=f"Failed to fetch car data: {str(e)}"
            )

    async def _fetch_from_api(self, car_id: str) -> PanAutoCarResponse:
        """Make actual API request to pan-auto.ru"""

        # Rotate user agent for each request
        self._rotate_user_agent()

        # Add small random delay to avoid rate limiting
        delay = random.uniform(0.3, 1.0)
        await asyncio.sleep(delay)

        url = f"{self.BASE_URL}{self.API_ENDPOINT.format(car_id=car_id)}"

        logger.info(f"Fetching car data from pan-auto.ru: {car_id}")

        try:
            response = self.session.get(url, timeout=15)
            self.stats['api_calls_made'] += 1

            if response.status_code == 200:
                data = response.json()
                return self._parse_response(car_id, data)

            elif response.status_code == 404:
                logger.info(f"Car {car_id} not found on pan-auto.ru")
                return PanAutoCarResponse(
                    success=False,
                    car_id=car_id,
                    has_hp=False,
                    has_customs=False,
                    error="Car not found on pan-auto.ru"
                )

            else:
                logger.warning(f"Pan-auto.ru API returned status {response.status_code}")
                return PanAutoCarResponse(
                    success=False,
                    car_id=car_id,
                    has_hp=False,
                    has_customs=False,
                    error=f"Pan-auto.ru API error: HTTP {response.status_code}"
                )

        except requests.Timeout:
            logger.warning(f"Timeout fetching car {car_id} from pan-auto.ru")
            return PanAutoCarResponse(
                success=False,
                car_id=car_id,
                has_hp=False,
                has_customs=False,
                error="Request timeout"
            )

        except requests.RequestException as e:
            logger.error(f"Request error fetching car {car_id}: {str(e)}")
            raise

    def _parse_response(self, car_id: str, data: dict) -> PanAutoCarResponse:
        """Parse pan-auto.ru API response"""

        try:
            # Extract HP
            hp = data.get('hp')
            has_hp = hp is not None and isinstance(hp, (int, float)) and hp > 0

            # Extract costs
            costs = data.get('costs', {})
            costs_rub_data = costs.get('RUB', {})

            # Check if we have valid customs data
            has_customs = (
                costs_rub_data and
                costs_rub_data.get('clearanceCost') is not None and
                costs_rub_data.get('utilizationFee') is not None and
                costs_rub_data.get('customsDuty') is not None
            )

            # Parse costs to Pydantic model
            costs_rub = None
            if has_customs:
                try:
                    costs_rub = PanAutoCostsRUB(
                        carPriceEncar=costs_rub_data.get('carPriceEncar', 0),
                        carPrice=costs_rub_data.get('carPrice', 0),
                        clearanceCost=costs_rub_data.get('clearanceCost', 0),
                        utilizationFee=costs_rub_data.get('utilizationFee', 0),
                        customsDuty=costs_rub_data.get('customsDuty', 0),
                        deliveryRate=costs_rub_data.get('deliveryRate'),
                        deliveryCost=costs_rub_data.get('deliveryCost', 0),
                        vladivostokServices=costs_rub_data.get('vladivostokServices', 0),
                        totalFees=costs_rub_data.get('totalFees', 0),
                        finalCost=costs_rub_data.get('finalCost', 0),
                        dealerCost=costs_rub_data.get('dealerCost', 0)
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse costs for car {car_id}: {e}")
                    has_customs = False
                    costs_rub = None

            # Extract other fields
            manufacturer_data = data.get('manufacturer', {})
            model_data = data.get('model', {})

            response = PanAutoCarResponse(
                success=True,
                car_id=car_id,
                hp=int(hp) if has_hp else None,
                displacement=data.get('displacement'),
                year=data.get('year'),
                form_year=data.get('formYear'),
                fuel_type=data.get('fuelType'),
                mileage=data.get('mileage'),
                costs_rub=costs_rub,
                manufacturer=manufacturer_data.get('name') if manufacturer_data else None,
                model=model_data.get('name') if model_data else None,
                badge=data.get('badge'),
                vin=data.get('vin'),
                has_hp=has_hp,
                has_customs=has_customs,
                meta={
                    'source': 'pan-auto.ru',
                    'fetched_at': datetime.now().isoformat(),
                    'original_id': data.get('id')
                }
            )

            logger.info(
                f"Parsed pan-auto.ru data for car {car_id}: "
                f"HP={response.hp}, has_customs={has_customs}"
            )

            return response

        except Exception as e:
            logger.error(f"Error parsing pan-auto.ru response for car {car_id}: {str(e)}")
            return PanAutoCarResponse(
                success=False,
                car_id=car_id,
                has_hp=False,
                has_customs=False,
                error=f"Failed to parse response: {str(e)}"
            )

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""

        return {
            **self.stats,
            'cache_size': len(self.cache),
            'current_user_agent': self.session.headers.get('User-Agent', 'Unknown')[:50] + '...'
        }

    def clear_cache(self):
        """Clear all cached results"""

        with self.cache_lock:
            self.cache.clear()
            logger.info("Pan-auto.ru cache cleared")

    def clear_expired_cache(self):
        """Remove expired entries from cache"""

        with self.cache_lock:
            expired_keys = [
                key for key, cached in self.cache.items()
                if cached.is_expired
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"Removed {len(expired_keys)} expired pan-auto.ru cache entries")


# Singleton instance
_panauto_service_instance: Optional[PanAutoService] = None


def get_panauto_service() -> PanAutoService:
    """Get or create pan-auto.ru service singleton"""

    global _panauto_service_instance

    if _panauto_service_instance is None:
        _panauto_service_instance = PanAutoService()

    return _panauto_service_instance
