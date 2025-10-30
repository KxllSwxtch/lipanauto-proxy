"""
VLB Broker Customs Calculation Service
High-performance service for calculating customs duties via VLB broker
with advanced caching, rate limiting, and anti-blocking measures
"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import requests
from dataclasses import dataclass
import threading

from schemas.vlb_customs import (
    VLBCustomsRequest,
    VLBCustomsResponse,
    VLBCustomsBreakdown,
    VLBServiceConfig,
    TurnkeyPriceComponents,
    TurnkeyPriceResponse
)
from parsers.vlb_parser import VLBCustomsParser

logger = logging.getLogger(__name__)


@dataclass
class CachedCustomsResult:
    """Cached customs calculation result"""

    customs: VLBCustomsBreakdown
    currency_rates: Dict[str, str]
    created_at: datetime
    ttl_seconds: int = 86400  # 24 hours

    @property
    def is_expired(self) -> bool:
        """Check if cached result is expired"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)


@dataclass
class RateLimitTracker:
    """Track rate limiting per minute"""

    requests_this_minute: List[datetime]
    max_requests: int = 10

    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limit"""
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests_this_minute = [
            req_time for req_time in self.requests_this_minute
            if now - req_time < timedelta(minutes=1)
        ]
        return len(self.requests_this_minute) < self.max_requests

    def record_request(self):
        """Record a new request"""
        self.requests_this_minute.append(datetime.now())


class VLBCustomsService:
    """
    Advanced VLB Broker customs calculation service

    Features:
    - Intelligent caching with 24-hour TTL
    - Rate limiting (10 requests/minute)
    - Session rotation and User-Agent rotation
    - Exponential backoff retry logic
    - Circuit breaker pattern
    - Anti-blocking measures
    """

    # User-Agent pool for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]

    def __init__(self, proxy_client=None):
        """Initialize VLB customs service"""

        self.proxy_client = proxy_client
        self.parser = VLBCustomsParser()
        self.config = VLBServiceConfig()

        # Caching
        self.cache: Dict[str, CachedCustomsResult] = {}
        self.cache_lock = threading.Lock()

        # Rate limiting
        self.rate_limiter = RateLimitTracker(
            requests_this_minute=[],
            max_requests=self.config.max_requests_per_minute
        )

        # Session management
        self.session = requests.Session()
        self.request_count = 0
        self.current_user_agent_index = 0

        # Circuit breaker
        self.consecutive_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = None

        # Performance tracking
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_made': 0,
            'api_failures': 0,
            'average_response_time': 0.0,
            'rate_limited_requests': 0
        }

        self._setup_session()

    def _setup_session(self):
        """Setup HTTP session with proper headers"""

        self._rotate_user_agent()

        base_headers = {
            'Accept': '*/*',
            'Accept-Language': 'en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.config.base_url,
            'Referer': self.config.referer_url,
            'Sec-Ch-Ua': '"Chromium";v="91", " Not=A?Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }

        self.session.headers.update(base_headers)

        # Set timeout
        self.session.timeout = self.config.request_timeout

    def _rotate_user_agent(self):
        """Rotate User-Agent to avoid detection"""

        user_agent = self.USER_AGENTS[self.current_user_agent_index]
        self.session.headers['User-Agent'] = user_agent

        self.current_user_agent_index = (
            self.current_user_agent_index + 1
        ) % len(self.USER_AGENTS)

    def _should_rotate_session(self) -> bool:
        """Check if we should rotate the session"""
        return self.request_count >= self.config.session_rotation_requests

    def _rotate_session(self):
        """Create new session to avoid detection"""

        logger.info("Rotating VLB session to avoid detection")

        self.session.close()
        self.session = requests.Session()
        self.request_count = 0
        self._setup_session()

    def _get_cache_key(self, request: VLBCustomsRequest) -> str:
        """Generate cache key for customs request"""

        return f"vlb_customs_{request.year}_{request.engine_volume}_{request.price}_{request.currency}"

    def _get_cached_result(self, cache_key: str) -> Optional[CachedCustomsResult]:
        """Get cached result if valid"""

        with self.cache_lock:
            cached = self.cache.get(cache_key)
            if cached and not cached.is_expired:
                self.stats['cache_hits'] += 1
                return cached
            elif cached:
                # Remove expired cache entry
                del self.cache[cache_key]

            self.stats['cache_misses'] += 1
            return None

    def _cache_result(self, cache_key: str, customs: VLBCustomsBreakdown,
                     currency_rates: Dict[str, str]):
        """Cache customs calculation result"""

        with self.cache_lock:
            self.cache[cache_key] = CachedCustomsResult(
                customs=customs,
                currency_rates=currency_rates,
                created_at=datetime.now(),
                ttl_seconds=self.config.cache_ttl_seconds
            )

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""

        if self.consecutive_failures >= self.circuit_breaker_threshold:
            if self.circuit_breaker_reset_time is None:
                self.circuit_breaker_reset_time = datetime.now() + timedelta(minutes=5)
                logger.warning("VLB circuit breaker opened - too many consecutive failures")
                return True

            if datetime.now() < self.circuit_breaker_reset_time:
                return True
            else:
                # Reset circuit breaker
                logger.info("Resetting VLB circuit breaker")
                self.consecutive_failures = 0
                self.circuit_breaker_reset_time = None

        return False

    async def calculate_customs(self, request: VLBCustomsRequest,
                              force_refresh: bool = False) -> VLBCustomsResponse:
        """
        Calculate customs duties for a vehicle

        Args:
            request: VLB customs calculation request
            force_refresh: Skip cache and force fresh calculation

        Returns:
            VLBCustomsResponse with customs breakdown or error
        """

        start_time = time.time()

        # Check circuit breaker
        if self._is_circuit_breaker_open():
            return VLBCustomsResponse(
                success=False,
                error="Service temporarily unavailable - please try again later"
            )

        # Generate cache key
        cache_key = self._get_cache_key(request)

        # Try to get from cache
        if not force_refresh:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info(f"Returning cached customs result for {cache_key}")
                return VLBCustomsResponse(
                    success=True,
                    customs=cached_result.customs,
                    currency_rates=cached_result.currency_rates,
                    cached=True,
                    cache_ttl=cached_result.ttl_seconds
                )

        # Check rate limiting
        if not self.rate_limiter.can_make_request():
            self.stats['rate_limited_requests'] += 1

            # Try to return last cached result even if slightly expired
            with self.cache_lock:
                expired_cache = self.cache.get(cache_key)
                if expired_cache:
                    logger.warning("Rate limited - returning expired cache")
                    return VLBCustomsResponse(
                        success=True,
                        customs=expired_cache.customs,
                        currency_rates=expired_cache.currency_rates,
                        cached=True
                    )

            return VLBCustomsResponse(
                success=False,
                error="Rate limit exceeded - please try again in a minute"
            )

        # Make API request
        try:
            result = await self._make_api_request(request)

            # Record successful request
            self.rate_limiter.record_request()
            self.consecutive_failures = 0

            # Cache successful result
            if result.success and result.customs:
                self._cache_result(cache_key, result.customs, result.currency_rates or {})

            # Update performance stats
            response_time = time.time() - start_time
            self._update_response_time_stats(response_time)

            return result

        except Exception as e:
            self.consecutive_failures += 1
            self.stats['api_failures'] += 1
            logger.error(f"VLB customs calculation failed: {str(e)}")

            return VLBCustomsResponse(
                success=False,
                error=f"Customs calculation failed: {str(e)}"
            )

    async def _make_api_request(self, request: VLBCustomsRequest) -> VLBCustomsResponse:
        """Make actual API request to VLB broker"""

        # Check if we should rotate session
        if self._should_rotate_session():
            self._rotate_session()

        # Add random delay to avoid detection
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)

        # Prepare request data
        data = {
            'strategy': request.strategy,
            'html': request.html,
            'nt': request.nt,
            'p': request.p,
            'fiz': request.fiz,
            'price': str(request.price),
            'currency': request.currency,
            'marka_j': request.marka_j,
            'model_j': request.model_j,
            'marka_k': request.marka_k,
            'model_k': request.model_k,
            'm': request.vehicle_type,
            'emin': request.emin,
            'year': str(request.year),
            'v': str(request.engine_volume),
            'ptype': request.ptype,
            'ptype_e': request.ptype_e,
        }

        url = f"{self.config.base_url}{self.config.calculator_endpoint}"

        # Make request with retries
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Making VLB API request (attempt {attempt + 1}/{self.config.max_retries})")

                response = self.session.post(url, data=data)
                self.request_count += 1
                self.stats['api_calls_made'] += 1

                if response.status_code == 200:
                    # Parse response
                    customs = self.parser.parse_customs_response(response.text)
                    if customs:
                        currency_rates = self.parser.extract_currency_rates(response.text)

                        logger.info("Successfully parsed VLB customs response")

                        return VLBCustomsResponse(
                            success=True,
                            customs=customs,
                            currency_rates=currency_rates
                        )
                    else:
                        logger.warning("Failed to parse VLB response - response format may have changed")
                        return VLBCustomsResponse(
                            success=False,
                            error="Failed to parse customs calculation response"
                        )

                elif response.status_code == 429:
                    # Rate limited by server
                    logger.warning(f"VLB server rate limited us: {response.status_code}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

                else:
                    logger.warning(f"VLB API returned status {response.status_code}")
                    if attempt == self.config.max_retries - 1:
                        return VLBCustomsResponse(
                            success=False,
                            error=f"VLB API error: HTTP {response.status_code}"
                        )

            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(wait_time)
                else:
                    raise e

    def _update_response_time_stats(self, response_time: float):
        """Update average response time statistics"""

        if self.stats['average_response_time'] == 0:
            self.stats['average_response_time'] = response_time
        else:
            # Moving average
            self.stats['average_response_time'] = (
                self.stats['average_response_time'] * 0.9 + response_time * 0.1
            )

    def calculate_turnkey_price(self, bike_price_krw: int, customs: VLBCustomsBreakdown,
                               krw_to_rub_rate: float, usd_to_rub_rate: float) -> TurnkeyPriceComponents:
        """
        Calculate complete turnkey price for bike including all costs

        Formula from bike-turnkey.md:
        - Base price + 10% markup
        - Broker Services: 105,000 RUB
        - Korea logistics: 520,000 KRW → RUB
        - Vladivostok logistics: 55,000 RUB
        - Packaging: 500,000 KRW → RUB
        - Customs total (from VLB)
        """

        # Convert base price to RUB
        base_price_rub = int(bike_price_krw * krw_to_rub_rate)

        # Calculate 10% markup
        markup_10_percent = int(base_price_rub * 0.1)

        # Fixed costs
        documents_fee = 105000  # Broker Services fee (Услуги Брокера)

        # Convert variable costs
        korea_logistics_krw = 520000
        korea_logistics_rub = int(korea_logistics_krw * krw_to_rub_rate)

        vladivostok_logistics_usd = 550  # Kept for schema compatibility
        vladivostok_logistics_rub = 55000  # Fixed RUB value (Логистика до Владивостока)

        packaging_krw = 500000
        packaging_rub = int(packaging_krw * krw_to_rub_rate)

        return TurnkeyPriceComponents(
            base_price_krw=bike_price_krw,
            base_price_rub=base_price_rub,
            markup_10_percent=markup_10_percent,
            documents_fee=documents_fee,
            korea_logistics_krw=korea_logistics_krw,
            korea_logistics_rub=korea_logistics_rub,
            vladivostok_logistics_usd=vladivostok_logistics_usd,
            vladivostok_logistics_rub=vladivostok_logistics_rub,
            packaging_krw=packaging_krw,
            packaging_rub=packaging_rub,
            customs_total=customs.total
        )

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""

        return {
            **self.stats,
            'cache_size': len(self.cache),
            'consecutive_failures': self.consecutive_failures,
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'current_user_agent': self.session.headers.get('User-Agent', 'Unknown'),
            'session_request_count': self.request_count
        }

    def clear_cache(self):
        """Clear all cached customs results"""

        with self.cache_lock:
            self.cache.clear()
            logger.info("VLB customs cache cleared")

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
                logger.info(f"Removed {len(expired_keys)} expired cache entries")