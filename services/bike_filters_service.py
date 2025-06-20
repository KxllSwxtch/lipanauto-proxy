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
)
from parsers.bike_filters_parser import BikeFiltersParser

logger = logging.getLogger(__name__)


class BikeFiltersService:
    """
    Service for managing bike filter operations
    Integrates with bobaedream.co.kr filter API
    """

    BASE_URL = "https://www.bobaedream.co.kr/bike2/get_cardepth.php"

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
        """Get bike manufacturers (level 1)"""
        params = FilterSearchParams(dep=1, parval="", selval="", ifnew="N", level_no2=0)
        return await self.get_filter_level(params)

    async def get_models(
        self, manufacturer_id: str, category_id: str = ""
    ) -> FilterLevel:
        """
        Get bike models for specific manufacturer (level 3)

        Args:
            manufacturer_id: Manufacturer ID (e.g., "1928")
            category_id: Category ID for filtering (optional)
        """
        params = FilterSearchParams(
            dep=3,
            parval=manufacturer_id,
            selval=f"row_2_{manufacturer_id}",
            ifnew="N",
            level_no2=0,
        )
        return await self.get_filter_level(params)

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
                    popular_filters={"error": "Failed to fetch filter data"},
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

            return FilterInfo(
                categories=available_categories,
                manufacturers=available_manufacturers,
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
                categories=[], manufacturers=[], popular_filters={"error": str(e)}
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

    def clear_cache(self):
        """Clear filter cache"""
        self._cache.clear()
        logger.info("Filter cache cleared")
