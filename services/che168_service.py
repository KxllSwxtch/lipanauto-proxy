"""
Che168 Service - BravoMotors Proxy Implementation
Business logic layer for Chinese car marketplace integration via bravomotorrs.com proxy
"""

import asyncio
import hashlib
import json
import logging
import time
import random
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, Timeout, ConnectionError
from diskcache import Cache

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
    Che168CarDetailResponse,
)

logger = logging.getLogger(__name__)

# BravoMotors Proxy Configuration
BRAVOMOTORS_PROXY_URL = "https://bravomotorrs.com/api/che168/data"

# Che168 API Base URLs (used to construct proxy URLs)
CHE168_SEARCH_API = "https://api2scsou.che168.com"
CHE168_DETAIL_API = "https://apiuscdt.che168.com"

# Cache TTLs (in seconds)
CACHE_TTL_BRANDS = 3600      # 1 hour
CACHE_TTL_MODELS = 1800      # 30 minutes
CACHE_TTL_YEARS = 1800       # 30 minutes
CACHE_TTL_SEARCH = 300       # 5 minutes
CACHE_TTL_CAR_DETAIL = 600   # 10 minutes


class Che168Service:
    """
    Che168 service for Chinese car marketplace integration via BravoMotors proxy

    Routes all requests through bravomotorrs.com/api/che168/data which handles:
    - Request forwarding to che168.com
    - Authentication and session management
    - Rate limiting and anti-bot measures

    Provides comprehensive functionality for:
    - Car search with filters and pagination
    - Individual car detail retrieval
    - Brand/model/year cascading filters
    - Disk-based caching for performance
    """

    def __init__(self, proxy_client=None):
        self.proxy_client = proxy_client  # Not used with BravoMotors proxy
        self.parser = Che168Parser()

        # Session management
        self.session = requests.Session()

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        # Disk-based cache
        self.cache = Cache('/tmp/che168_cache')

        # Circuit breaker state
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_reset = time.time()
        self.circuit_breaker_cooldown_until = 0

        # Setup session
        self._setup_session()

    def _setup_session(self):
        """Setup session with BravoMotors proxy requirements"""
        # Headers matching the user's cURL example
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5',
            'content-type': 'application/json',
            'priority': 'u=1, i',
            'referer': 'https://bravomotorrs.com/catalog/cn',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        })

        # Session configuration
        self.session.timeout = (10, 30)  # connect, read timeout

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

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_proxy_url(self, original_url: str, params: Dict[str, Any] = None) -> str:
        """
        Build bravomotorrs.com proxy URL

        Args:
            original_url: The original che168 API URL (base only, without params)
            params: Query parameters to append

        Returns:
            Proxy URL with encoded che168 URL as parameter
        """
        # Build the full che168 URL with params
        if params:
            param_string = urlencode(params, safe='')
            full_url = f"{original_url}?{param_string}"
        else:
            full_url = original_url

        # URL encode the full che168 URL and wrap with proxy
        encoded_url = quote(full_url, safe='')
        return f"{BRAVOMOTORS_PROXY_URL}?url={encoded_url}"

    def _get_cache_key(self, prefix: str, params: Dict[str, Any] = None) -> str:
        """Generate a cache key from prefix and parameters"""
        if params:
            # Create deterministic hash of params
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
            return f"che168:{prefix}:{param_hash}"
        return f"che168:{prefix}"

    async def _rate_limit(self):
        """Rate limiting for BravoMotors proxy (200ms between requests)"""
        current_time = time.time()
        min_interval = 0.2  # 200ms between requests

        if current_time - self.last_request_time < min_interval:
            await asyncio.sleep(min_interval - (current_time - self.last_request_time))

        self.last_request_time = time.time()
        self.request_count += 1

        # Add random delay occasionally to appear more human-like
        if self.request_count % 20 == 0:
            await asyncio.sleep(random.uniform(0.5, 1.5))

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
        self,
        base_url: str,
        endpoint_path: str,
        params: Dict = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Make HTTP request through BravoMotors proxy

        Args:
            base_url: Che168 API base URL (e.g., CHE168_SEARCH_API or CHE168_DETAIL_API)
            endpoint_path: API endpoint path (e.g., "/api/v11/search")
            params: Query parameters
            max_retries: Maximum retry attempts

        Returns:
            JSON response data
        """
        await self._rate_limit()

        if params is None:
            params = {}

        # Build the original che168 URL
        original_url = f"{base_url}{endpoint_path}"

        # Build proxy URL
        proxy_url = self._build_proxy_url(original_url, params)

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
                logger.debug(f"Making proxy request (attempt {attempt + 1}): {endpoint_path}")
                response = self.session.get(proxy_url, timeout=(10, 30))
                response.raise_for_status()

                # Parse JSON response
                json_data = response.json()

                # Log slow requests
                request_time = time.time() - request_start_time
                if request_time > 5.0:
                    logger.warning(f"Slow request detected: {endpoint_path} took {request_time:.2f}s")

                # Reset circuit breaker on success
                self.circuit_breaker_failures = 0

                return json_data

            except RequestException as e:
                last_exception = e
                status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') and e.response else None

                logger.warning(f"Request attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}")

                # Update circuit breaker
                self.circuit_breaker_failures += 1
                if self.circuit_breaker_failures >= 10:
                    self.circuit_breaker_cooldown_until = time.time() + 10
                    logger.error(f"Circuit breaker OPENED - too many failures ({self.circuit_breaker_failures})")

                # Retry with exponential backoff
                if attempt < max_retries:
                    backoff_time = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                    logger.info(f"Retrying in {backoff_time:.1f}s...")
                    await asyncio.sleep(backoff_time)
                    continue

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
            # Build search parameters
            params = {
                "_appid": "2sc.m",
                "pageindex": str(filters.pageindex),
                "pagesize": str(filters.pagesize),
                "pvareaid": "111478",
                "scene_no": "12",
                "sort": str(filters.sort) if filters.sort else "0",
            }

            # Add optional filters
            if filters.brandid:
                params["brandid"] = str(filters.brandid)
            if filters.seriesid:
                params["seriesid"] = str(filters.seriesid)
            if filters.seriesyearid:
                params["seriesyearid"] = str(filters.seriesyearid)
            if filters.specid:
                params["specid"] = str(filters.specid)
            if filters.service:
                params["service"] = str(filters.service)
            if filters.price:
                params["price"] = str(filters.price)
            if filters.agerange:
                params["agerange"] = str(filters.agerange)
            if filters.mileage:
                params["mileage"] = str(filters.mileage)
            if filters.fueltype:
                params["fueltype"] = str(filters.fueltype)
            if filters.displacement:
                params["displacement"] = str(filters.displacement)

            # Check cache first (only for non-page-1 requests to ensure fresh data on initial load)
            cache_key = self._get_cache_key("search", params)
            if filters.pageindex > 1:
                cached = self.cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for search: {cache_key}")
                    return cached

            # Make request
            json_data = await self._make_request(
                CHE168_SEARCH_API,
                "/api/v11/search",
                params
            )
            result = self.parser.parse_car_search_response(json_data)

            # Cache successful results
            if result.success:
                self.cache.set(cache_key, result, expire=CACHE_TTL_SEARCH)

            return result

        except Exception as e:
            logger.error(f"Error in search_cars: {str(e)}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={},
                success=False
            )

    async def get_brands(self) -> Che168BrandsResponse:
        """
        Get all available car brands from Che168

        Returns:
            Che168BrandsResponse with all available brands
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key("brands")
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("Cache hit for brands")
                return cached

            params = {
                "_appid": "2sc.m",
                "cid": "0",
                "pid": "0",
                "isenergy": "0",
                "s_pid": "0",
                "s_cid": "0",
            }

            json_data = await self._make_request(
                CHE168_SEARCH_API,
                "/api/v2/getbrands",
                params
            )
            result = self.parser.parse_brands_response(json_data)

            # Cache successful results
            if result.returncode == 0:
                self.cache.set(cache_key, result, expire=CACHE_TTL_BRANDS)

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
            cache_key = self._get_cache_key("models", {"brand_id": brand_id})
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for models: brand_id={brand_id}")
                return cached

            params = {
                "_appid": "2sc.m",
                "pageindex": "1",
                "pagesize": "1",
                "brandid": str(brand_id),
                "pvareaid": "111478",
                "scene_no": "12",
            }

            raw_response = await self._make_request(
                CHE168_SEARCH_API,
                "/api/v11/search",
                params
            )

            if raw_response.get("returncode") != 0:
                return Che168SearchResponse(
                    returncode=raw_response.get("returncode", -1),
                    message=raw_response.get('message', 'Unknown error'),
                    result={},
                    success=False
                )

            result = self.parser.parse_car_search_response(raw_response)

            # Extract models from filters array
            models = []
            if result.filters:
                for filter_item in result.filters:
                    if filter_item.key == "seriesid":
                        models.append({
                            "id": int(filter_item.value),
                            "name": filter_item.title,
                            "value": filter_item.value,
                            "title": filter_item.title,
                        })

            # Add models to result
            if hasattr(result, 'result') and isinstance(result.result, dict):
                result.result['models'] = models
                result.result['series'] = models

            # Cache successful results
            if result.success:
                self.cache.set(cache_key, result, expire=CACHE_TTL_MODELS)

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
            cache_key = self._get_cache_key("years", {"brand_id": brand_id, "series_id": series_id})
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for years: brand_id={brand_id}, series_id={series_id}")
                return cached

            params = {
                "_appid": "2sc.m",
                "pageindex": "1",
                "pagesize": "1",
                "brandid": str(brand_id),
                "seriesid": str(series_id),
                "pvareaid": "111478",
                "scene_no": "12",
            }

            raw_response = await self._make_request(
                CHE168_SEARCH_API,
                "/api/v11/search",
                params
            )

            if raw_response.get("returncode") != 0:
                return Che168SearchResponse(
                    returncode=raw_response.get("returncode", -1),
                    message=raw_response.get('message', 'Unknown error'),
                    result={},
                    success=False
                )

            result = self.parser.parse_car_search_response(raw_response)

            # Extract years from filters array
            years = []
            if result.filters:
                for filter_item in result.filters:
                    if filter_item.key == "seriesyearid":
                        years.append({
                            "id": int(filter_item.value),
                            "name": filter_item.title,
                            "value": filter_item.value,
                            "title": filter_item.title,
                        })

            # Add years to result
            if hasattr(result, 'result') and isinstance(result.result, dict):
                result.result['years'] = years

            # Cache successful results
            if result.success:
                self.cache.set(cache_key, result, expire=CACHE_TTL_YEARS)

            return result

        except Exception as e:
            logger.error(f"Error in get_years for brand {brand_id}, series {series_id}: {str(e)}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Service error: {str(e)}",
                result={},
                success=False
            )

    async def get_car_detail(self, info_id: int) -> Che168CarDetailResponse:
        """
        Get detailed information for a specific car

        Fetches both car info and params in parallel for better performance.

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarDetailResponse with car details
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key("car_detail", {"info_id": info_id})
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for car detail: info_id={info_id}")
                return cached

            # Fetch car info and params in parallel
            car_info_task = self.get_car_info(info_id)
            car_params_task = self.get_car_params(info_id)

            car_info_response, car_params_response = await asyncio.gather(
                car_info_task,
                car_params_task,
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(car_info_response, Exception):
                logger.error(f"Error fetching car info for {info_id}: {str(car_info_response)}")
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error=f"Failed to fetch car info: {str(car_info_response)}"
                )

            if isinstance(car_params_response, Exception):
                logger.error(f"Error fetching car params for {info_id}: {str(car_params_response)}")
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

            # Build car object from car_info data
            if car_info_response.result:
                info_data = car_info_response.result

                # Extract image URLs from picList
                pic_list = info_data.get('picList', [])
                image_url = pic_list[0] if pic_list else ""

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
                    "remark": info_data.get('remark', ''),
                    "guidanceprice": info_data.get('guidanceprice', 0),
                    "engine": info_data.get('engine', ''),
                    "vincode": info_data.get('vincode', ''),
                }

                # Add parameter sections
                param_sections = []
                if car_params_response.returncode == 0 and car_params_response.result:
                    param_sections = car_params_response.result

                result = Che168CarDetailResponse(
                    success=True,
                    car=car_object,
                    meta={"params": param_sections}
                )

                # Cache successful results
                self.cache.set(cache_key, result, expire=CACHE_TTL_CAR_DETAIL)

                return result
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

    async def get_car_info(self, info_id: int) -> Che168CarInfoResponse:
        """
        Get basic car information using Che168 getcarinfo API

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarInfoResponse with basic car information
        """
        try:
            params = {
                "infoid": str(info_id),
                "_appid": "2sc.m"
            }

            json_data = await self._make_request(
                CHE168_DETAIL_API,
                "/apic/v2/car/getcarinfo",
                params
            )

            if json_data.get("returncode") == 0 and "result" in json_data:
                return Che168CarInfoResponse(
                    returncode=json_data.get("returncode", 0),
                    message=json_data.get("message", "Success"),
                    result=json_data["result"]
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
            params = {
                "infoid": str(info_id),
                "_appid": "2sc.m"
            }

            json_data = await self._make_request(
                CHE168_DETAIL_API,
                "/api/v1/car/getparamtypeitems",
                params
            )

            if json_data.get("returncode") == 0 and "result" in json_data:
                return Che168CarParamsResponse(
                    returncode=json_data.get("returncode", 0),
                    message=json_data.get("message", "Success"),
                    result=json_data["result"]
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

    async def get_filters(self) -> Che168FiltersResponse:
        """
        Get available filter options

        Returns:
            Che168FiltersResponse with available filters
        """
        try:
            brands_result = await self.get_brands()

            if brands_result.returncode != 0:
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

    async def get_car_analysis(self, info_id: int) -> Che168CarAnalysisResponse:
        """
        Get car analysis and evaluation (placeholder - not available on Che168 API)

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarAnalysisResponse with car analysis data
        """
        logger.info(f"Car analysis not available for {info_id} - endpoint does not exist")
        return Che168CarAnalysisResponse(
            returncode=0,
            message="Analysis data not available for this vehicle",
            result={}
        )

    async def translate_text(self, text: str, target_language: str = "ru") -> TranslationResponse:
        """
        Translate Chinese text to target language

        Args:
            text: Chinese text to translate
            target_language: Target language code (default: "ru")

        Returns:
            TranslationResponse with translation result
        """
        # Placeholder - should be replaced with actual translation service
        return TranslationResponse(
            original_text=text,
            translated_text=text,
            source_language="zh-cn",
            target_language=target_language,
            type="analysis",
            is_static=False,
            is_cached=False,
            success=True
        )

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information including cache statistics"""
        return {
            "proxy_url": BRAVOMOTORS_PROXY_URL,
            "request_count": self.request_count,
            "last_request": self.last_request_time,
            "cache_stats": {
                "size": len(self.cache),
                "volume": self.cache.volume(),
            },
            "circuit_breaker": {
                "failures": self.circuit_breaker_failures,
                "is_open": time.time() < self.circuit_breaker_cooldown_until,
                "cooldown_remaining": max(0, int(self.circuit_breaker_cooldown_until - time.time()))
            }
        }

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Cache cleared")

    def update_cookies(self, new_cookies: Dict[str, str]):
        """Update session cookies (not used with proxy, kept for compatibility)"""
        pass
