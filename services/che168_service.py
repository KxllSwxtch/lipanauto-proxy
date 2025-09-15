"""
Che168 Service
Business logic layer for Chinese car marketplace integration
"""

import json
import logging
import time
import random
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import requests
from requests.exceptions import RequestException, Timeout

from parsers.che168_parser import Che168Parser
from schemas.che168 import (
    Che168SearchResponse,
    Che168CarDetailResponse,
    Che168FiltersResponse,
    Che168SearchFilters,
    Che168BrandsResponse,
    Che168ModelsResponse,
    Che168YearsResponse,
)

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

        # Cache for brands/models/years to reduce API calls
        self.brands_cache = None
        self.brands_cache_time = 0
        self.models_cache = {}
        self.years_cache = {}

    def _rate_limit(self):
        """Rate limiting to avoid being blocked"""
        current_time = time.time()
        if current_time - self.last_request_time < 0.5:  # 500ms between requests
            time.sleep(0.5 - (current_time - self.last_request_time))

        self.last_request_time = time.time()
        self.request_count += 1

        # Add random delay occasionally
        if self.request_count % 20 == 0:
            time.sleep(random.uniform(1.0, 3.0))

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

    async def _make_request(
        self, url: str, params: Dict = None, use_proxy: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retry logic

        Args:
            url: Target URL
            params: Query parameters
            use_proxy: Whether to use proxy client

        Returns:
            JSON response data
        """
        self._rate_limit()

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

        max_retries = 3
        for attempt in range(max_retries):
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
                return json_data

            except RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await_time = 2 ** attempt
                    time.sleep(await_time + random.uniform(0, 1))
                    continue
                else:
                    return {
                        "returncode": 1,
                        "message": f"Request failed after {max_retries} attempts: {str(e)}",
                        "result": {},
                    }

            except Exception as e:
                logger.error(f"Unexpected error in request: {str(e)}")
                return {
                    "returncode": 1,
                    "message": f"Unexpected error: {str(e)}",
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
                "existtags": filters.existtags,
                "pid": str(filters.pid),
                "testtype": filters.testtype,
                "test102223": filters.test102223,
                "testnewcarspecid": filters.testnewcarspecid,
                "test102797": filters.test102797,
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

            json_data = await self._make_request(url, params)
            result = self.parser.parse_api_response(json_data)

            return result

        except Exception as e:
            logger.error(f"Error in search_cars: {str(e)}")
            return Che168SearchResponse(
                success=False,
                cars=[],
                pagination={},
                service_filters=[],
                total_count=0,
                meta={
                    "service": "che168_search",
                    "error": f"Service error: {str(e)}",
                },
            )

    async def get_car_detail(self, info_id: int) -> Che168CarDetailResponse:
        """
        Get detailed information for a specific car

        Args:
            info_id: Car listing ID

        Returns:
            Che168CarDetailResponse with car details
        """
        try:
            # This would typically be a different endpoint for car details
            # For now, we'll search for this specific car
            filters = Che168SearchFilters(pagesize=1)
            search_result = await self.search_cars(filters)

            if not search_result.success:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error="Failed to fetch car details",
                    meta={"service": "che168_detail", "info_id": info_id},
                )

            # Look for the specific car in results
            target_car = None
            for car in search_result.cars:
                if car.infoid == info_id:
                    target_car = car
                    break

            if not target_car:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error=f"Car with ID {info_id} not found",
                    meta={"service": "che168_detail", "info_id": info_id},
                )

            return Che168CarDetailResponse(
                success=True,
                car=target_car,
                error=None,
                meta={"service": "che168_detail", "info_id": info_id},
            )

        except Exception as e:
            logger.error(f"Error in get_car_detail for {info_id}: {str(e)}")
            return Che168CarDetailResponse(
                success=False,
                car=None,
                error=f"Service error: {str(e)}",
                meta={"service": "che168_detail", "info_id": info_id},
            )

    async def get_filters(self) -> Che168FiltersResponse:
        """
        Get available filter options

        Returns:
            Che168FiltersResponse with available filters
        """
        try:
            # Get filters from a basic search request
            filters = Che168SearchFilters(pagesize=1)
            search_result = await self.search_cars(filters)

            if not search_result.success:
                return Che168FiltersResponse(
                    success=False,
                    service_types=[],
                    meta={
                        "service": "che168_filters",
                        "error": "Failed to fetch filters",
                    },
                )

            return Che168FiltersResponse(
                success=True,
                service_types=search_result.service_filters,
                meta={
                    "service": "che168_filters",
                    "total_filters": len(search_result.service_filters),
                },
            )

        except Exception as e:
            logger.error(f"Error in get_filters: {str(e)}")
            return Che168FiltersResponse(
                success=False,
                service_types=[],
                meta={
                    "service": "che168_filters",
                    "error": f"Service error: {str(e)}",
                },
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
            if result.success:
                self.brands_cache = result
                self.brands_cache_time = current_time

            return result

        except Exception as e:
            logger.error(f"Error in get_brands: {str(e)}")
            return Che168BrandsResponse(
                success=False,
                brands=[],
                brand_groups=[],
                total_brands=0,
                meta={
                    "service": "che168_brands",
                    "error": f"Service error: {str(e)}",
                },
            )

    async def get_models(self, brand_id: int) -> Che168ModelsResponse:
        """
        Get available models for a specific brand

        Args:
            brand_id: Brand ID to get models for

        Returns:
            Che168ModelsResponse with available models
        """
        try:
            # Check cache first
            cache_key = f"brand_{brand_id}"
            if cache_key in self.models_cache:
                cached_result, cache_time = self.models_cache[cache_key]
                if (time.time() - cache_time) < 1800:  # 30 minutes cache
                    return cached_result

            # Make search request with brand ID to get models from filters
            filters = Che168SearchFilters(brandid=brand_id, pagesize=1)
            search_result = await self.search_cars(filters)

            if not search_result.success:
                return Che168ModelsResponse(
                    success=False,
                    models=[],
                    brand_id=brand_id,
                    total_models=0,
                    meta={
                        "service": "che168_models",
                        "brand_id": brand_id,
                        "error": "Failed to fetch models from search API",
                    },
                )

            # We need to make another request to get the raw response with filters
            # Since the parsed response doesn't contain the raw filters data
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
                return Che168ModelsResponse(
                    success=False,
                    models=[],
                    brand_id=brand_id,
                    total_models=0,
                    meta={
                        "service": "che168_models",
                        "brand_id": brand_id,
                        "error": f"API error: {raw_response.get('message', 'Unknown error')}",
                    },
                )

            # Extract models from filters
            filter_data = self.parser.parse_filters_from_raw_response(raw_response, "seriesid")
            models = [
                Che168ModelFilter(
                    title=f["title"],
                    key=f["key"],
                    value=f["value"],
                    dtype=f["dtype"],
                    subvalue=f["subvalue"],
                    subspecname=f["subspecname"],
                )
                for f in filter_data
            ]

            result = Che168ModelsResponse(
                success=True,
                models=models,
                brand_id=brand_id,
                total_models=len(models),
                meta={
                    "service": "che168_models",
                    "brand_id": brand_id,
                    "extracted_from": "search_filters",
                },
            )

            # Cache the result
            self.models_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Error in get_models for brand {brand_id}: {str(e)}")
            return Che168ModelsResponse(
                success=False,
                models=[],
                brand_id=brand_id,
                total_models=0,
                meta={
                    "service": "che168_models",
                    "brand_id": brand_id,
                    "error": f"Service error: {str(e)}",
                },
            )

    async def get_years(self, brand_id: int, series_id: int) -> Che168YearsResponse:
        """
        Get available years for a specific brand and model

        Args:
            brand_id: Brand ID
            series_id: Series (model) ID

        Returns:
            Che168YearsResponse with available years
        """
        try:
            # Check cache first
            cache_key = f"brand_{brand_id}_series_{series_id}"
            if cache_key in self.years_cache:
                cached_result, cache_time = self.years_cache[cache_key]
                if (time.time() - cache_time) < 1800:  # 30 minutes cache
                    return cached_result

            # Make search request with brand and series ID to get years from filters
            filters = Che168SearchFilters(brandid=brand_id, seriesid=series_id, pagesize=1)
            search_result = await self.search_cars(filters)

            if not search_result.success:
                return Che168YearsResponse(
                    success=False,
                    years=[],
                    brand_id=brand_id,
                    series_id=series_id,
                    total_years=0,
                    meta={
                        "service": "che168_years",
                        "brand_id": brand_id,
                        "series_id": series_id,
                        "error": "Failed to fetch years from search API",
                    },
                )

            # Make another request to get the raw response with year filters
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
                return Che168YearsResponse(
                    success=False,
                    years=[],
                    brand_id=brand_id,
                    series_id=series_id,
                    total_years=0,
                    meta={
                        "service": "che168_years",
                        "brand_id": brand_id,
                        "series_id": series_id,
                        "error": f"API error: {raw_response.get('message', 'Unknown error')}",
                    },
                )

            # Extract years from filters
            filter_data = self.parser.parse_filters_from_raw_response(raw_response, "seriesyearid")
            years = [
                Che168YearFilter(
                    title=f["title"],
                    key=f["key"],
                    value=f["value"],
                    dtype=f["dtype"],
                    subvalue=f["subvalue"],
                    subspecname=f["subspecname"],
                )
                for f in filter_data
            ]

            result = Che168YearsResponse(
                success=True,
                years=years,
                brand_id=brand_id,
                series_id=series_id,
                total_years=len(years),
                meta={
                    "service": "che168_years",
                    "brand_id": brand_id,
                    "series_id": series_id,
                    "extracted_from": "search_filters",
                },
            )

            # Cache the result
            self.years_cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Error in get_years for brand {brand_id}, series {series_id}: {str(e)}")
            return Che168YearsResponse(
                success=False,
                years=[],
                brand_id=brand_id,
                series_id=series_id,
                total_years=0,
                meta={
                    "service": "che168_years",
                    "brand_id": brand_id,
                    "series_id": series_id,
                    "error": f"Service error: {str(e)}",
                },
            )

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
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
        }