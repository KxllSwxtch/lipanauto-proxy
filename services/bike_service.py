"""
Business logic service for bike operations
Integrates with existing proxy infrastructure and parsing
"""

import logging
from typing import Dict, Optional
from urllib.parse import urlencode
from bs4.dammit import UnicodeDammit

from parsers.bobaedream_parser import BobaeDreamBikeParser
from schemas.bikes import BikeSearchParams, BikeSearchResponse, BikeDetailResponse
from schemas.bike_filters import BikeSearchFilters
from services.bike_filters_service import BikeFiltersService

logger = logging.getLogger(__name__)


class BikeService:
    """
    Service layer for bike operations
    Handles business logic, validation, and integration
    """

    def __init__(self, proxy_client):
        """
        Initialize with existing proxy client

        Args:
            proxy_client: EncarProxyClient instance for HTTP requests
        """
        self.proxy_client = proxy_client
        self.parser = BobaeDreamBikeParser()
        self.filters_service = BikeFiltersService(proxy_client)
        self.base_url = "https://www.bobaedream.co.kr"

        # Enhanced headers for Korean site
        self.korean_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        }

        # Cookies for session management
        self.default_cookies = {
            "_ga": "GA1.1.1493642756.1750328716",
            "_ga_F5YV62DJXL": "GS2.1.s1750333343$o2$g0$t1750333448$j60$l0$h0",
        }

    async def search_bikes(self, params: BikeSearchParams) -> BikeSearchResponse:
        """
        Search for bikes using the provided parameters

        Args:
            params: Search parameters (ifnew, gubun, tab, page, sort)

        Returns:
            BikeSearchResponse: Search results with bikes and metadata
        """
        try:
            # Build URL with parameters
            url = self._build_search_url(params)

            logger.info(f"Searching bikes with URL: {url}")

            # Make request through proxy client
            response = await self.proxy_client.make_request(url)

            if not response.get("success"):
                return BikeSearchResponse(
                    success=False,
                    bikes=[],
                    meta={
                        "error": response.get("error", "Request failed"),
                        "url": url,
                        "service": "bike_service",
                    },
                )

            # Handle encoding for Korean content
            html_content = response.get("text", "")

            # Parse the HTML content
            search_result = self.parser.parse_bike_listings(html_content, self.base_url)

            # Add request metadata
            search_result.meta.update(
                {
                    "request_url": url,
                    "response_size": len(html_content),
                    "proxy_attempts": response.get("attempt", 1),
                    "service": "bike_service",
                }
            )

            logger.info(f"Successfully parsed {len(search_result.bikes)} bikes")

            return search_result

        except Exception as e:
            logger.error(f"Error in bike search: {str(e)}")
            return BikeSearchResponse(
                success=False,
                bikes=[],
                meta={"error": str(e), "service": "bike_service"},
            )

    async def get_bike_details(self, bike_id: str) -> Dict:
        """
        Get detailed information for a specific bike

        Args:
            bike_id: Unique bike identifier

        Returns:
            Dict: Detailed bike information or error
        """
        try:
            # Build detail page URL
            url = f"{self.base_url}/bike2/bike_view.php?no={bike_id}&gubun=K&ifnew=N"

            logger.info(f"Fetching bike details for ID {bike_id}: {url}")

            # Make request through proxy client
            response = await self.proxy_client.make_request(url)

            if not response.get("success"):
                return {
                    "success": False,
                    "bike": None,
                    "meta": {
                        "error": response.get("error", "Request failed"),
                        "bike_id": bike_id,
                        "url": url,
                        "service": "bike_service",
                    },
                }

            # Get HTML content
            html_content = response.get("text", "")

            # Parse the detail page
            detail_result = self.parser.parse_bike_detail(html_content, bike_id)

            # Add request metadata
            detail_result["meta"].update(
                {
                    "request_url": url,
                    "response_size": len(html_content),
                    "proxy_attempts": response.get("attempt", 1),
                    "service": "bike_service",
                }
            )

            if detail_result.get("success"):
                logger.info(f"Successfully parsed details for bike {bike_id}")
            else:
                logger.warning(f"Failed to parse details for bike {bike_id}")

            return detail_result

        except Exception as e:
            logger.error(f"Error fetching bike details for ID {bike_id}: {str(e)}")
            return {
                "success": False,
                "bike": None,
                "meta": {
                    "error": str(e),
                    "bike_id": bike_id,
                    "service": "bike_service",
                },
            }

    def get_supported_filters(self) -> Dict:
        """
        Get information about supported search filters

        Returns:
            Dict: Filter information and descriptions
        """
        return {
            "success": True,
            "filters": {
                "ifnew": {
                    "description": "Vehicle condition",
                    "options": {"N": "Used bikes (중고)", "Y": "New bikes (신차)"},
                    "default": "N",
                },
                "gubun": {
                    "description": "Origin classification",
                    "options": {
                        "K": "Korean bikes (국산)",
                        "I": "Imported bikes (수입)",
                    },
                    "default": None,
                },
                "tab": {
                    "description": "Listing category",
                    "options": {
                        "2": "Verified listings (검증매물)",
                        "3": "Premium listings (프리미엄)",
                        "4": "Quick sale (급매)",
                    },
                    "default": None,
                },
                "page": {
                    "description": "Page number for pagination",
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                },
                "sort": {
                    "description": "Sort order",
                    "options": {
                        "1": "Recent (최신순)",
                        "2": "Low price (낮은가격순)",
                        "3": "High price (높은가격순)",
                        "4": "Most viewed (조회순)",
                    },
                    "default": None,
                },
            },
            "site_info": {
                "name": "보배드림 (BobaeDream)",
                "url": self.base_url,
                "encoding": "EUC-KR",
                "supported_vehicles": ["motorcycles", "scooters", "bikes"],
            },
        }

    def _build_search_url(self, params: BikeSearchParams) -> str:
        """
        Build search URL from parameters

        Args:
            params: Search parameters

        Returns:
            str: Complete search URL
        """
        # Base URL for bike listings
        base_url = f"{self.base_url}/bike2/bike_list.php"

        # Build query parameters
        query_params = {}

        # Always include ifnew parameter
        query_params["ifnew"] = params.ifnew

        # Add optional parameters if provided
        if params.gubun:
            query_params["gubun"] = params.gubun

        if params.tab:
            query_params["tab"] = params.tab

        if params.page and params.page > 1:
            query_params["page"] = str(params.page)

        if params.sort:
            query_params["sort"] = params.sort

        # Build final URL
        if query_params:
            url = f"{base_url}?{urlencode(query_params)}"
        else:
            url = base_url

        return url

    def _fix_response_encoding(self, html_content: str) -> str:
        """
        Fix encoding issues in response content

        Args:
            html_content: Raw HTML content

        Returns:
            str: Fixed content with proper encoding
        """
        try:
            # Check if content has encoding issues
            if isinstance(html_content, str):
                # Look for common Korean encoding problems
                if any(
                    char in html_content for char in ["°³ÀÎ", "È¿¼º", "º¸¹è", "¸ñ·Ï"]
                ):
                    logger.info("Detected Korean encoding issues, attempting to fix")

                    # Try to fix with EUC-KR
                    try:
                        # Convert back to bytes with latin-1 and decode with EUC-KR
                        byte_content = html_content.encode("latin-1")
                        fixed_content = byte_content.decode("euc-kr")
                        logger.info("Successfully fixed encoding with EUC-KR")
                        return fixed_content
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        # Use UnicodeDammit as fallback
                        logger.info("Trying UnicodeDammit for encoding detection")
                        dammit = UnicodeDammit(
                            html_content.encode("latin-1"),
                            ["euc-kr", "cp949", "utf-8", "iso-8859-1"],
                        )
                        if dammit.unicode_markup:
                            return dammit.unicode_markup

            return html_content

        except Exception as e:
            logger.warning(f"Error fixing response encoding: {str(e)}")
            return html_content

    def _parse_bike_details(self, html_content: str, bike_id: str) -> Dict:
        """
        Parse detailed bike information from detail page

        Args:
            html_content: HTML content of detail page
            bike_id: Bike identifier

        Returns:
            Dict: Parsed bike details
        """
        # Simplified detail parsing - could be expanded later
        return {
            "bike_id": bike_id,
            "detail_page_available": True,
            "content_length": len(html_content),
            "note": "Detailed parsing not implemented yet - basic info extracted from listing page",
        }

    async def search_bikes_with_filters(
        self, filters: BikeSearchFilters
    ) -> BikeSearchResponse:
        """
        Search bikes using advanced filters

        Args:
            filters: Advanced search filter parameters

        Returns:
            BikeSearchResponse: Search results with bikes and metadata
        """
        try:
            # Build URL with filters
            url = self.filters_service.build_search_url(filters)

            logger.info(f"Searching bikes with filters: {url}")

            # Make request through proxy client
            response = await self.proxy_client.make_request(url)

            if not response.get("success"):
                return BikeSearchResponse(
                    success=False,
                    bikes=[],
                    meta={
                        "error": response.get("error", "Request failed"),
                        "url": url,
                        "service": "bike_service",
                        "filters_applied": True,
                    },
                )

            # Handle encoding for Korean content
            html_content = response.get("text", "")

            # Parse the HTML content
            search_result = self.parser.parse_bike_listings(html_content, self.base_url)

            # Add request metadata
            search_result.meta.update(
                {
                    "request_url": url,
                    "response_size": len(html_content),
                    "proxy_attempts": response.get("attempt", 1),
                    "service": "bike_service",
                    "filters_applied": True,
                    "filter_count": len(
                        [v for v in filters.dict().values() if v is not None]
                    ),
                }
            )

            logger.info(
                f"Successfully parsed {len(search_result.bikes)} bikes with filters"
            )

            return search_result

        except Exception as e:
            logger.error(f"Error in filtered bike search: {str(e)}")
            return BikeSearchResponse(
                success=False,
                bikes=[],
                meta={
                    "error": str(e),
                    "service": "bike_service",
                    "filters_applied": True,
                },
            )

    async def get_filter_info(self):
        """Get comprehensive filter information"""
        return await self.filters_service.get_filter_info()

    async def get_categories(self):
        """Get bike categories"""
        return await self.filters_service.get_categories()

    async def get_manufacturers(self):
        """Get bike manufacturers"""
        return await self.filters_service.get_manufacturers()

    async def get_models(self, manufacturer_id: str):
        """Get models for specific manufacturer"""
        return await self.filters_service.get_models(manufacturer_id)

    def get_filter_suggestions(self):
        """Get filter suggestions for common searches"""
        return self.filters_service.get_filter_suggestions()
