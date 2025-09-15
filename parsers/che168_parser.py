"""
Che168 Parser
Handles JSON parsing for Chinese car marketplace API responses
"""

import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from schemas.che168 import (
    Che168ApiResponse,
    Che168SearchResponse,
    Che168CarListing,
    Che168ServiceOption,
    Che168CarDetailResponse,
    Che168FiltersResponse,
    Che168CarTag,
    Che168CarTags,
    Che168CPCInfo,
    Che168Consignment,
    Che168BrandsResponse,
    Che168BrandGroup,
    Che168Brand,
    Che168ModelsResponse,
    Che168ModelFilter,
    Che168YearsResponse,
    Che168YearFilter,
)

logger = logging.getLogger(__name__)


class Che168Parser:
    """
    Comprehensive parser for Che168 API responses
    Handles JSON parsing and data transformation
    """

    def __init__(self):
        self.base_url = "https://api2scsou.che168.com"
        self.parser_name = "che168_json"

    def parse_api_response(self, json_data: Dict) -> Che168SearchResponse:
        """
        Parse main API response from Che168 search endpoint

        Args:
            json_data: Raw JSON response from API

        Returns:
            Che168SearchResponse with parsed data
        """
        try:
            if json_data.get("returncode") != 0:
                return Che168SearchResponse(
                    success=False,
                    cars=[],
                    pagination={},
                    service_filters=[],
                    total_count=0,
                    meta={
                        "parser": "che168_api",
                        "error": f"API returned code {json_data.get('returncode')}: {json_data.get('message', 'Unknown error')}",
                    },
                )

            result = json_data.get("result", {})

            # Parse car listings
            car_listings = []
            for car_data in result.get("carlist", []):
                try:
                    car = self._parse_car_listing(car_data)
                    if car:
                        car_listings.append(car)
                except Exception as e:
                    logger.warning(f"Failed to parse car listing: {str(e)}")
                    continue

            # Parse service filters
            service_filters = []
            for service_data in result.get("service", []):
                try:
                    service = self._parse_service_option(service_data)
                    if service:
                        service_filters.append(service)
                except Exception as e:
                    logger.warning(f"Failed to parse service filter: {str(e)}")
                    continue

            # Build pagination info
            pagination = {
                "current_page": result.get("pageindex", 1),
                "page_size": result.get("pagesize", 10),
                "total_pages": result.get("pagecount", 0),
                "total_count": result.get("totalcount", 0),
                "query_id": result.get("queryid", ""),
            }

            return Che168SearchResponse(
                success=True,
                cars=car_listings,
                pagination=pagination,
                service_filters=service_filters,
                total_count=result.get("totalcount", 0),
                meta={
                    "parser": "che168_api",
                    "parsed_cars": len(car_listings),
                    "api_message": json_data.get("message", ""),
                    "style_type": result.get("styletype", 1),
                    "show_type": result.get("showtype", 2),
                },
            )

        except Exception as e:
            logger.error(f"Error parsing Che168 API response: {str(e)}")
            return Che168SearchResponse(
                success=False,
                cars=[],
                pagination={},
                service_filters=[],
                total_count=0,
                meta={
                    "parser": "che168_api",
                    "error": f"Parser error: {str(e)}",
                },
            )

    def _parse_car_listing(self, car_data: Dict) -> Optional[Che168CarListing]:
        """Parse individual car listing data"""
        try:
            # Parse car tags
            cartags_data = car_data.get("cartags", {})
            cartags = Che168CarTags(
                p1=[self._parse_car_tag(tag) for tag in cartags_data.get("p1", [])],
                p2=[self._parse_car_tag(tag) for tag in cartags_data.get("p2", [])],
                p3=[self._parse_car_tag(tag) for tag in cartags_data.get("p3", [])],
            )

            # Parse CPC info
            cpcinfo_data = car_data.get("cpcinfo", {})
            cpcinfo = Che168CPCInfo(
                adid=cpcinfo_data.get("adid", 0),
                platform=cpcinfo_data.get("platform", 1),
                cpctype=cpcinfo_data.get("cpctype", 0),
                position=cpcinfo_data.get("position", 0),
                encryptinfo=cpcinfo_data.get("encryptinfo", ""),
            )

            # Parse consignment info
            consignment_data = car_data.get("consignment", {})
            consignment = Che168Consignment(
                isconsignment=consignment_data.get("isconsignment", 0),
                endtime=consignment_data.get("endtime", 0),
                imurl=consignment_data.get("imurl", ""),
                isyouxin=consignment_data.get("isyouxin", 0),
                citytype=consignment_data.get("citytype", 1),
            )

            # Create car listing object
            car = Che168CarListing(
                infoid=car_data.get("infoid", 0),
                carname=car_data.get("carname", ""),
                cname=car_data.get("cname", ""),
                dealerid=car_data.get("dealerid", 0),
                mileage=car_data.get("mileage", "0"),
                cityid=car_data.get("cityid", 0),
                seriesid=car_data.get("seriesid", 0),
                specid=car_data.get("specid", 0),
                sname=car_data.get("sname", ""),
                syname=car_data.get("syname", ""),
                price=car_data.get("price", "0"),
                saveprice=car_data.get("saveprice", ""),
                discount=car_data.get("discount", ""),
                firstregyear=car_data.get("firstregyear", ""),
                fromtype=car_data.get("fromtype", 0),
                imageurl=car_data.get("imageurl", ""),
                cartype=car_data.get("cartype", 0),
                bucket=car_data.get("bucket", 0),
                isunion=car_data.get("isunion", 0),
                isoutsite=car_data.get("isoutsite", 0),
                videourl=car_data.get("videourl", ""),
                car_level=car_data.get("car_level", 0),
                dealer_level=car_data.get("dealer_level", ""),
                downpayment=car_data.get("downpayment", "0"),
                url=car_data.get("url", ""),
                position=car_data.get("position", 0),
                isnewly=car_data.get("isnewly", 0),
                kindname=car_data.get("kindname", ""),
                usc_adid=car_data.get("usc_adid", 0),
                particularactivity=car_data.get("particularactivity", 0),
                livestatus=car_data.get("livestatus", 0),
                stra=car_data.get("stra", ""),
                springid=car_data.get("springid", ""),
                followcount=car_data.get("followcount", 0),
                cxctype=car_data.get("cxctype", 0),
                isfqtj=car_data.get("isfqtj", 0),
                isrelivedbuy=car_data.get("isrelivedbuy", 0),
                photocount=car_data.get("photocount", 0),
                isextwarranty=car_data.get("isextwarranty", 0),
                offertype=car_data.get("offertype", 0),
                cpcinfo=cpcinfo,
                displacement=car_data.get("displacement", ""),
                environmental=car_data.get("environmental", ""),
                liveurl=car_data.get("liveurl", ""),
                imuserid=car_data.get("imuserid", ""),
                consignment=consignment,
                pv_extstr=car_data.get("pv_extstr", ""),
                act_discount=car_data.get("act_discount", ""),
                cartags=cartags,
            )

            return car

        except Exception as e:
            logger.error(f"Error parsing car listing: {str(e)}")
            return None

    def _parse_car_tag(self, tag_data: Dict) -> Che168CarTag:
        """Parse individual car tag"""
        return Che168CarTag(
            title=tag_data.get("title", ""),
            bg_color=tag_data.get("bg_color", ""),
            bg_color_end=tag_data.get("bg_color_end", ""),
            font_color=tag_data.get("font_color", ""),
            border_color=tag_data.get("border_color", ""),
            bg_color_direction=tag_data.get("bg_color_direction", 0),
            stype=tag_data.get("stype", ""),
            sort=tag_data.get("sort", 0),
            icon=tag_data.get("icon", ""),
            url=tag_data.get("url", ""),
            image=tag_data.get("image", ""),
            imgheight=tag_data.get("imgheight", 0),
            imgwidth=tag_data.get("imgwidth", 0),
        )

    def _parse_service_option(self, service_data: Dict) -> Optional[Che168ServiceOption]:
        """Parse service filter option"""
        try:
            return Che168ServiceOption(
                title=service_data.get("title", ""),
                subtitle=service_data.get("subtitle", ""),
                key=service_data.get("key", ""),
                value=service_data.get("value", ""),
                icon=service_data.get("icon", ""),
                iconfocus=service_data.get("iconfocus", ""),
                tag=service_data.get("tag", ""),
                viewtype=service_data.get("viewtype", 100),
                iconwidth=service_data.get("iconwidth", 0),
                badgetitle=service_data.get("badgetitle", ""),
                headbgurl=service_data.get("headbgurl", ""),
                headsubbgurl=service_data.get("headsubbgurl", ""),
                titlecolorfocus=service_data.get("titlecolorfocus", ""),
                titlecolor=service_data.get("titlecolor", ""),
                tabtype=service_data.get("tabtype", 0),
                linkurl=service_data.get("linkurl", ""),
                basevalue=service_data.get("basevalue", ""),
                dtype=service_data.get("dtype", 0),
                subvalue=service_data.get("subvalue", ""),
                subspecname=service_data.get("subspecname", ""),
                needreddot=service_data.get("needreddot", 0),
                brandvalue=service_data.get("brandvalue", ""),
                brandname=service_data.get("brandname", ""),
                isgray=service_data.get("isgray", 0),
            )
        except Exception as e:
            logger.error(f"Error parsing service option: {str(e)}")
            return None

    def parse_car_detail(self, json_data: Dict, info_id: int) -> Che168CarDetailResponse:
        """
        Parse individual car detail response

        Args:
            json_data: Raw JSON response
            info_id: Car info ID

        Returns:
            Che168CarDetailResponse with car details
        """
        try:
            if json_data.get("returncode") != 0:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error=f"API error: {json_data.get('message', 'Unknown error')}",
                    meta={"parser": "che168_detail", "info_id": info_id},
                )

            result = json_data.get("result", {})
            car_data = result.get("carinfo", {})

            if not car_data:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error="No car data found",
                    meta={"parser": "che168_detail", "info_id": info_id},
                )

            car = self._parse_car_listing(car_data)
            if not car:
                return Che168CarDetailResponse(
                    success=False,
                    car=None,
                    error="Failed to parse car data",
                    meta={"parser": "che168_detail", "info_id": info_id},
                )

            return Che168CarDetailResponse(
                success=True,
                car=car,
                error=None,
                meta={
                    "parser": "che168_detail",
                    "info_id": info_id,
                    "api_message": json_data.get("message", ""),
                },
            )

        except Exception as e:
            logger.error(f"Error parsing car detail for {info_id}: {str(e)}")
            return Che168CarDetailResponse(
                success=False,
                car=None,
                error=f"Parser error: {str(e)}",
                meta={"parser": "che168_detail", "info_id": info_id},
            )

    def parse_filters(self, json_data: Dict) -> Che168FiltersResponse:
        """
        Parse available filters from API response

        Args:
            json_data: Raw JSON response

        Returns:
            Che168FiltersResponse with available filters
        """
        try:
            if json_data.get("returncode") != 0:
                return Che168FiltersResponse(
                    success=False,
                    service_types=[],
                    meta={
                        "parser": "che168_filters",
                        "error": f"API error: {json_data.get('message', 'Unknown error')}",
                    },
                )

            result = json_data.get("result", {})
            service_filters = []

            for service_data in result.get("service", []):
                service = self._parse_service_option(service_data)
                if service:
                    service_filters.append(service)

            return Che168FiltersResponse(
                success=True,
                service_types=service_filters,
                meta={
                    "parser": "che168_filters",
                    "total_filters": len(service_filters),
                    "api_message": json_data.get("message", ""),
                },
            )

        except Exception as e:
            logger.error(f"Error parsing filters: {str(e)}")
            return Che168FiltersResponse(
                success=False,
                service_types=[],
                meta={
                    "parser": "che168_filters",
                    "error": f"Parser error: {str(e)}",
                },
            )

    def parse_brands_response(self, json_data: Dict) -> Che168BrandsResponse:
        """
        Parse brands API response from Che168

        Args:
            json_data: Raw JSON response from brands API

        Returns:
            Che168BrandsResponse with parsed brands data
        """
        try:
            if json_data.get("returncode") != 0:
                return Che168BrandsResponse(
                    success=False,
                    brands=[],
                    brand_groups=[],
                    total_brands=0,
                    meta={
                        "parser": "che168_brands",
                        "error": f"API returned code {json_data.get('returncode')}: {json_data.get('message', 'Unknown error')}",
                    },
                )

            result = json_data.get("result", {})
            brands_data = result.get("brands", [])

            brand_groups = []
            all_brands = []

            for group_data in brands_data:
                try:
                    # Parse individual brands in this group
                    brands_in_group = []
                    for brand_data in group_data.get("brand", []):
                        try:
                            brand = Che168Brand(
                                bid=brand_data.get("bid", 0),
                                name=brand_data.get("name", ""),
                                py=brand_data.get("py", ""),
                                icon=brand_data.get("icon", ""),
                                price=brand_data.get("price", "0万"),
                                on_sale_num=brand_data.get("on_sale_num", 0),
                                dtype=brand_data.get("dtype", 0),
                                url=brand_data.get("url", ""),
                            )
                            brands_in_group.append(brand)
                            all_brands.append(brand)
                        except Exception as e:
                            logger.warning(f"Failed to parse brand: {str(e)}")
                            continue

                    # Create brand group
                    if brands_in_group:
                        brand_group = Che168BrandGroup(
                            letter=group_data.get("letter", ""),
                            brand=brands_in_group,
                        )
                        brand_groups.append(brand_group)

                except Exception as e:
                    logger.warning(f"Failed to parse brand group: {str(e)}")
                    continue

            return Che168BrandsResponse(
                success=True,
                brands=all_brands,
                brand_groups=brand_groups,
                total_brands=len(all_brands),
                meta={
                    "parser": "che168_brands",
                    "total_groups": len(brand_groups),
                    "api_message": json_data.get("message", ""),
                },
            )

        except Exception as e:
            logger.error(f"Error parsing brands response: {str(e)}")
            return Che168BrandsResponse(
                success=False,
                brands=[],
                brand_groups=[],
                total_brands=0,
                meta={
                    "parser": "che168_brands",
                    "error": f"Parser error: {str(e)}",
                },
            )

    def parse_models_from_search(self, search_response: Che168SearchResponse, brand_id: int) -> List[Che168ModelFilter]:
        """
        Extract model filters from search response

        Args:
            search_response: Search response containing filters
            brand_id: Brand ID for context

        Returns:
            List of model filters
        """
        models = []

        try:
            # In a real scenario, we would need to make an actual search request and extract from the raw response
            # Since we're working with the parsed response, we'll return an empty list for now
            # This would need to be implemented by storing the raw response in the search result
            logger.info(f"Model extraction for brand {brand_id} - would need raw API response")

            # Placeholder implementation - in practice, you'd extract from the filters array in the raw API response
            # where filters have key="seriesid" and dtype matching model type

        except Exception as e:
            logger.error(f"Error extracting models from search response: {str(e)}")

        return models

    def parse_years_from_search(self, search_response: Che168SearchResponse, brand_id: int, series_id: int) -> List[Che168YearFilter]:
        """
        Extract year filters from search response

        Args:
            search_response: Search response containing filters
            brand_id: Brand ID for context
            series_id: Series ID for context

        Returns:
            List of year filters
        """
        years = []

        try:
            # Similar to models, this would extract from the raw API response filters array
            # where filters have key="seriesyearid" and dtype matching year type
            logger.info(f"Year extraction for brand {brand_id}, series {series_id} - would need raw API response")

            # Placeholder implementation

        except Exception as e:
            logger.error(f"Error extracting years from search response: {str(e)}")

        return years

    def parse_filters_from_raw_response(self, json_data: Dict, filter_type: str) -> List[Dict]:
        """
        Parse filters from raw API response

        Args:
            json_data: Raw JSON response from API
            filter_type: Type of filter to extract ('seriesid' for models, 'seriesyearid' for years)

        Returns:
            List of filter dictionaries
        """
        filters = []

        try:
            result = json_data.get("result", {})
            filters_data = result.get("filters", [])

            for filter_data in filters_data:
                if filter_data.get("key") == filter_type:
                    filters.append({
                        "title": filter_data.get("title", ""),
                        "key": filter_data.get("key", ""),
                        "value": filter_data.get("value", ""),
                        "dtype": filter_data.get("dtype", 0),
                        "subvalue": filter_data.get("subvalue", ""),
                        "subspecname": filter_data.get("subspecname", ""),
                    })

        except Exception as e:
            logger.error(f"Error parsing filters from raw response: {str(e)}")

        return filters