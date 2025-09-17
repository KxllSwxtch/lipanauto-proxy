"""
BravoMotors Service
Business logic layer for Chinese car marketplace integration via bravomotors.com
"""

import json
import logging
import time
import random
import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import requests
from requests.exceptions import RequestException, Timeout

from parsers.bravomotors_parser import BravoMotorsParser
from schemas.bravomotors import (
    BravoMotorsSearchResponse,
    BravoMotorsCarDetailResponse,
    BravoMotorsFiltersResponse,
    BravoMotorsSearchFilters,
    TranslationRequest,
    TranslationResponse,
)

logger = logging.getLogger(__name__)


class BravoMotorsService:
    """
    BravoMotors service for Chinese car marketplace integration

    Provides comprehensive functionality for:
    - Car search with filters and pagination
    - Individual car detail retrieval
    - Translation services for Chinese content
    - Session management with Chinese site requirements
    """

    def __init__(self, proxy_client=None):
        self.proxy_client = proxy_client
        self.parser = BravoMotorsParser()

        # BravoMotors API endpoints
        self.car_api_url = "https://bravomotorrs.com/api/proxy"
        self.translation_api_url = "https://tr.habsidev.com/api/v1/translate"

        # Session management
        self.session = requests.Session()

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        # Setup session
        self._setup_session()

    def _setup_session(self):
        """Setup session with Chinese site requirements"""
        # Headers from the bravomotors cars.py example
        self.session.headers.update({
            'sec-ch-ua-platform': '"macOS"',
            'Referer': 'https://bravomotorrs.com/catalog/cn',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
        })

        # Session configuration
        self.session.timeout = (10, 30)  # connect, read timeout
        self.session.max_redirects = 3

        # Translation headers
        self.translation_headers = {
            'accept': '*/*',
            'accept-language': 'en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5',
            'authorization': 'Bearer encar-translations-2024-secret-key',
            'content-type': 'application/json',
            'origin': 'https://bravomotorrs.com',
            'priority': 'u=1, i',
            'referer': 'https://bravomotorrs.com/',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }

    def _rate_limit(self):
        """Rate limiting to avoid being blocked"""
        current_time = time.time()
        if current_time - self.last_request_time < 1.0:  # 1 second between requests
            time.sleep(1.0 - (current_time - self.last_request_time))

        self.last_request_time = time.time()
        self.request_count += 1

        # Add random delay occasionally
        if self.request_count % 10 == 0:
            time.sleep(random.uniform(1.0, 2.0))

    async def search_cars(self, filters: BravoMotorsSearchFilters = None) -> BravoMotorsSearchResponse:
        """
        Search cars using BravoMotors API

        Args:
            filters: Search filters for cars

        Returns:
            BravoMotorsSearchResponse with search results
        """
        try:
            self._rate_limit()

            # Build API URL (using the example from cars.py)
            api_url = "https://bravomotorrs.com/api/proxy?url=https%3A%2F%2Fapiuscdt.che168.com%2Fapi%2Fv1%2Fcar%2Fgetparamtypeitems%3Finfoid%3D55885320%26_appid%3D2sc.m&origin=https%3A%2F%2Fm.che168.com&media_type=application/json"

            logger.info(f"Searching BravoMotors cars with URL: {api_url}")

            # Make request
            response = self.session.get(api_url)
            response.raise_for_status()

            # Parse JSON response
            json_data = response.json()
            logger.info(f"BravoMotors API response status: {json_data.get('returncode', 'unknown')}")

            # Parse using our parser
            search_response = self.parser.parse_car_search_response(json_data)

            # Apply translation if cars found
            if search_response.success and search_response.cars:
                search_response.cars = await self._translate_car_listings(search_response.cars)

            return search_response

        except RequestException as e:
            logger.error(f"BravoMotors API request failed: {str(e)}")
            return BravoMotorsSearchResponse(
                success=False,
                cars=[],
                total_count=0,
                meta={"error": f"API request failed: {str(e)}"},
            )

        except Exception as e:
            logger.error(f"BravoMotors search failed: {str(e)}")
            return BravoMotorsSearchResponse(
                success=False,
                cars=[],
                total_count=0,
                meta={"error": f"Search failed: {str(e)}"},
            )

    async def get_car_details(self, car_id: str) -> BravoMotorsCarDetailResponse:
        """
        Get detailed information for a specific car

        Args:
            car_id: Unique car identifier

        Returns:
            BravoMotorsCarDetailResponse with car details
        """
        try:
            self._rate_limit()

            # For this example, we'll use the same endpoint as search
            # In a real implementation, you'd have a specific detail endpoint
            api_url = "https://bravomotorrs.com/api/proxy?url=https%3A%2F%2Fapiuscdt.che168.com%2Fapi%2Fv1%2Fcar%2Fgetparamtypeitems%3Finfoid%3D55885320%26_appid%3D2sc.m&origin=https%3A%2F%2Fm.che168.com&media_type=application/json"

            response = self.session.get(api_url)
            response.raise_for_status()

            json_data = response.json()
            detail_response = self.parser.parse_car_detail_response(json_data)

            # Apply translation to details
            if detail_response.success and detail_response.car:
                detail_response.translated_data = await self._translate_car_details(detail_response.car)

            return detail_response

        except Exception as e:
            logger.error(f"BravoMotors car detail fetch failed: {str(e)}")
            return BravoMotorsCarDetailResponse(
                success=False,
                meta={"error": f"Detail fetch failed: {str(e)}"},
            )

    async def translate_text(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate Chinese text to target language

        Args:
            request: Translation request with text and language settings

        Returns:
            TranslationResponse with translated text
        """
        try:
            self._rate_limit()

            # Prepare translation request
            json_data = {
                'text': request.text,
                'targetLanguage': request.target_language,
                'sourceLanguage': request.source_language,
                'type': request.type,
            }

            logger.info(f"Translating text: {request.text[:50]}...")

            # Make translation request
            response = requests.post(
                self.translation_api_url,
                headers=self.translation_headers,
                json=json_data
            )
            response.raise_for_status()

            translation_data = response.json()
            return self.parser.parse_translation_response(translation_data)

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return TranslationResponse(
                original_text=request.text,
                translated_text=request.text,  # Fallback to original
                source_language=request.source_language,
                target_language=request.target_language,
                type=request.type,
                success=False,
            )

    async def get_available_filters(self) -> BravoMotorsFiltersResponse:
        """
        Get available filter options for search

        Returns:
            BravoMotorsFiltersResponse with filter options
        """
        try:
            # For this example, return predefined filters
            # In a real implementation, these might come from a separate API
            return BravoMotorsFiltersResponse(
                manufacturers=[
                    {"name": "Mercedes-Benz", "name_chinese": "奔驰"},
                    {"name": "BMW", "name_chinese": "宝马"},
                    {"name": "Audi", "name_chinese": "奥迪"},
                    {"name": "Volkswagen", "name_chinese": "大众"},
                    {"name": "Toyota", "name_chinese": "丰田"},
                    {"name": "Honda", "name_chinese": "本田"},
                    {"name": "Nissan", "name_chinese": "日产"},
                ],
                years=list(range(2010, 2025)),
                fuel_types=["汽油", "柴油", "电动", "混合动力"],
                transmissions=["手动", "自动", "无级变速"],
                locations=["北京", "上海", "广州", "深圳", "杭州"],
                price_ranges=[
                    {"min": 0, "max": 100000},
                    {"min": 100000, "max": 300000},
                    {"min": 300000, "max": 500000},
                    {"min": 500000, "max": 1000000},
                    {"min": 1000000, "max": float('inf')},
                ],
            )

        except Exception as e:
            logger.error(f"Failed to get filters: {str(e)}")
            return BravoMotorsFiltersResponse()

    async def _translate_car_listings(self, cars: List) -> List:
        """Translate car listing titles"""
        translated_cars = []

        for car in cars:
            try:
                if car.title and not car.title_translated:
                    translation_request = TranslationRequest(
                        text=car.title,
                        target_language="ru",
                        source_language="zh-cn",
                        type="analysis"
                    )

                    translation_response = await self.translate_text(translation_request)

                    if translation_response.success:
                        car.title_translated = translation_response.translated_text
                        logger.info(f"Translated: {car.title} -> {car.title_translated}")

                translated_cars.append(car)

                # Small delay between translations to avoid rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.warning(f"Failed to translate car title: {str(e)}")
                translated_cars.append(car)

        return translated_cars

    async def _translate_car_details(self, car_detail) -> Dict[str, Any]:
        """Translate car detail information"""
        try:
            translated_data = {}

            # Translate basic info
            if car_detail.basic_info:
                translated_basic = {}
                for key, value in car_detail.basic_info.items():
                    if isinstance(value, str) and value.strip():
                        translation_request = TranslationRequest(
                            text=f"{key}: {value}",
                            target_language="ru",
                            source_language="zh-cn",
                            type="analysis"
                        )
                        translation_response = await self.translate_text(translation_request)
                        if translation_response.success:
                            translated_basic[key] = translation_response.translated_text
                        else:
                            translated_basic[key] = f"{key}: {value}"

                        await asyncio.sleep(0.1)  # Rate limiting

                translated_data["basic_info"] = translated_basic

            return translated_data

        except Exception as e:
            logger.warning(f"Failed to translate car details: {str(e)}")
            return {}

