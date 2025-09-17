"""
BravoMotors Parser
Handles JSON parsing for Chinese car marketplace API responses via bravomotors.com
"""

import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from schemas.bravomotors import (
    BravoMotorsSearchResponse,
    BravoMotorsCarListing,
    BravoMotorsCarDetail,
    BravoMotorsCarDetailResponse,
    BravoMotorsFiltersResponse,
    TranslationResponse,
)

logger = logging.getLogger(__name__)


class BravoMotorsParser:
    """
    Comprehensive parser for BravoMotors API responses
    Handles JSON parsing and data transformation for Chinese car data
    """

    def __init__(self):
        self.base_url = "https://bravomotorrs.com"
        self.parser_name = "bravomotors_json"

    def parse_car_search_response(self, json_data: Dict) -> BravoMotorsSearchResponse:
        """
        Parse car search API response from BravoMotors

        Args:
            json_data: Raw JSON response from API

        Returns:
            BravoMotorsSearchResponse with parsed data
        """
        try:
            # Check response status
            if json_data.get("returncode") != 0:
                return BravoMotorsSearchResponse(
                    success=False,
                    cars=[],
                    total_count=0,
                    meta={
                        "parser": self.parser_name,
                        "error": f"API returned code {json_data.get('returncode')}: {json_data.get('message', 'Unknown error')}",
                    },
                )

            result = json_data.get("result", [])
            car_listings = []

            # Parse each car entry
            for item in result:
                try:
                    car_data = self._parse_car_item(item)
                    if car_data:
                        car_listings.append(car_data)
                except Exception as e:
                    logger.warning(f"Failed to parse car item: {str(e)}")
                    continue

            return BravoMotorsSearchResponse(
                success=True,
                cars=car_listings,
                total_count=len(car_listings),
                page=1,
                per_page=len(car_listings),
                total_pages=1,
                meta={
                    "parser": self.parser_name,
                    "source": "bravomotors_api",
                },
            )

        except Exception as e:
            logger.error(f"Failed to parse BravoMotors search response: {str(e)}")
            return BravoMotorsSearchResponse(
                success=False,
                cars=[],
                total_count=0,
                meta={
                    "parser": self.parser_name,
                    "error": str(e),
                },
            )

    def _parse_car_item(self, item: Dict) -> Optional[BravoMotorsCarListing]:
        """
        Parse individual car item from the API response

        Args:
            item: Dictionary containing car data section

        Returns:
            BravoMotorsCarListing or None if parsing fails
        """
        try:
            # Handle the nested structure from the API response
            title_section = item.get("title", "")
            data_section = item.get("data", [])

            if not data_section:
                return None

            # Extract car basic information
            car_info = {}
            for data_item in data_section:
                name = data_item.get("name", "")
                content = data_item.get("content", "")
                car_info[name] = content

            # Extract key fields
            car_title = car_info.get("车型名称", title_section)
            if not car_title:
                return None

            # Generate unique ID from title
            car_id = f"bm_{hash(car_title)}"

            # Parse price
            price_str = car_info.get("厂商指导价(元)", "0")
            price = self._parse_price(price_str)

            # Parse year from registration date or model name
            year = self._parse_year(
                car_info.get("首次上牌时间", ""),
                car_info.get("上市时间", ""),
                car_title
            )

            # Parse engine info
            engine_info = car_info.get("发动机", "")
            engine_volume = self._parse_engine_volume(engine_info, car_info.get("排量(L)", ""))

            # Parse other specifications
            transmission = car_info.get("变速箱", "")
            fuel_type = car_info.get("能源类型", car_info.get("燃料形式", ""))
            drivetrain = car_info.get("驱动方式", "")

            # Extract manufacturer and model from title
            manufacturer, model = self._parse_manufacturer_model(car_title)

            return BravoMotorsCarListing(
                id=car_id,
                title=car_title,
                price=price,
                currency="CNY",
                year=year,
                manufacturer=manufacturer,
                model=model,
                engine_volume=engine_volume,
                fuel_type=fuel_type,
                transmission=transmission,
                drivetrain=drivetrain,
                source_platform="bravomotors",
            )

        except Exception as e:
            logger.warning(f"Failed to parse car item: {str(e)}")
            return None

    def parse_car_detail_response(self, json_data: Dict) -> BravoMotorsCarDetailResponse:
        """
        Parse detailed car information response

        Args:
            json_data: Raw JSON response for car details

        Returns:
            BravoMotorsCarDetailResponse with parsed details
        """
        try:
            if json_data.get("returncode") != 0:
                return BravoMotorsCarDetailResponse(
                    success=False,
                    meta={
                        "parser": self.parser_name,
                        "error": f"API returned code {json_data.get('returncode')}",
                    },
                )

            result = json_data.get("result", [])

            # Organize data by sections
            car_sections = {}
            for section in result:
                title = section.get("title", "")
                data = section.get("data", [])
                car_sections[title] = {item.get("name"): item.get("content") for item in data}

            car_detail = BravoMotorsCarDetail(
                id=f"bm_detail_{hash(str(json_data))}",
                basic_info=car_sections.get("基本参数", {}),
                specifications={
                    "engine": car_sections.get("发动机", {}),
                    "transmission": car_sections.get("变速箱", {}),
                    "chassis": car_sections.get("底盘转向", {}),
                    "body": car_sections.get("车身", {}),
                    "wheels": car_sections.get("车轮制动", {}),
                },
                condition_info=car_sections.get("牌照信息", {}),
                features=[],  # Features would need additional parsing
            )

            return BravoMotorsCarDetailResponse(
                success=True,
                car=car_detail,
                meta={
                    "parser": self.parser_name,
                    "sections_found": len(car_sections),
                },
            )

        except Exception as e:
            logger.error(f"Failed to parse car detail response: {str(e)}")
            return BravoMotorsCarDetailResponse(
                success=False,
                meta={
                    "parser": self.parser_name,
                    "error": str(e),
                },
            )

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
                target_language=json_data.get("targetLanguage", "en"),
                type=json_data.get("type", "analysis"),
                is_static=json_data.get("isStatic", False),
                is_cached=json_data.get("isCached", False),
                success=json_data.get("success", False),
            )
        except Exception as e:
            logger.error(f"Failed to parse translation response: {str(e)}")
            return TranslationResponse(
                original_text="",
                translated_text="",
                source_language="zh-cn",
                target_language="en",
                type="analysis",
                success=False,
            )

    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price from Chinese price string"""
        try:
            if not price_str or price_str == "-":
                return None

            # Remove Chinese characters and extract number
            price_clean = price_str.replace("万", "").replace("元", "").strip()
            if price_clean:
                # Convert 万 (10,000) to actual number
                price_num = float(price_clean)
                if "万" in price_str:
                    price_num *= 10000
                return price_num
            return None
        except (ValueError, TypeError):
            return None

    def _parse_year(self, reg_date: str, launch_date: str, title: str) -> Optional[int]:
        """Parse year from various date formats"""
        try:
            # Try registration date first
            if reg_date and reg_date != "-":
                year = int(reg_date.split("-")[0])
                if 1990 <= year <= 2030:
                    return year

            # Try launch date
            if launch_date and launch_date != "-":
                year_str = launch_date.replace(".", "").strip()
                if len(year_str) >= 4:
                    year = int(year_str[:4])
                    if 1990 <= year <= 2030:
                        return year

            # Try to extract from title
            import re
            year_match = re.search(r'(20\d{2})', title)
            if year_match:
                return int(year_match.group(1))

            return None
        except (ValueError, TypeError):
            return None

    def _parse_engine_volume(self, engine_str: str, displacement_str: str) -> Optional[float]:
        """Parse engine volume from engine description"""
        try:
            # First try displacement string
            if displacement_str and displacement_str != "-":
                return float(displacement_str)

            # Parse from engine string (e.g., "2.0T 258马力 L4")
            if engine_str and engine_str != "-":
                import re
                volume_match = re.search(r'(\d+\.\d+)', engine_str)
                if volume_match:
                    return float(volume_match.group(1))

            return None
        except (ValueError, TypeError):
            return None

    def _parse_manufacturer_model(self, title: str) -> tuple[Optional[str], Optional[str]]:
        """Parse manufacturer and model from car title"""
        try:
            # Common Chinese car brand mappings
            brand_mapping = {
                "奔驰": "Mercedes-Benz",
                "宝马": "BMW",
                "奥迪": "Audi",
                "大众": "Volkswagen",
                "丰田": "Toyota",
                "本田": "Honda",
                "日产": "Nissan",
                "马自达": "Mazda",
                "雷克萨斯": "Lexus",
                "英菲尼迪": "Infiniti",
            }

            for chinese_brand, english_brand in brand_mapping.items():
                if title.startswith(chinese_brand):
                    # Extract model from remaining text
                    model_part = title[len(chinese_brand):].strip()
                    model = model_part.split()[0] if model_part else None
                    return english_brand, model

            # If no known brand found, try to split the first two parts
            parts = title.split()
            if len(parts) >= 2:
                return parts[0], parts[1]
            elif len(parts) == 1:
                return parts[0], None

            return None, None
        except Exception:
            return None, None