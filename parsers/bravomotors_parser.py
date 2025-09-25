"""
Che168 Parser
Handles JSON parsing for che168.com API responses from Chinese car marketplace
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from schemas.bravomotors import (
    Che168SearchResponse,
    Che168CarListing,
    Che168CarDetailResponse,
    Che168CarDetailSection,
    Che168CarDetailItem,
    Che168FiltersResponse,
    Che168Brand,
    Che168BrandGroup,
    Che168BrandsResponse,
    Che168FilterItem,
    TranslationResponse,
)

logger = logging.getLogger(__name__)


class Che168Parser:
    """
    Comprehensive parser for che168.com API responses
    Handles JSON parsing and data transformation for Chinese car marketplace data
    """

    def __init__(self):
        self.base_url = "https://www.che168.com"
        self.parser_name = "che168_json"

        # CNY to RUB conversion rate (approximate)
        self.cny_to_rub_rate = 15.04

    def parse_brands_response(self, json_data: Dict) -> Che168BrandsResponse:
        """
        Parse brands API response from che168.com

        Args:
            json_data: Raw JSON response from brands API

        Returns:
            Che168BrandsResponse with parsed brands data
        """
        try:
            if json_data.get("returncode") != 0:
                logger.error(f"Brands API returned error: {json_data.get('message', 'Unknown error')}")
                return Che168BrandsResponse(
                    returncode=json_data.get("returncode", -1),
                    message=json_data.get("message", "Failed to fetch brands"),
                    result={}
                )

            result = json_data.get("result", {})
            parsed_result = {}

            # Parse each brand category (hotbrand, allbrand, etc.)
            for category, brands_data in result.items():
                if isinstance(brands_data, list):
                    parsed_items = []
                    for item_data in brands_data:
                        try:
                            # Check if this is a brand group (has 'letter' and 'brand' fields)
                            if 'letter' in item_data and 'brand' in item_data:
                                # Parse brand group
                                group_brands = []
                                for brand_data in item_data.get('brand', []):
                                    try:
                                        brand = Che168Brand(**brand_data)
                                        group_brands.append(brand)
                                    except Exception as e:
                                        logger.warning(f"Failed to parse brand in group {item_data.get('letter', 'unknown')}: {e}")
                                        continue

                                group = Che168BrandGroup(
                                    letter=item_data['letter'],
                                    brand=group_brands,
                                    on_sale_num=item_data.get('on_sale_num', 0)
                                )
                                parsed_items.append(group)
                            else:
                                # Parse individual brand
                                brand = Che168Brand(**item_data)
                                parsed_items.append(brand)
                        except Exception as e:
                            logger.warning(f"Failed to parse item in {category}: {e}")
                            continue
                    parsed_result[category] = parsed_items
                elif isinstance(brands_data, bool):
                    # Handle boolean flags like 'hasonlinesale'
                    parsed_result[category] = brands_data
                else:
                    parsed_result[category] = brands_data

            return Che168BrandsResponse(
                returncode=json_data["returncode"],
                message=json_data["message"],
                result=parsed_result
            )

        except Exception as e:
            logger.error(f"Failed to parse brands response: {e}")
            return Che168BrandsResponse(
                returncode=-1,
                message=f"Parse error: {str(e)}",
                result={}
            )

    def parse_car_search_response(self, json_data: Dict) -> Che168SearchResponse:
        """
        Parse car search API response from che168.com

        Args:
            json_data: Raw JSON response from search API

        Returns:
            Che168SearchResponse with parsed data
        """
        try:
            # Check response status
            if json_data.get("returncode") != 0:
                return Che168SearchResponse(
                    returncode=json_data.get("returncode", -1),
                    message=json_data.get("message", "Search failed"),
                    result={},
                    success=False
                )

            result = json_data.get("result", {})
            cars = []
            filters = []

            # Parse car listings from carlist
            carlist = result.get("carlist", [])
            for car_data in carlist:
                try:
                    # Convert price from 万元 to actual price and RUB
                    price_wan = float(car_data.get("price", "0"))
                    price_rub = price_wan * 10000 * self.cny_to_rub_rate if price_wan > 0 else None

                    car = Che168CarListing(
                        infoid=car_data["infoid"],
                        carname=car_data["carname"],
                        cname=car_data["cname"],
                        dealerid=car_data["dealerid"],
                        mileage=car_data["mileage"],
                        cityid=car_data["cityid"],
                        seriesid=car_data["seriesid"],
                        specid=car_data["specid"],
                        sname=car_data.get("sname", ""),
                        syname=car_data.get("syname", ""),
                        price=car_data["price"],
                        price_rub=price_rub,
                        saveprice=car_data.get("saveprice", ""),
                        discount=car_data.get("discount", ""),
                        firstregyear=car_data["firstregyear"],
                        fromtype=car_data["fromtype"],
                        imageurl=car_data["imageurl"],
                        cartype=car_data["cartype"],
                        bucket=car_data.get("bucket", 0),
                        isunion=car_data.get("isunion", 0)
                    )
                    cars.append(car)

                except Exception as e:
                    logger.warning(f"Failed to parse car listing {car_data.get('infoid', 'unknown')}: {e}")
                    continue

            # Parse filter items (service, brand, price, etc.)
            filter_categories = [
                "service", "brand", "price", "agerange", "mileage",
                "fueltype", "transmission", "displacement", "series"
            ]

            for category in filter_categories:
                if category in result:
                    category_filters = result[category]
                    if isinstance(category_filters, list):
                        for filter_data in category_filters:
                            try:
                                filter_item = Che168FilterItem(**filter_data)
                                filters.append(filter_item)
                            except Exception as e:
                                logger.warning(f"Failed to parse filter item in {category}: {e}")
                                continue

            return Che168SearchResponse(
                returncode=json_data["returncode"],
                message=json_data["message"],
                result=result,
                cars=cars,
                total_count=result.get("totalcount", len(cars)),
                page_count=result.get("pagecount", 1),
                current_page=result.get("pageindex", 1),
                page_size=result.get("pagesize", 12),
                filters=filters,
                success=True
            )

        except Exception as e:
            logger.error(f"Failed to parse search response: {e}")
            return Che168SearchResponse(
                returncode=-1,
                message=f"Parse error: {str(e)}",
                result={},
                success=False
            )

    def parse_car_detail_response(self, json_data: Dict) -> Che168CarDetailResponse:
        """
        Parse car detail API response from che168.com

        Args:
            json_data: Raw JSON response from car detail API

        Returns:
            Che168CarDetailResponse with parsed detail data
        """
        try:
            if json_data.get("returncode") != 0:
                return Che168CarDetailResponse(
                    returncode=json_data.get("returncode", -1),
                    message=json_data.get("message", "Failed to get car details"),
                    result=[],
                    success=False
                )

            result = json_data.get("result", [])
            sections = []

            # Parse each detail section (engine, body, etc.)
            for section_data in result:
                try:
                    items = []

                    # Parse data items in each section
                    for item_data in section_data.get("data", []):
                        try:
                            item = Che168CarDetailItem(
                                name=item_data["name"],
                                content=item_data["content"],
                                countline=item_data.get("countline", 0)
                            )
                            items.append(item)
                        except Exception as e:
                            logger.warning(f"Failed to parse detail item {item_data.get('name', 'unknown')}: {e}")
                            continue

                    section = Che168CarDetailSection(
                        title=section_data["title"],
                        data=items
                    )
                    sections.append(section)

                except Exception as e:
                    logger.warning(f"Failed to parse detail section {section_data.get('title', 'unknown')}: {e}")
                    continue

            return Che168CarDetailResponse(
                returncode=json_data["returncode"],
                message=json_data["message"],
                result=sections,
                success=True
            )

        except Exception as e:
            logger.error(f"Failed to parse car detail response: {e}")
            return Che168CarDetailResponse(
                returncode=-1,
                message=f"Parse error: {str(e)}",
                result=[],
                success=False
            )

    def create_filters_response(self, brands: List[Che168Brand]) -> Che168FiltersResponse:
        """
        Create structured filters response from brands and predefined options

        Args:
            brands: List of available car brands

        Returns:
            Che168FiltersResponse with all filter options
        """
        try:
            price_ranges = [
                {"value": "0-5", "label": "0-5万元"},
                {"value": "5-10", "label": "5-10万元"},
                {"value": "10-15", "label": "10-15万元"},
                {"value": "15-20", "label": "15-20万元"},
                {"value": "20-30", "label": "20-30万元"},
                {"value": "30-50", "label": "30-50万元"},
                {"value": "50-100", "label": "50-100万元"},
                {"value": "100-", "label": "100万元以上"}
            ]

            age_ranges = [
                {"value": "0-1", "label": "1年以内"},
                {"value": "1-3", "label": "1-3年"},
                {"value": "3-5", "label": "3-5年"},
                {"value": "5-7", "label": "5-7年"},
                {"value": "7-10", "label": "7-10年"},
                {"value": "10-", "label": "10年以上"}
            ]

            mileage_ranges = [
                {"value": "0-1", "label": "1万公里以内"},
                {"value": "1-3", "label": "1-3万公里"},
                {"value": "3-6", "label": "3-6万公里"},
                {"value": "6-10", "label": "6-10万公里"},
                {"value": "10-15", "label": "10-15万公里"},
                {"value": "15-", "label": "15万公里以上"}
            ]

            fuel_types = [
                {"id": 1, "name": "汽油", "label": "Бензин"},
                {"id": 2, "name": "柴油", "label": "Дизель"},
                {"id": 3, "name": "电动", "label": "Электро"},
                {"id": 4, "name": "油电混合", "label": "Гибрид"},
                {"id": 5, "name": "插电式混合", "label": "Плагин-гибрид"}
            ]

            transmissions = [
                {"value": "manual", "label": "手动"},
                {"value": "automatic", "label": "自动"},
                {"value": "amt", "label": "手自一体"},
                {"value": "dct", "label": "双离合"},
                {"value": "cvt", "label": "无级变速"}
            ]

            displacements = [
                {"value": "0-1.0", "label": "1.0L以下"},
                {"value": "1.0-1.6", "label": "1.0-1.6L"},
                {"value": "1.6-2.0", "label": "1.6-2.0L"},
                {"value": "2.0-2.5", "label": "2.0-2.5L"},
                {"value": "2.5-3.0", "label": "2.5-3.0L"},
                {"value": "3.0-4.0", "label": "3.0-4.0L"},
                {"value": "4.0-", "label": "4.0L以上"}
            ]

            return Che168FiltersResponse(
                brands=brands,
                price_ranges=price_ranges,
                age_ranges=age_ranges,
                mileage_ranges=mileage_ranges,
                fuel_types=fuel_types,
                transmissions=transmissions,
                displacements=displacements,
                success=True
            )

        except Exception as e:
            logger.error(f"Failed to create filters response: {e}")
            return Che168FiltersResponse(success=False)

    def parse_translation_response(self, json_data: Dict) -> TranslationResponse:
        """
        Parse translation API response

        Args:
            json_data: Raw JSON response from translation API

        Returns:
            TranslationResponse with parsed translation data
        """
        try:
            return TranslationResponse(
                original_text=json_data.get("originalText", ""),
                translated_text=json_data.get("translatedText", ""),
                source_language=json_data.get("sourceLanguage", "zh-cn"),
                target_language=json_data.get("targetLanguage", "ru"),
                type=json_data.get("type", "analysis"),
                is_static=json_data.get("isStatic", False),
                is_cached=json_data.get("isCached", False),
                success=json_data.get("success", False),
            )
        except Exception as e:
            logger.error(f"Failed to parse translation response: {e}")
            return TranslationResponse(
                original_text="",
                translated_text="",
                source_language="zh-cn",
                target_language="ru",
                type="analysis",
                success=False,
            )


# =============================================================================
# LEGACY BRAVOMOTORS PARSER (DEPRECATED - Use Che168Parser instead)
# =============================================================================


class BravoMotorsParser(Che168Parser):
    """
    Legacy BravoMotors parser - deprecated, use Che168Parser instead
    This class exists for backward compatibility only
    """

    def __init__(self):
        super().__init__()
        logger.warning("BravoMotorsParser is deprecated. Use Che168Parser instead.")