"""
Che168 Service
Business logic layer for Chinese car marketplace integration
"""

import asyncio
import json
import logging
import time
import random
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, Timeout, ConnectionError

from parsers.bravomotors_parser import Che168Parser
from schemas.bravomotors import (
    Che168SearchResponse,
    Che168FiltersResponse,
    Che168SearchFilters,
    Che168BrandsResponse,
    TranslationResponse,
)
from schemas.che168 import (
    Che168CarInfoResponse,
    Che168CarParamsResponse,
    Che168CarAnalysisResponse,
    Che168CarDetailResponse,  # Use correct schema from che168
)

# Import request cache utility
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lib.request_cache import RequestCache

logger = logging.getLogger(__name__)


class Che168Service:
    """
    Che168 service for Chinese car marketplace integration

    Provides comprehensive functionality for:
    - Car search with filters and pagination
    - Individual car detail retrieval
    - Service filter options
    - Session management with Chinese site requirements
    - Request signing for API authentication
    """

    def __init__(self, proxy_client=None):
        self.proxy_client = proxy_client
        self.parser = Che168Parser()
        self.base_url = "https://api2scsou.che168.com"
        self.mobile_url = "https://m.che168.com"

        # Session management
        self.session = requests.Session()

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        # Cache for session persistence
        self.session_cookies = {}
        self.device_id = "e51c9bd2-efd9-4aaa-b0bd-4f0fd92d9f84"

        # Failed request cache (5 minute TTL for 404s)
        self.failed_request_cache = RequestCache(max_size=500, default_ttl=300)

        # Circuit breaker state
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_reset = time.time()
        self.circuit_breaker_cooldown_until = 0

        # Setup session after device_id is defined
        self._setup_session()

    def _setup_session(self):
        """Setup session with Chinese site requirements"""
        # Chinese site specific headers (from cars.py example)
        self.session.headers.update(
            {
                "accept": "*/*",
                "accept-language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
                "origin": "https://m.che168.com",
                "priority": "u=1, i",
                "referer": "https://m.che168.com/",
                "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            }
        )

        # Set up cookies from cars.py example
        cookies = {
            "fvlid": "175765024666870S5QR2lY0E5",
            "sessionid": self.device_id,
            "sessionip": "1.228.56.78",
            "area": "0",
            "che_sessionid": "65845ADD-8F0D-498F-A254-8B7B4EC47F01%7C%7C2025-09-12+12%3A10%3A47.942%7C%7Cwww.google.com",
            "Hm_lvt_d381ec2f88158113b9b76f14c497ed48": "1757650247,1757841415",
            "HMACCOUNT": "7D5AA048D6828FA7",
            "userarea": "0",
            "listuserarea": "0",
            "sessionvisit": "0e9b80a5-c2ff-4ba7-baf8-79a0256f24ee",
            "sessionvisitInfo": f"{self.device_id}||0",
            "che_sessionvid": "140239D5-014C-434E-ABFF-82B91E2B6D77",
            "Hm_lpvt_d381ec2f88158113b9b76f14c497ed48": str(int(time.time())),
            "showNum": "17",
            "_ac": "TDjKkEvclbcQ7E0PG_UvuH0jdR8JW5ShH2qwXbTIr4OJITU9lHrR",
            "KEY_LOCATION_CITY_GEO_DATE": "2025915",
            "ahpvno": "7",
            "ahuuid": "1F965AC4-0F18-4209-BD3F-2D89C5E74F0C",
            "v_no": "16",
            "visit_info_ad": "65845ADD-8F0D-498F-A254-8B7B4EC47F01||140239D5-014C-434E-ABFF-82B91E2B6D77||-1||-1||16",
            "che_ref": "www.google.com%7C0%7C0%7C0%7C2025-09-15+07%3A27%3A45.576%7C2025-09-12+12%3A10%3A47.942",
            "sessionuid": self.device_id,
        }

        self.session.cookies.update(cookies)

        # Session configuration
        self.session.timeout = (10, 30)  # connect, read timeout
        self.session.max_redirects = 3

        # Connection pooling with retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )

        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=100,
            max_retries=retry_strategy,
            pool_block=False
        )

        # Mount adapter for both HTTP and HTTPS
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Cache for brands/models/years to reduce API calls
        self.brands_cache = None
        self.brands_cache_time = 0
        self.models_cache = {}
        self.years_cache = {}

    async def _rate_limit(self):
        """Rate limiting to avoid being blocked (async-compatible)"""
        current_time = time.time()
        if current_time - self.last_request_time < 0.5:  # 500ms between requests
            await asyncio.sleep(0.5 - (current_time - self.last_request_time))

        self.last_request_time = time.time()
        self.request_count += 1

        # Add random delay occasionally
        if self.request_count % 20 == 0:
            await asyncio.sleep(random.uniform(1.0, 3.0))

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        Generate _sign parameter for API authentication
        Based on the pattern from cars.py example
        """
        try:
            # Create a deterministic but seemingly random sign
            # This is a simplified version - in practice, you'd need to reverse engineer the actual algorithm
            param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if k != "_sign")
            param_string += f"&deviceid={self.device_id}&timestamp={int(time.time())}"

            # Generate MD5 hash as sign (simplified approach)
            sign = hashlib.md5(param_string.encode()).hexdigest()
            return sign
        except Exception as e:
            logger.warning(f"Failed to generate sign: {str(e)}")
            # Fallback to example sign from cars.py
            return "1af9c29a34a656070bfa923b31e570eb"

    def _is_retriable_error(self, exception: Exception) -> bool:
        """
        Determine if an error should be retried

        Retriable errors:
        - 5xx server errors (temporary server issues)
        - Network timeouts
        - Connection errors

        Non-retriable errors:
        - 404 Not Found (resource doesn't exist)
        - 400 Bad Request (invalid parameters)
        - 401/403 Authentication/Authorization errors
        """
        if isinstance(exception, Timeout):
            return True

        if isinstance(exception, ConnectionError):
            return True

        if isinstance(exception, RequestException):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                # Only retry 5xx errors
                return 500 <= status_code < 600

        return False

    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker is open (requests should be blocked)

        Returns:
            True if requests are allowed, False if circuit is open
        """
        current_time = time.time()

        # Reset failure counter every 60 seconds
        if current_time - self.circuit_breaker_last_reset > 60:
            self.circuit_breaker_failures = 0
            self.circuit_breaker_last_reset = current_time

        # Check if in cooldown period
        if current_time < self.circuit_breaker_cooldown_until:
            remaining = int(self.circuit_breaker_cooldown_until - current_time)
            logger.warning(f"Circuit breaker is OPEN - cooldown for {remaining}s more")
            return False

        return True

    async def _make_request(
        self, url: str, params: Dict = None, use_proxy: bool = False, max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Make HTTP request with intelligent error handling and retry logic

        Args:
            url: Target URL
            params: Query parameters
            use_proxy: Whether to use proxy client
            max_retries: Maximum retry attempts (default: 1, only for retriable errors)

        Returns:
            JSON response data
        """
        await self._rate_limit()

        if params is None:
            params = {}

        # Add required parameters
        params.update({
            "deviceid": self.device_id,
            "userid": "0",
            "s_pid": "0",
            "s_cid": "0",
            "_appid": "2sc.m",
            "v": "11.41.5",
        })

        # Generate signature
        params["_sign"] = self._generate_sign(params)

        # Check cache for failed requests first
        cached_response = self.failed_request_cache.get(url, params)
        if cached_response is not None:
            return cached_response

        # Check circuit breaker
        if not self._check_circuit_breaker():
            return {
                "returncode": 503,
                "message": "Service temporarily unavailable (circuit breaker open)",
                "result": {},
            }

        request_start_time = time.time()
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if use_proxy and self.proxy_client:
                    # Use proxy client if available
                    response = self.proxy_client.session.get(url, params=params)
                else:
                    # Use regular session
                    response = self.session.get(url, params=params)

                response.raise_for_status()

                # Parse JSON response
                json_data = response.json()

                # Log slow requests
                request_time = time.time() - request_start_time
                if request_time > 5.0:
                    logger.warning(f"Slow request detected: {url} took {request_time:.2f}s")

                # Reset circuit breaker on success
                self.circuit_breaker_failures = 0

                return json_data

            except RequestException as e:
                last_exception = e
                status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') and e.response else None

                # Log appropriately based on error type
                if status_code == 404:
                    logger.info(f"Resource not found (404): {url} - infoid may be invalid or car delisted")
                elif status_code and 400 <= status_code < 500:
                    logger.warning(f"Client error ({status_code}): {url} - {str(e)}")
                else:
                    logger.warning(f"Request attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}")

                # Check if error is retriable
                is_retriable = self._is_retriable_error(e)

                # Cache non-retriable errors (404, 400, etc.) to prevent redundant requests
                if not is_retriable and status_code:
                    error_response = {
                        "returncode": status_code,
                        "message": f"Request failed with {status_code}: {str(e)}",
                        "result": {},
                    }
                    # Cache 404s for 5 minutes, other client errors for 1 minute
                    ttl = 300 if status_code == 404 else 60
                    self.failed_request_cache.set(url, error_response, params, ttl=ttl)

                    # Update circuit breaker
                    self.circuit_breaker_failures += 1
                    if self.circuit_breaker_failures >= 10:  # 10 failures in 1 minute
                        self.circuit_breaker_cooldown_until = time.time() + 10
                        logger.error(f"Circuit breaker OPENED - too many failures ({self.circuit_breaker_failures})")

                    return error_response

                # Only retry if error is retriable and we have retries left
                if is_retriable and attempt < max_retries:
                    # Exponential backoff with async sleep (non-blocking)
                    backoff_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                    logger.info(f"Retriable error, retrying in {backoff_time:.1f}s...")
                    await asyncio.sleep(backoff_time)
                    continue
                else:
                    # No more retries or non-retriable error
                    self.circuit_breaker_failures += 1
                    if self.circuit_breaker_failures >= 10:
                        self.circuit_breaker_cooldown_until = time.time() + 10
                        logger.error(f"Circuit breaker OPENED - too many failures ({self.circuit_breaker_failures})")

                    return {
                        "returncode": status_code or 1,
                        "message": f"Request failed: {str(e)}",
                        "result": {},
                    }

            except Exception as e:
                logger.error(f"Unexpected error in request: {str(e)}")
                return {
                    "returncode": 1,
                    "message": f"Unexpected error: {str(e)}",
                    "result": {},
                }

        # Should not reach here, but handle it gracefully
        return {
            "returncode": 1,
            "message": f"Request failed after {max_retries + 1} attempts: {str(last_exception)}",
            "result": {},
        }

    async def search_cars(self, filters: Che168SearchFilters) -> Che168SearchResponse:
        """
        Search cars with specified filters

        Args:
            filters: Search filter parameters

        Returns:
            Che168SearchResponse with search results
        """
        try:
            url = f"{self.base_url}/api/v11/search"

            # Convert filters to API parameters
            params = {
                "pageindex": str(filters.pageindex),
                "pagesize": str(filters.pagesize),
                "ishideback": str(filters.ishideback),
                "service": str(filters.service) if filters.service else "50",
                "srecom": str(filters.srecom),
                "personalizedpush": str(filters.personalizedpush),
                "cid": str(filters.cid),
                "iscxcshowed": str(filters.iscxcshowed),
                "scene_no": str(filters.scene_no),
                "pageid": f"{int(time.time())}_4145",
                "existtags": getattr(filters, 'existtags', ''),
                "pid": str(filters.pid),
                "testtype": getattr(filters, 'testtype', ''),
                "test102223": getattr(filters, 'test102223', ''),
                "testnewcarspecid": getattr(filters, 'testnewcarspecid', ''),
                "test102797": getattr(filters, 'test102797', ''),
                "otherstatisticsext": "%7B%22history%22%3A%22%E5%88%97%E8%A1%A8%E9%A1%B5%22%2C%22pvareaid%22%3A%220%22%2C%22eventid%22%3A%22usc_2sc_mc_mclby_cydj_click%22%7D",
                "filtertype": str(filters.filtertype),
                "ssnew": str(filters.ssnew),
            }

            # Add brand/model/year filters if provided
            if filters.brandid:
                params["brandid"] = str(filters.brandid)
            if filters.seriesid:
                params["seriesid"] = str(filters.seriesid)
            if filters.seriesyearid:
                params["seriesyearid"] = str(filters.seriesyearid)
            if filters.specid:
                params["specid"] = str(filters.specid)
            if filters.sort:
                params["sort"] = str(filters.sort)

            json_data = await self._make_request(url, params)
            result = self.parser.parse_car_search_response(json_data)

            return result

        except Exception as e:
            logger.error(f"Error in search_cars: {str(e)}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={},
                success=False
            )

    async def get_car_detail(self, info_id: int) -> Che168CarDetailResponse:
        """
        Get detailed information for a specific car

        This method now uses the working endpoints:
        - /car/getcarinfo for basic information
        - /car/getparamtypeitems for detailed parameters

        These are fetched in parallel for better performance.

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarDetailResponse with car details
        """
        try:
            # Fetch car info and params in parallel using the working endpoints
            car_info_task = self.get_car_info(info_id)
            car_params_task = self.get_car_params(info_id)

            # Wait for both requests to complete
            car_info_response, car_params_response = await asyncio.gather(
                car_info_task,
                car_params_task,
                return_exceptions=True
            )

            # Check if requests failed
            if isinstance(car_info_response, Exception):
                logger.error(f"Error fetching car info for {info_id}: {str(car_info_response)}")
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error=f"Failed to fetch car info: {str(car_info_response)}"
                )

            if isinstance(car_params_response, Exception):
                logger.error(f"Error fetching car params for {info_id}: {str(car_params_response)}")
                # We can still return partial data if we have car info
                car_params_response = Che168CarParamsResponse(
                    returncode=0,
                    message="Params not available",
                    result=[]
                )

            # Check if car info is valid
            if car_info_response.returncode != 0:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error=car_info_response.message or "Car info not found"
                )

            # Build a car object from car_info data (matching frontend Che168Car interface)
            if car_info_response.result:
                info_data = car_info_response.result

                # Extract image URLs from picList
                pic_list = info_data.get('picList', [])
                image_url = pic_list[0] if pic_list else ""

                # Create a car object that matches the frontend Che168Car interface
                car_object = {
                    "infoid": info_data.get('infoid', 0),
                    "carname": info_data.get('carname', ''),
                    "cname": info_data.get('cname', ''),
                    "dealerid": info_data.get('dealerid', 0),
                    "mileage": str(info_data.get('mileage', '')),
                    "cityid": info_data.get('cityid', 0),
                    "seriesid": info_data.get('seriesid', 0),
                    "specid": info_data.get('specid', 0),
                    "sname": info_data.get('sname', ''),
                    "syname": info_data.get('syname', ''),
                    "price": str(info_data.get('price', '')),
                    "saveprice": str(info_data.get('saveprice', '')),
                    "discount": str(info_data.get('discount', '')),
                    "firstregyear": str(info_data.get('firstregyear', '')),
                    "imageurl": image_url,
                    "displacement": info_data.get('displacement', ''),
                    "environmental": info_data.get('environmental', ''),
                    "brandname": info_data.get('brandname', ''),
                    "seriesname": info_data.get('seriesname', ''),
                    "countyname": info_data.get('countyname', ''),
                    "firstregdate": info_data.get('firstregdate', ''),
                    "picList": pic_list,
                    "gearbox": info_data.get('gearbox', ''),
                    "colorname": info_data.get('colorname', ''),
                    "transfercount": info_data.get('transfercount', 0),
                    "fromtype": info_data.get('fromtype', 0),
                    "cartype": info_data.get('cartype', 0),
                    "bucket": info_data.get('bucket', 0),
                    "isunion": info_data.get('isunion', 0),
                    "isoutsite": info_data.get('isoutsite', 0),
                    "videourl": info_data.get('videourl', ''),
                    "car_level": info_data.get('car_level', 0),
                    "dealer_level": str(info_data.get('dealer_level', '')),
                    "downpayment": str(info_data.get('downpayment', '')),
                    "url": info_data.get('url', ''),
                    "position": info_data.get('position', 0),
                    "isnewly": info_data.get('isnewly', 0),
                    "kindname": info_data.get('kindname', ''),
                    "photocount": info_data.get('photocount', 0),
                }

                # Add parameter sections as a separate field for UI rendering
                param_sections = []
                if car_params_response.returncode == 0 and car_params_response.result:
                    param_sections = car_params_response.result

                # Return response with car object (matching frontend expectations)
                return Che168CarDetailResponse(
                    success=True,
                    car=car_object,
                    meta={"params": param_sections}
                )
            else:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error="No car details found"
                )

        except Exception as e:
            logger.error(f"Error in get_car_detail for {info_id}: {str(e)}")
            return Che168CarDetailResponse(
                success=False,
                car=None,
                error=f"Service error: {str(e)}"
            )

    async def get_filters(self) -> Che168FiltersResponse:
        """
        Get available filter options

        Returns:
            Che168FiltersResponse with available filters
        """
        try:
            # Get brands first
            brands_result = await self.get_brands()

            if not brands_result.returncode == 0:
                return Che168FiltersResponse(
                    success=False,
                    brands=[],
                    price_ranges=[],
                    age_ranges=[],
                    mileage_ranges=[],
                    fuel_types=[],
                    transmissions=[],
                    displacements=[]
                )

            # Create structured filters response using parser
            all_brands = []
            for brand_group in brands_result.result.values():
                if isinstance(brand_group, list):
                    all_brands.extend(brand_group)

            result = self.parser.create_filters_response(all_brands)
            return result

        except Exception as e:
            logger.error(f"Error in get_filters: {str(e)}")
            return Che168FiltersResponse(
                success=False,
                brands=[],
                price_ranges=[],
                age_ranges=[],
                mileage_ranges=[],
                fuel_types=[],
                transmissions=[],
                displacements=[]
            )

    def update_cookies(self, new_cookies: Dict[str, str]):
        """Update session cookies"""
        self.session.cookies.update(new_cookies)
        self.session_cookies.update(new_cookies)

    async def get_brands(self) -> Che168BrandsResponse:
        """
        Get all available car brands from Che168

        Returns:
            Che168BrandsResponse with all available brands
        """
        try:
            # Check cache first (cache for 1 hour)
            current_time = time.time()
            if self.brands_cache and (current_time - self.brands_cache_time) < 3600:
                return self.brands_cache

            url = f"{self.base_url}/api/v2/getbrands"

            # Use minimal parameters similar to brands.py example
            params = {
                "cid": "0",
                "pid": "0",
                "isenergy": "0",
                "s_pid": "0",
                "s_cid": "0",
            }

            json_data = await self._make_request(url, params)
            result = self.parser.parse_brands_response(json_data)

            # Cache the result
            if result.returncode == 0:
                self.brands_cache = result
                self.brands_cache_time = current_time

            return result

        except Exception as e:
            logger.error(f"Error in get_brands: {str(e)}")
            return Che168BrandsResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={}
            )

    async def get_models(self, brand_id: int) -> Che168SearchResponse:
        """
        Get available models for a specific brand

        Args:
            brand_id: Brand ID to get models for

        Returns:
            Che168SearchResponse with search results containing model filters
        """
        try:
            # Check cache first
            cache_key = f"brand_{brand_id}"
            if cache_key in self.models_cache:
                cached_result, cache_time = self.models_cache[cache_key]
                if (time.time() - cache_time) < 1800:  # 30 minutes cache
                    return cached_result

            # Make search request with brand ID to get models from filters
            url = f"{self.base_url}/api/v11/search"
            params = {
                "pageindex": "1",
                "pagesize": "1",
                "ishideback": "1",
                "brandid": str(brand_id),
                "srecom": "2",
                "personalizedpush": "1",
                "cid": "0",
                "iscxcshowed": "-1",
                "scene_no": "12",
                "pageid": f"{int(time.time())}_4145",
                "existtags": "6",
                "pid": "0",
                "testtype": "X",
                "test102223": "X",
                "testnewcarspecid": "X",
                "test102797": "X",
                "otherstatisticsext": "%7B%22history%22%3A%22%E5%88%97%E8%A1%A8%E9%A1%B5%22%2C%22pvareaid%22%3A%220%22%2C%22eventid%22%3A%22usc_2sc_mc_mclby_cydj_click%22%7D",
                "filtertype": "0",
                "ssnew": "1",
            }

            # Get raw response to extract models from filters
            raw_response = await self._make_request(url, params)

            if raw_response.get("returncode") != 0:
                return Che168SearchResponse(
                    returncode=raw_response.get("returncode", -1),
                    message=raw_response.get('message', 'Unknown error'),
                    result={},
                    success=False
                )

            # Parse the response with models in filters
            result = self.parser.parse_car_search_response(raw_response)

            # Extract models from filters array for easier frontend consumption
            models = []
            if result.filters:
                for filter_item in result.filters:
                    # Look for series/model filters (key = "seriesid")
                    if filter_item.key == "seriesid":
                        models.append({
                            "id": int(filter_item.value),
                            "name": filter_item.title,
                            "icon": getattr(filter_item, 'icon', ''),
                            "tag": getattr(filter_item, 'tag', ''),
                            "value": filter_item.value,
                            "title": filter_item.title,
                            "subtitle": getattr(filter_item, 'subtitle', ''),
                        })

            # Add models array to result for frontend compatibility
            if hasattr(result, 'result') and isinstance(result.result, dict):
                result.result['models'] = models
                result.result['series'] = models  # Also add as series for backward compatibility

            # Cache the result
            self.models_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Error in get_models for brand {brand_id}: {str(e)}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={},
                success=False
            )

    async def get_years(self, brand_id: int, series_id: int) -> Che168SearchResponse:
        """
        Get available years for a specific brand and model

        Args:
            brand_id: Brand ID
            series_id: Series (model) ID

        Returns:
            Che168SearchResponse with search results containing year filters
        """
        try:
            # Check cache first
            cache_key = f"brand_{brand_id}_series_{series_id}"
            if cache_key in self.years_cache:
                cached_result, cache_time = self.years_cache[cache_key]
                if (time.time() - cache_time) < 1800:  # 30 minutes cache
                    return cached_result

            # Make search request with brand and series ID to get years from filters
            url = f"{self.base_url}/api/v11/search"
            params = {
                "pageindex": "1",
                "pagesize": "1",
                "ishideback": "1",
                "brandid": str(brand_id),
                "seriesid": str(series_id),
                "srecom": "2",
                "personalizedpush": "1",
                "cid": "0",
                "iscxcshowed": "-1",
                "scene_no": "12",
                "pageid": f"{int(time.time())}_4375",
                "existtags": "6",
                "pid": "0",
                "testtype": "X",
                "test102223": "X",
                "testnewcarspecid": "X",
                "test102797": "X",
                "otherstatisticsext": "%7B%22history%22%3A%22%E5%88%97%E8%A1%A8%E9%A1%B5%22%2C%22pvareaid%22%3A%220%22%2C%22eventid%22%3A%22usc_2sc_mc_mclby_cydj_click%22%7D",
                "filtertype": "0",
                "ssnew": "1",
            }

            # Get raw response to extract years from filters
            raw_response = await self._make_request(url, params)

            if raw_response.get("returncode") != 0:
                return Che168SearchResponse(
                    returncode=raw_response.get("returncode", -1),
                    message=raw_response.get('message', 'Unknown error'),
                    result={},
                    success=False
                )

            # Parse the response with years in filters
            result = self.parser.parse_car_search_response(raw_response)

            # Extract years from filters array for easier frontend consumption
            years = []
            if result.filters:
                for filter_item in result.filters:
                    # Look for year filters (key = "seriesyearid")
                    if filter_item.key == "seriesyearid":
                        years.append({
                            "id": int(filter_item.value),
                            "name": filter_item.title,
                            "value": filter_item.value,
                            "title": filter_item.title,
                            "subtitle": getattr(filter_item, 'subtitle', ''),
                        })

            # Add years array to result for frontend compatibility
            if hasattr(result, 'result') and isinstance(result.result, dict):
                result.result['years'] = years

            # Cache the result
            self.years_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Error in get_years for brand {brand_id}, series {series_id}: {str(e)}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={},
                success=False
            )

    async def translate_text(self, text: str, target_language: str = "ru") -> TranslationResponse:
        """
        Translate Chinese text to target language (Russian by default)

        Args:
            text: Chinese text to translate
            target_language: Target language code (default: "ru")

        Returns:
            TranslationResponse with translation result
        """
        try:
            # In a real implementation, you would use a translation service like:
            # - Google Translate API
            # - Baidu Translate API
            # - Microsoft Translator
            # - Or a local translation model

            # For now, return a placeholder implementation
            # This should be replaced with actual translation service

            translation_data = {
                "originalText": text,
                "translatedText": text,  # Placeholder - should be actual translation
                "sourceLanguage": "zh-cn",
                "targetLanguage": target_language,
                "type": "analysis",
                "isStatic": False,
                "isCached": False,
                "success": True
            }

            result = self.parser.parse_translation_response(translation_data)
            return result

        except Exception as e:
            logger.error(f"Error in translate_text: {str(e)}")
            return TranslationResponse(
                original_text=text,
                translated_text=text,
                source_language="zh-cn",
                target_language=target_language,
                type="analysis",
                success=False
            )

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information including cache statistics"""
        return {
            "device_id": self.device_id,
            "request_count": self.request_count,
            "cookies_count": len(self.session.cookies),
            "last_request": self.last_request_time,
            "cache_status": {
                "brands_cached": self.brands_cache is not None,
                "models_cache_size": len(self.models_cache),
                "years_cache_size": len(self.years_cache),
            },
            "failed_request_cache": self.failed_request_cache.get_stats(),
            "circuit_breaker": {
                "failures": self.circuit_breaker_failures,
                "is_open": time.time() < self.circuit_breaker_cooldown_until,
                "cooldown_remaining": max(0, int(self.circuit_breaker_cooldown_until - time.time()))
            }
        }

    async def get_car_info(self, info_id: int) -> Che168CarInfoResponse:
        """
        Get basic car information using Che168 getcarinfo API

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarInfoResponse with basic car information
        """
        try:
            url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"

            params = {
                "infoid": str(info_id),
                "_appid": "2sc.m"
            }

            # Use proxy client to avoid 514 rate limiting errors
            if self.proxy_client and hasattr(self.proxy_client, 'session'):
                response = self.proxy_client.session.get(url, params=params)
            else:
                response = self.session.get(url, params=params)
            response.raise_for_status()
            json_data = response.json()

            # Create response using the schema
            if json_data.get("returncode") == 0 and "result" in json_data:
                result_data = json_data["result"]

                return Che168CarInfoResponse(
                    returncode=json_data.get("returncode", 0),
                    message=json_data.get("message", "Success"),
                    result=result_data
                )
            else:
                return Che168CarInfoResponse(
                    returncode=json_data.get("returncode", -1),
                    message=json_data.get("message", "Failed to get car info"),
                    result={}
                )

        except Exception as e:
            logger.error(f"Error in get_car_info for {info_id}: {str(e)}")
            return Che168CarInfoResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={}
            )

    async def get_car_params(self, info_id: int) -> Che168CarParamsResponse:
        """
        Get detailed car parameters using Che168 getparamtypeitems API

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarParamsResponse with car specifications
        """
        try:
            url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"

            params = {
                "infoid": str(info_id),
                "_appid": "2sc.m"
            }

            # Use proxy client to avoid 514 rate limiting errors
            if self.proxy_client and hasattr(self.proxy_client, 'session'):
                response = self.proxy_client.session.get(url, params=params)
            else:
                response = self.session.get(url, params=params)
            response.raise_for_status()
            json_data = response.json()

            # Create response using the schema
            if json_data.get("returncode") == 0 and "result" in json_data:
                result_data = json_data["result"]

                return Che168CarParamsResponse(
                    returncode=json_data.get("returncode", 0),
                    message=json_data.get("message", "Success"),
                    result=result_data
                )
            else:
                return Che168CarParamsResponse(
                    returncode=json_data.get("returncode", -1),
                    message=json_data.get("message", "Failed to get car params"),
                    result=[]
                )

        except Exception as e:
            logger.error(f"Error in get_car_params for {info_id}: {str(e)}")
            return Che168CarParamsResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result=[]
            )

    async def get_car_analysis(self, info_id: int) -> Che168CarAnalysisResponse:
        """
        Get car analysis and evaluation using Che168 getcaranalysis API
        Note: This endpoint is currently not available on Che168 API

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarAnalysisResponse with car analysis data
        """
        try:
            # The getcaranalysis endpoint is not available on Che168 API
            # Return a default response indicating no analysis data available
            logger.info(f"Car analysis not available for {info_id} - endpoint does not exist")
            return Che168CarAnalysisResponse(
                returncode=0,
                message="Analysis data not available for this vehicle",
                result={}
            )

        except Exception as e:
            logger.error(f"Error in get_car_analysis for {info_id}: {str(e)}")
            return Che168CarAnalysisResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={}
            )