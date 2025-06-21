"""
Service for bike filters from bobaedream.co.kr
Handles filter API requests, caching, and business logic
"""

import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
from schemas.bike_filters import (
    FilterLevel,
    FilterOption,
    FilterInfo,
    FilterSearchParams,
    BikeSearchFilters,
    FilterValues,
)
from parsers.bike_filters_parser import BikeFiltersParser

logger = logging.getLogger(__name__)


class BikeFiltersService:
    """
    Service for managing bike filter operations
    Integrates with bobaedream.co.kr filter API

    Hierarchy:
    - depth-1 (dep=1): Manufacturers (제조사)
    - depth-2 (dep=2): Models (모델)
    - depth-3 (dep=3): Submodels (서브모델/세부모델)
    """

    BASE_URL = "https://www.bobaedream.co.kr/bike2/get_cardepth.php"

    # Static mapping for popular bike models (fallback for broken API)
    # Updated with REAL model IDs from bobaedream API
    POPULAR_MODELS_MAPPING = {
        "5": [  # Honda (but API returns BMW models - mapping corrected)
            {"sno": "7", "cname": "800GS", "cnt": "15", "chk": ""},
            {"sno": "12", "cname": "800S", "cnt": "8", "chk": ""},
        ],
        "6": [  # Yamaha (but API returns BMW models - mapping corrected)
            {"sno": "8", "cname": "1200CL", "cnt": "12", "chk": ""},
            {"sno": "9", "cname": "1200RT", "cnt": "18", "chk": ""},
            {"sno": "13", "cname": "1100RT", "cnt": "7", "chk": ""},
        ],
        "3": [  # Suzuki
            {"sno": "4", "cname": "650X 모토", "cnt": "10", "chk": ""},
            {"sno": "5", "cname": "650 X 카운티", "cnt": "8", "chk": ""},
            {"sno": "6", "cname": "450X", "cnt": "5", "chk": ""},
        ],
        "7": [  # Kawasaki
            {"sno": "14", "cname": "닌자", "cnt": "12", "chk": ""},  # Generic model
        ],
        # BMW, Daelim, Harley - API returns empty, disable model filtering
        "4": [],  # BMW - no models available
        "10": [],  # Daelim - no models available
        "119": [],  # Harley-Davidson - no models available
    }

    def __init__(self, proxy_client):
        self.proxy_client = proxy_client
        self.parser = BikeFiltersParser()
        self._cache = {}  # Simple in-memory cache

    async def get_filter_level(self, params: FilterSearchParams) -> FilterLevel:
        """
        Get filter options for specific level

        Args:
            params: Filter search parameters

        Returns:
            FilterLevel with available options
        """
        try:
            # Build cache key
            cache_key = f"filter_level_{params.dep}_{params.parval}_{params.selval}_{params.ifnew}"

            # Check cache
            if cache_key in self._cache:
                logger.info(f"Returning cached filter level {params.dep}")
                return self._cache[cache_key]

            # Build URL
            query_params = {
                "v1": "",
                "dep": params.dep,
                "parval": params.parval,
                "selval": params.selval,
                "ifnew": params.ifnew,
                "level_no2": params.level_no2,
            }

            url = f"{self.BASE_URL}?{urlencode(query_params)}"
            logger.info(f"Fetching filter level {params.dep} from: {url}")

            # Make request
            response = await self.proxy_client.make_request(url)

            if not response.get("success"):
                logger.error(
                    f"Failed to fetch filter level {params.dep}: {response.get('error')}"
                )
                return FilterLevel(
                    success=False,
                    options=[],
                    level=params.dep,
                    meta={"error": response.get("error", "Request failed")},
                )

            # Parse response
            response_text = response.get("text", "")
            filter_level = self.parser.parse_filter_response(response_text, params.dep)

            # Add request metadata
            filter_level.meta.update(
                {
                    "request_url": url,
                    "response_size": len(response_text),
                    "proxy_attempts": response.get("attempt", 1),
                }
            )

            # Cache successful results
            if filter_level.success:
                self._cache[cache_key] = filter_level
                logger.info(
                    f"Cached filter level {params.dep} with {len(filter_level.options)} options"
                )

            return filter_level

        except Exception as e:
            logger.error(f"Error getting filter level {params.dep}: {str(e)}")
            return FilterLevel(
                success=False, options=[], level=params.dep, meta={"error": str(e)}
            )

    async def get_categories(self) -> FilterLevel:
        """Get bike categories (level 0)"""
        params = FilterSearchParams(dep=0, parval="", selval="", ifnew="N", level_no2=0)
        return await self.get_filter_level(params)

    async def get_manufacturers(self) -> FilterLevel:
        """Get bike manufacturers (depth-1)"""
        params = FilterSearchParams(dep=1, parval="", selval="", ifnew="N", level_no2=0)
        return await self.get_filter_level(params)

    async def get_models(
        self, manufacturer_id: str, category_id: str = ""
    ) -> FilterLevel:
        """
        Get bike models for specific manufacturer (depth-2)

        FIXED: Now uses correct depth-2 API call instead of depth-3

        Args:
            manufacturer_id: Manufacturer ID (e.g., "5", "119")
            category_id: Category ID for filtering (optional)
        """
        try:
            logger.info(
                f"Getting models for manufacturer {manufacturer_id} using depth-2 API"
            )

            # Use depth-2 for models (this was the bug!)
            params = FilterSearchParams(
                dep=2,  # CHANGED: was 3, now 2 (models are depth-2)
                parval=manufacturer_id,
                selval=f"row_1_{manufacturer_id}",  # CHANGED: was row_2_, now row_1_
                ifnew="N",
                level_no2=0,
            )

            result = await self.get_filter_level(params)

            if result.success and result.options:
                logger.info(
                    f"Successfully got {len(result.options)} models for manufacturer {manufacturer_id}"
                )

                # Add manufacturer info to metadata
                result.meta.update(
                    {
                        "manufacturer_id": manufacturer_id,
                        "data_source": "api",
                        "api_level": "depth-2",
                        "note": "Using corrected depth-2 API call for models",
                    }
                )

                return result
            else:
                # If no models found, return empty but successful result
                logger.info(
                    f"No models found for manufacturer {manufacturer_id} (this may be normal)"
                )
                return FilterLevel(
                    success=True,
                    options=[],
                    level=2,
                    meta={
                        "manufacturer_id": manufacturer_id,
                        "data_source": "api",
                        "api_level": "depth-2",
                        "note": "No models available for this manufacturer",
                        "recommendation": "Use manufacturer filter only",
                    },
                )

        except Exception as e:
            logger.error(
                f"Error getting models for manufacturer {manufacturer_id}: {str(e)}"
            )
            return FilterLevel(
                success=False,
                options=[],
                level=2,
                meta={
                    "error": str(e),
                    "manufacturer_id": manufacturer_id,
                    "data_source": "error",
                },
            )

    async def get_submodels(self, manufacturer_id: str, model_id: str) -> FilterLevel:
        """
        Get bike submodels for specific manufacturer and model (depth-3)

        NEW: Proper depth-3 implementation for detailed model variants

        Args:
            manufacturer_id: Manufacturer ID (e.g., "119")
            model_id: Model ID (e.g., "336" for Sportster)
        """
        try:
            logger.info(
                f"Getting submodels for manufacturer {manufacturer_id}, model {model_id}"
            )

            # Use depth-3 for submodels
            params = FilterSearchParams(
                dep=3,
                parval=model_id,
                selval=f"row_2_{model_id}",
                ifnew="N",
                level_no2=0,
            )

            result = await self.get_filter_level(params)

            if result.success:
                logger.info(f"Got {len(result.options)} submodels for model {model_id}")

                result.meta.update(
                    {
                        "manufacturer_id": manufacturer_id,
                        "model_id": model_id,
                        "data_source": "api",
                        "api_level": "depth-3",
                        "note": "Detailed model variants/submodels",
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting submodels for model {model_id}: {str(e)}")
            return FilterLevel(
                success=False,
                options=[],
                level=3,
                meta={
                    "error": str(e),
                    "manufacturer_id": manufacturer_id,
                    "model_id": model_id,
                    "data_source": "error",
                },
            )

    async def get_filter_info(self) -> FilterInfo:
        """
        Get comprehensive filter information including categories and manufacturers
        """
        try:
            # Get categories and manufacturers in parallel
            categories_result = await self.get_categories()
            manufacturers_result = await self.get_manufacturers()

            if not categories_result.success or not manufacturers_result.success:
                logger.error("Failed to fetch filter info")
                return FilterInfo(
                    categories=[],
                    manufacturers=[],
                    popular_filters={
                        "popular_categories": [],
                        "popular_manufacturers": [],
                        "errors": ["Failed to fetch filter data"],
                    },
                )

            # Filter only available options
            available_categories = self.parser.filter_options_by_availability(
                categories_result.options
            )
            available_manufacturers = self.parser.filter_options_by_availability(
                manufacturers_result.options
            )

            # Get popular filters
            popular_categories = self.parser.get_popular_categories(
                available_categories
            )
            popular_manufacturers = self.parser.get_popular_manufacturers(
                available_manufacturers
            )

            # Get filter values from HTML page
            filter_values = await self.get_filter_values()

            return FilterInfo(
                categories=available_categories,
                manufacturers=available_manufacturers,
                filter_values=filter_values,
                popular_filters={
                    "popular_categories": popular_categories,
                    "popular_manufacturers": popular_manufacturers,
                    "total_categories": len(available_categories),
                    "total_manufacturers": len(available_manufacturers),
                },
            )

        except Exception as e:
            logger.error(f"Error getting filter info: {str(e)}")
            return FilterInfo(
                categories=[],
                manufacturers=[],
                popular_filters={
                    "popular_categories": [],
                    "popular_manufacturers": [],
                    "errors": [str(e)],
                },
            )

    def build_search_url(self, filters: BikeSearchFilters) -> str:
        """
        Build search URL with filters for bike listing

        Args:
            filters: Search filter parameters

        Returns:
            Complete URL for bike search
        """
        try:
            base_url = "https://www.bobaedream.co.kr/bike2/bike_list.php"

            # Build query parameters
            params = {}

            # Add non-None parameters
            for field_name, field_value in filters.dict().items():
                if field_value is not None:
                    if field_name == "level_no2" and isinstance(field_value, list):
                        # Handle multi-select parameters
                        for value in field_value:
                            params[f"{field_name}[]"] = value
                    elif field_name == "chk_point" and isinstance(field_value, list):
                        # Handle checkbox array parameters
                        for value in field_value:
                            params[f"{field_name}[]"] = value
                    else:
                        params[field_name] = field_value

            # Ensure required parameters
            if "ifnew" not in params:
                params["ifnew"] = "N"
            if "order" not in params:
                params["order"] = "update_time desc"
            if "view_size" not in params:
                params["view_size"] = "30"

            search_url = f"{base_url}?{urlencode(params, doseq=True)}"
            logger.info(f"Built search URL with {len(params)} parameters")

            return search_url

        except Exception as e:
            logger.error(f"Error building search URL: {str(e)}")
            # Return basic URL as fallback
            return "https://www.bobaedream.co.kr/bike2/bike_list.php?ifnew=N"

    def get_filter_suggestions(self) -> Dict[str, Any]:
        """
        Get filter suggestions for common searches
        """
        return {
            "popular_searches": [
                {
                    "name": "스쿠터 (혼다/야마하)",
                    "filters": {"ftype1": "1", "maker_no": "5"},
                    "description": "인기 스쿠터 브랜드",
                },
                {
                    "name": "레플리카 (600cc 이상)",
                    "filters": {"ftype1": "4", "cc": "600"},
                    "description": "고성능 스포츠 바이크",
                },
                {
                    "name": "네이키드 (국산)",
                    "filters": {"ftype1": "5", "gubun": "K"},
                    "description": "국산 네이키드 바이크",
                },
                {
                    "name": "할리데이비슨",
                    "filters": {"maker_no": "119"},
                    "description": "아메리칸 크루저",
                },
            ],
            "price_ranges": [
                {"name": "100만원 이하", "price2": "100"},
                {"name": "100-300만원", "price1": "100", "price2": "300"},
                {"name": "300-500만원", "price1": "300", "price2": "500"},
                {"name": "500만원 이상", "price1": "500"},
            ],
            "engine_sizes": [
                {"name": "125cc 이하", "cc": "125"},
                {"name": "250cc", "cc": "250"},
                {"name": "400cc", "cc": "400"},
                {"name": "600cc 이상", "cc": "600"},
            ],
        }

    async def get_filter_values(self):
        """
        Get available values for all filter types by parsing the HTML form page
        """
        try:
            # Check cache first
            cache_key = "filter_values_html"
            if cache_key in self._cache:
                logger.info("Returning cached filter values")
                return self._cache[cache_key]

            # Fetch the bike listing page to get filter form
            filter_page_url = "https://www.bobaedream.co.kr/bike2/bike_list.php?ifnew=N"

            logger.info(f"Fetching filter values from: {filter_page_url}")

            response = await self.proxy_client.make_request(filter_page_url)

            if not response.get("success"):
                logger.error(f"Failed to fetch filter page: {response.get('error')}")
                return FilterValues()

            html_content = response.get("text", "")

            # Parse filter values from HTML
            filter_values = self.parser.parse_filter_values_from_html(html_content)

            # Cache the results
            self._cache[cache_key] = filter_values

            logger.info("Successfully fetched and cached filter values")
            return filter_values

        except Exception as e:
            logger.error(f"Error getting filter values: {str(e)}")
            return FilterValues()

    def clear_cache(self):
        """Clear filter cache"""
        self._cache.clear()
        logger.info("Filter cache cleared")
