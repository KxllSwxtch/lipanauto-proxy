"""
KBChaChaCha Service
Business logic layer for Korean car marketplace integration
"""

import json
import logging
import time
import random
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import requests
from requests.exceptions import RequestException, Timeout

from parsers.kbchachacha_parser import KBChaChaParser
from schemas.kbchachacha import (
    KBMakersResponse,
    KBModelsResponse,
    KBGenerationsResponse,
    KBConfigsTrimsResponse,
    KBSearchResponse,
    KBDefaultListResponse,
    KBSearchFilters,
)

logger = logging.getLogger(__name__)


class KBChaChaService:
    """
    KBChaChaCha service for Korean car marketplace integration

    Provides comprehensive functionality for:
    - Manufacturers, models, generations, configurations listing
    - Car search with filters
    - HTML parsing for car listings
    - Session management with Korean site requirements
    """

    def __init__(self, proxy_client=None):
        self.proxy_client = proxy_client
        self.parser = KBChaChaParser()
        self.base_url = "https://www.kbchachacha.com"

        # Session management
        self.session = requests.Session()
        self._setup_session()

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        # Cache for session persistence
        self.session_cookies = {}

    def _setup_session(self):
        """Setup session with Korean site requirements"""
        # Korean site specific headers
        self.session.headers.update(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
                "Connection": "keep-alive",
                "Referer": "https://www.kbchachacha.com/public/search/main.kbc",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }
        )

        # Session configuration
        self.session.timeout = (10, 30)  # connect, read timeout
        self.session.max_redirects = 3

    def _rate_limit(self):
        """Rate limiting to avoid being blocked"""
        current_time = time.time()
        if current_time - self.last_request_time < 1.0:  # 1 second between requests
            time.sleep(1.0 - (current_time - self.last_request_time))

        self.last_request_time = time.time()
        self.request_count += 1

        # Add random delay occasionally
        if self.request_count % 10 == 0:
            time.sleep(random.uniform(0.5, 2.0))

    async def _make_request(
        self, url: str, params: Dict = None, use_proxy: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retry logic

        Args:
            url: Target URL
            params: Query parameters
            use_proxy: Whether to use proxy client (disabled for now)

        Returns:
            Dict with response data
        """
        self._rate_limit()

        for attempt in range(3):  # Max 3 attempts
            try:
                # For now, always use direct request
                response = self.session.get(url, params=params)

                if response.status_code == 200:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "text": response.text,
                        "url": str(response.url),
                        "attempt": attempt + 1,
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code}",
                        "url": str(response.url),
                        "attempt": attempt + 1,
                    }

            except Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/3): {url}")
                if attempt == 2:
                    return {"success": False, "error": "Request timeout", "url": url}
                import asyncio

                await asyncio.sleep(2**attempt)  # Exponential backoff

            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/3): {str(e)}")
                if attempt == 2:
                    return {
                        "success": False,
                        "error": f"Request failed: {str(e)}",
                        "url": url,
                    }
                import asyncio

                await asyncio.sleep(2**attempt)

        return {"success": False, "error": "Max retries exceeded", "url": url}

    async def get_manufacturers(self) -> KBMakersResponse:
        """
        Get list of car manufacturers

        Returns:
            KBMakersResponse with domestic and imported manufacturers
        """
        try:
            logger.info("Fetching car manufacturers from KBChaChaCha")

            url = f"{self.base_url}/public/search/carMaker.json"
            params = {"page": "1", "sort": "-orderDate"}

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBMakersResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_manufacturers",
                    },
                )

            # Parse JSON response
            try:
                json_data = json.loads(response_data["text"])
                parsed_data = self.parser.parse_manufacturers_json(json_data)

                if not parsed_data.get("success"):
                    return KBMakersResponse(
                        success=False,
                        total_count=0,
                        meta={
                            "error": parsed_data.get("error", "Parser error"),
                            "service": "kbchachacha_manufacturers",
                        },
                    )

                return KBMakersResponse(
                    success=True,
                    domestic=parsed_data["domestic"],
                    imported=parsed_data["imported"],
                    total_count=parsed_data["total_count"],
                    meta=parsed_data.get("meta", {}),
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return KBMakersResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": f"JSON decode error: {str(e)}",
                        "service": "kbchachacha_manufacturers",
                    },
                )

        except Exception as e:
            logger.error(f"Error fetching manufacturers: {str(e)}")
            return KBMakersResponse(
                success=False,
                total_count=0,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_manufacturers",
                },
            )

    async def get_models(self, maker_code: str) -> KBModelsResponse:
        """
        Get car models for specific manufacturer

        Args:
            maker_code: Manufacturer code (e.g., "101" for 현대)

        Returns:
            KBModelsResponse with car models
        """
        try:
            logger.info(f"Fetching car models for maker {maker_code}")

            url = f"{self.base_url}/public/search/carClass.json"
            params = {"page": "1", "sort": "-orderDate", "makerCode": maker_code}

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBModelsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_models",
                        "maker_code": maker_code,
                    },
                )

            # Parse JSON response
            try:
                json_data = json.loads(response_data["text"])
                parsed_data = self.parser.parse_models_json(json_data)

                if not parsed_data.get("success"):
                    return KBModelsResponse(
                        success=False,
                        total_count=0,
                        meta={
                            "error": parsed_data.get("error", "Parser error"),
                            "service": "kbchachacha_models",
                            "maker_code": maker_code,
                        },
                    )

                return KBModelsResponse(
                    success=True,
                    models=parsed_data["models"],
                    total_count=parsed_data["total_count"],
                    meta={**parsed_data.get("meta", {}), "maker_code": maker_code},
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return KBModelsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": f"JSON decode error: {str(e)}",
                        "service": "kbchachacha_models",
                        "maker_code": maker_code,
                    },
                )

        except Exception as e:
            logger.error(f"Error fetching models for maker {maker_code}: {str(e)}")
            return KBModelsResponse(
                success=False,
                total_count=0,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_models",
                    "maker_code": maker_code,
                },
            )

    async def get_generations(self, class_code: str) -> KBGenerationsResponse:
        """
        Get car generations for specific model class

        Args:
            class_code: Model class code (e.g., "1101" for 그랜저, "1108" for 쏘나타)

        Returns:
            KBGenerationsResponse with generations
        """
        try:
            logger.info(f"Fetching car generations for class code {class_code}")

            # Use carName.json API for generations (not carModel.json)
            url = f"{self.base_url}/public/search/carName.json"
            params = {"page": "1", "sort": "-orderDate", "classCode": class_code}

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBGenerationsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_generations",
                        "class_code": class_code,
                    },
                )

            # Parse JSON response
            try:
                json_data = json.loads(response_data["text"])
                parsed_data = self.parser.parse_generations_json(json_data)

                if not parsed_data.get("success"):
                    return KBGenerationsResponse(
                        success=False,
                        total_count=0,
                        meta={
                            "error": parsed_data.get("error", "Parser error"),
                            "service": "kbchachacha_generations",
                            "class_code": class_code,
                        },
                    )

                return KBGenerationsResponse(
                    success=True,
                    generations=parsed_data["generations"],
                    total_count=parsed_data["total_count"],
                    meta={**parsed_data.get("meta", {}), "class_code": class_code},
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return KBGenerationsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": f"JSON decode error: {str(e)}",
                        "service": "kbchachacha_generations",
                        "class_code": class_code,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error fetching generations for class code {class_code}: {str(e)}"
            )
            return KBGenerationsResponse(
                success=False,
                total_count=0,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_generations",
                    "class_code": class_code,
                },
            )

    async def get_configs_trims(self, car_code: str) -> KBConfigsTrimsResponse:
        """
        Get configurations and trims for specific car code

        Args:
            car_code: Car code (same as generations endpoint)

        Returns:
            KBConfigsTrimsResponse with configurations and trims
        """
        try:
            logger.info(f"Fetching configurations and trims for car code {car_code}")

            # Use same API as generations - it contains both codeModel and codeGrade
            url = f"{self.base_url}/public/search/carModel.json"
            params = {"page": "1", "sort": "-orderDate", "carCode": car_code}

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBConfigsTrimsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_configs_trims",
                        "car_code": car_code,
                    },
                )

            # Parse JSON response
            try:
                json_data = json.loads(response_data["text"])
                parsed_data = self.parser.parse_configs_trims_json(json_data)

                if not parsed_data.get("success"):
                    return KBConfigsTrimsResponse(
                        success=False,
                        total_count=0,
                        meta={
                            "error": parsed_data.get("error", "Parser error"),
                            "service": "kbchachacha_configs_trims",
                            "car_code": car_code,
                        },
                    )

                return KBConfigsTrimsResponse(
                    success=True,
                    configurations=parsed_data["configurations"],
                    trims=parsed_data["trims"],
                    total_count=len(parsed_data["configurations"])
                    + len(parsed_data["trims"]),
                    meta={**parsed_data.get("meta", {}), "car_code": car_code},
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return KBConfigsTrimsResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": f"JSON decode error: {str(e)}",
                        "service": "kbchachacha_configs_trims",
                        "car_code": car_code,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error fetching configs/trims for car code {car_code}: {str(e)}"
            )
            return KBConfigsTrimsResponse(
                success=False,
                total_count=0,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_configs_trims",
                    "car_code": car_code,
                },
            )

    async def get_default_listings(self) -> KBDefaultListResponse:
        """
        Get default car listings (KB Star Pick and certified cars)

        Returns:
            KBDefaultListResponse with default listings
        """
        try:
            logger.info("Fetching default car listings")

            url = f"{self.base_url}/public/search/list.empty"
            params = {"page": "1", "sort": "-orderDate"}

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBDefaultListResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_default_listings",
                    },
                )

            # Parse HTML response
            parsed_data = self.parser.parse_car_listings_html(response_data["text"])

            if not parsed_data.get("success"):
                return KBDefaultListResponse(
                    success=False,
                    total_count=0,
                    meta={
                        "error": parsed_data.get("error", "Parser error"),
                        "service": "kbchachacha_default_listings",
                    },
                )

            return KBDefaultListResponse(
                success=True,
                star_pick_listings=parsed_data["star_pick_listings"],
                certified_listings=parsed_data["certified_listings"],
                total_count=parsed_data["total_count"],
                meta=parsed_data.get("meta", {}),
            )

        except Exception as e:
            logger.error(f"Error fetching default listings: {str(e)}")
            return KBDefaultListResponse(
                success=False,
                total_count=0,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_default_listings",
                },
            )

    def _build_search_params(self, filters: KBSearchFilters) -> Dict[str, str]:
        """
        Build search parameters from filters

        Args:
            filters: KBSearchFilters object with all filter options

        Returns:
            Dict with URL parameters for KBChaChaCha search
        """
        params = {
            "page": str(filters.page),
            "sort": filters.sort,
        }

        # Basic car filters
        if filters.makerCode:
            params["makerCode"] = filters.makerCode
        if filters.classCode:
            params["classCode"] = filters.classCode
        if filters.carCode:
            params["carCode"] = filters.carCode
        if filters.modelCode:
            params["modelCode"] = filters.modelCode
        if filters.modelGradeCode:
            params["modelGradeCode"] = filters.modelGradeCode

        # Year filter (연식) - priority: new fields, then legacy
        year_from = filters.year_from or filters.yearFrom
        year_to = filters.year_to or filters.yearTo
        if year_from and year_to:
            params["regiDay"] = f"{year_from},{year_to}"
        elif year_from:
            params["regiDay"] = f"{year_from},{year_from + 10}"  # Default range
        elif year_to:
            params["regiDay"] = f"{year_to - 10},{year_to}"  # Default range

        # Mileage filter (주행거리) - in kilometers
        mileage_from = filters.mileage_from or filters.mileageFrom
        mileage_to = filters.mileage_to or filters.mileageTo
        if mileage_from is not None and mileage_to is not None:
            params["km"] = f"{mileage_from},{mileage_to}"
        elif mileage_from is not None:
            params["km"] = f"{mileage_from},999999"  # No upper limit
        elif mileage_to is not None:
            params["km"] = f"0,{mileage_to}"

        # Price filter (가격) - in 만원 (10,000 KRW units)
        price_from = filters.price_from or filters.priceFrom
        price_to = filters.price_to or filters.priceTo
        if price_from is not None and price_to is not None:
            params["sellAmt"] = f"{price_from},{price_to}"
        elif price_from is not None:
            params["sellAmt"] = f"{price_from},99999"  # No upper limit
        elif price_to is not None:
            params["sellAmt"] = f"0,{price_to}"

        # Fuel type filter (연료)
        if filters.fuel_types:
            # Join multiple fuel types with comma
            fuel_codes = [fuel_type.value for fuel_type in filters.fuel_types]
            if len(fuel_codes) == 1:
                params["gas"] = fuel_codes[0]
            else:
                # Multiple fuel types - might need different format
                params["gas"] = ",".join(fuel_codes)

        return params

    async def search_cars(self, filters: KBSearchFilters) -> KBSearchResponse:
        """
        Search cars with comprehensive filters

        Args:
            filters: KBSearchFilters with all search criteria

        Returns:
            KBSearchResponse with car listings
        """
        try:
            logger.info(
                f"Searching cars with filters: page={filters.page}, sort={filters.sort}"
            )
            if filters.makerCode:
                logger.info(f"Manufacturer filter: {filters.makerCode}")
            if filters.year_from or filters.year_to:
                logger.info(f"Year filter: {filters.year_from}-{filters.year_to}")
            if filters.price_from or filters.price_to:
                logger.info(
                    f"Price filter: {filters.price_from}-{filters.price_to} 만원"
                )
            if filters.mileage_from or filters.mileage_to:
                logger.info(
                    f"Mileage filter: {filters.mileage_from}-{filters.mileage_to} km"
                )
            if filters.fuel_types:
                logger.info(f"Fuel types: {[ft.value for ft in filters.fuel_types]}")

            # Use filtered search endpoint that supports all filters
            url = f"{self.base_url}/public/search/list.empty"
            params = self._build_search_params(filters)

            response_data = await self._make_request(url, params)

            if not response_data.get("success"):
                return KBSearchResponse(
                    success=False,
                    total_count=0,
                    page=filters.page,
                    has_next_page=False,
                    meta={
                        "error": response_data.get("error", "Unknown error"),
                        "service": "kbchachacha_search",
                        "filters": params,
                    },
                )

            # Parse HTML response for car listings
            try:
                parsed_data = self.parser.parse_search_results_html(
                    response_data["text"], filters.page
                )

                if not parsed_data.get("success"):
                    return KBSearchResponse(
                        success=False,
                        total_count=0,
                        page=filters.page,
                        has_next_page=False,
                        meta={
                            "error": parsed_data.get("error", "Parser error"),
                            "service": "kbchachacha_search",
                            "filters": params,
                        },
                    )

                return KBSearchResponse(
                    success=True,
                    listings=parsed_data.get("listings", []),
                    total_count=parsed_data.get("total_count", 0),
                    page=filters.page,
                    has_next_page=parsed_data.get("has_next_page", False),
                    star_pick_count=parsed_data.get("star_pick_count", 0),
                    certified_count=parsed_data.get("certified_count", 0),
                    meta={
                        "service": "kbchachacha_search",
                        "filters_applied": params,
                        "parser": "kbchachacha_search_results",
                        **parsed_data.get("meta", {}),
                    },
                )

            except Exception as e:
                logger.error(f"HTML parsing error: {str(e)}")
                return KBSearchResponse(
                    success=False,
                    total_count=0,
                    page=filters.page,
                    has_next_page=False,
                    meta={
                        "error": f"HTML parsing error: {str(e)}",
                        "service": "kbchachacha_search",
                        "filters": params,
                    },
                )

        except Exception as e:
            logger.error(f"Error searching cars: {str(e)}")
            return KBSearchResponse(
                success=False,
                total_count=0,
                page=filters.page,
                has_next_page=False,
                meta={
                    "error": f"Service error: {str(e)}",
                    "service": "kbchachacha_search",
                },
            )

    async def get_car_details(self, car_seq: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific car

        Args:
            car_seq: Car sequence ID (e.g., "27069369")

        Returns:
            Dict with detailed car information
        """
        try:
            logger.info(f"Fetching car details for carSeq: {car_seq}")

            # Build URL for car detail page
            url = f"{self.base_url}/public/car/detail.kbc"
            params = {"carSeq": car_seq}

            # Update session headers for car detail page request
            detail_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Cache-Control": "max-age=0",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }

            # Temporarily update headers for this request
            original_headers = self.session.headers.copy()
            self.session.headers.update(detail_headers)

            try:
                response_data = await self._make_request(url, params)
            finally:
                # Restore original headers
                self.session.headers = original_headers

            if not response_data.get("success"):
                return {
                    "success": False,
                    "error": response_data.get(
                        "error", "Failed to fetch car detail page"
                    ),
                    "meta": {
                        "service": "kbchachacha_car_details",
                        "car_seq": car_seq,
                        "url": f"{url}?carSeq={car_seq}",
                    },
                }

            # Parse HTML content
            html_content = response_data["text"]

            # Check if we got a valid car detail page
            if "차량정보" not in html_content and "판매가격" not in html_content:
                return {
                    "success": False,
                    "error": "Invalid car detail page - car may not exist or be unavailable",
                    "meta": {
                        "service": "kbchachacha_car_details",
                        "car_seq": car_seq,
                        "html_size": len(html_content),
                        "url": response_data.get("url"),
                    },
                }

            # Parse car detail HTML
            parsed_data = self.parser.parse_car_detail_html(html_content, car_seq)

            if not parsed_data.get("success"):
                return {
                    "success": False,
                    "error": parsed_data.get("error", "Failed to parse car detail"),
                    "meta": {
                        "service": "kbchachacha_car_details",
                        "car_seq": car_seq,
                        "parser_error": parsed_data.get("error"),
                    },
                }

            # Transform parsed data to match KBCarDetailResponse schema
            from schemas.kbchachacha import (
                KBCarSpecification,
                KBCarPricing,
                KBCarCondition,
                KBCarOptions,
                KBSellerInfo,
            )

            # Create structured objects from parsed data
            specifications = KBCarSpecification(**parsed_data.get("specifications", {}))
            pricing = KBCarPricing(
                current_price=parsed_data.get("pricing", {}).get("current_price", 0),
                current_price_text=parsed_data.get("pricing", {}).get(
                    "current_price_text", ""
                ),
                **{
                    k: v
                    for k, v in parsed_data.get("pricing", {}).items()
                    if k not in ["current_price", "current_price_text"]
                },
            )
            condition = KBCarCondition(**parsed_data.get("condition", {}))
            options = KBCarOptions(**parsed_data.get("options", {}))
            seller = KBSellerInfo(**parsed_data.get("seller", {}))

            # Build final response
            return {
                "success": True,
                "car_seq": car_seq,
                "title": parsed_data.get("title", ""),
                "brand": parsed_data.get("brand", ""),
                "model": parsed_data.get("model", ""),
                "full_name": parsed_data.get("full_name", ""),
                "images": parsed_data.get("images", []),
                "main_image": parsed_data.get("main_image"),
                "specifications": specifications,
                "pricing": pricing,
                "condition": condition,
                "options": options,
                "seller": seller,
                "description": parsed_data.get("description", ""),
                "tags": parsed_data.get("tags", []),
                "badges": parsed_data.get("badges", []),
                "detail_url": parsed_data.get("detail_url", ""),
                "meta": {
                    "service": "kbchachacha_car_details",
                    "car_seq": car_seq,
                    "parsing_success": True,
                    "data_sections": parsed_data.get("meta", {}).get(
                        "extracted_sections", []
                    ),
                    "url": response_data.get("url"),
                },
            }

        except Exception as e:
            logger.error(f"Error getting car details for {car_seq}: {str(e)}")
            return {
                "success": False,
                "error": f"Service error: {str(e)}",
                "meta": {
                    "service": "kbchachacha_car_details",
                    "car_seq": car_seq,
                    "exception": str(e),
                },
            }
