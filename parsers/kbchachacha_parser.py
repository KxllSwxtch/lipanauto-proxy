"""
KBChaChaCha Parser
Handles HTML and JSON parsing for Korean car marketplace
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from schemas.kbchachacha import (
    KBMaker,
    KBCarModel,
    KBGeneration,
    KBConfiguration,
    KBTrim,
    KBCarListing,
)

logger = logging.getLogger(__name__)


class KBChaChaParser:
    """
    Comprehensive parser for KBChaChaCha website
    Handles both JSON API responses and HTML page parsing
    """

    def __init__(self):
        self.base_url = "https://www.kbchachacha.com"
        self.parser_name = "lxml"

    def parse_manufacturers_json(self, json_data: Dict) -> Dict[str, Any]:
        """
        Parse manufacturers JSON response

        Args:
            json_data: Raw JSON response from /carMaker.json

        Returns:
            Dict with parsed manufacturers data
        """
        try:
            if json_data.get("status") != 200:
                return {
                    "success": False,
                    "error": f"API returned status {json_data.get('status')}",
                    "meta": {"parser": "kbchachacha_manufacturers"},
                }

            result = json_data.get("result", {})
            domestic_makers = []
            imported_makers = []

            # Parse domestic manufacturers (국산)
            if "국산" in result:
                for maker_data in result["국산"]:
                    domestic_makers.append(KBMaker(**maker_data))

            # Parse imported manufacturers (수입)
            if "수입" in result:
                for maker_data in result["수입"]:
                    imported_makers.append(KBMaker(**maker_data))

            return {
                "success": True,
                "domestic": domestic_makers,
                "imported": imported_makers,
                "total_count": len(domestic_makers) + len(imported_makers),
                "meta": {
                    "parser": "kbchachacha_manufacturers",
                    "domestic_count": len(domestic_makers),
                    "imported_count": len(imported_makers),
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse manufacturers JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_manufacturers"},
            }

    def parse_models_json(self, json_data: Dict) -> Dict[str, Any]:
        """
        Parse car models JSON response (extract from "code" array)

        Args:
            json_data: Raw JSON response from /carClass.json

        Returns:
            Dict with parsed models data
        """
        try:
            if json_data.get("status") != 200:
                return {
                    "success": False,
                    "error": f"API returned status {json_data.get('status')}",
                    "meta": {"parser": "kbchachacha_models"},
                }

            result = json_data.get("result", {})
            code_array = result.get("code", [])

            models = []
            for model_data in code_array:
                models.append(KBCarModel(**model_data))

            return {
                "success": True,
                "models": models,
                "total_count": len(models),
                "meta": {"parser": "kbchachacha_models", "source_array": "code"},
            }

        except Exception as e:
            logger.error(f"Failed to parse models JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_models"},
            }

    def parse_generations_json(self, json_data: Dict) -> Dict[str, Any]:
        """
        Parse car generations JSON response

        Args:
            json_data: Raw JSON response from carModel.json

        Returns:
            Dict with parsed generations data
        """
        try:
            if json_data.get("status") != 200:
                return {
                    "success": False,
                    "error": f"API returned status {json_data.get('status')}",
                    "meta": {"parser": "kbchachacha_generations"},
                }

            result = json_data.get("result", {})
            generations = []

            # Parse generations from codeModel array
            if "codeModel" in result:
                for model_data in result["codeModel"]:
                    # Extract model year range from modelName if available
                    model_year = None
                    if "modelName" in model_data:
                        # Look for year patterns like "2.5 가솔린 2WD" -> extract engine info as year context
                        model_year = model_data["modelName"]

                    generations.append(
                        KBGeneration(
                            modelCode=model_data.get("modelCode", ""),
                            modelName=model_data.get("modelName", ""),
                            modelYear=model_year,
                            count=0,  # Count not available in this structure
                        )
                    )

            return {
                "success": True,
                "generations": generations,
                "total_count": len(generations),
                "meta": {
                    "parser": "kbchachacha_generations",
                    "source": "codeModel array",
                    "note": "Parsed from carModel.json response with carCode parameter",
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse generations JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_generations"},
            }

    def parse_configs_trims_json(self, json_data: Dict) -> Dict[str, Any]:
        """
        Parse configurations and trims JSON response

        Args:
            json_data: Raw JSON response from carGrade.json

        Returns:
            Dict with parsed configurations and trims
        """
        try:
            if json_data.get("status") != 200:
                return {
                    "success": False,
                    "error": f"API returned status {json_data.get('status')}",
                    "meta": {"parser": "kbchachacha_configs_trims"},
                }

            result = json_data.get("result", {})
            configurations = []
            trims = []

            # Parse configurations (codeModel)
            if "codeModel" in result:
                for config_data in result["codeModel"]:
                    configurations.append(
                        KBConfiguration(
                            codeModel=config_data.get("modelCode", ""),
                            nameModel=config_data.get("modelName", ""),
                            count=0,  # Count not available in API response
                        )
                    )

            # Parse trims/grades (codeGrade)
            if "codeGrade" in result:
                for trim_data in result["codeGrade"]:
                    trims.append(
                        KBTrim(
                            codeGrade=trim_data.get("gradeCode", ""),
                            nameGrade=trim_data.get("gradeName", ""),
                            count=0,  # Count not available in API response
                        )
                    )

            return {
                "success": True,
                "configurations": configurations,
                "trims": trims,
                "meta": {
                    "parser": "kbchachacha_configs_trims",
                    "configurations_count": len(configurations),
                    "trims_count": len(trims),
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse configs/trims JSON: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_configs_trims"},
            }

    def parse_car_listings_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parse car listings from HTML response

        Args:
            html_content: Raw HTML from search results or default list

        Returns:
            Dict with parsed car listings
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            # Extract different types of listings
            star_pick_listings = self._parse_star_pick_section(soup)
            certified_listings = self._parse_certified_section(soup)

            all_listings = star_pick_listings + certified_listings

            return {
                "success": True,
                "star_pick_listings": star_pick_listings,
                "certified_listings": certified_listings,
                "total_count": len(all_listings),
                "star_pick_count": len(star_pick_listings),
                "certified_count": len(certified_listings),
                "meta": {
                    "parser": "kbchachacha_listings",
                    "response_size": len(html_content),
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse car listings HTML: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_listings"},
            }

    def _parse_star_pick_section(self, soup: BeautifulSoup) -> List[KBCarListing]:
        """Parse KB Star Pick section"""
        star_pick_listings = []

        # Find KB Star Pick section
        star_pick_section = soup.find("h2", string=re.compile(r"KB스타픽"))
        if star_pick_section:
            section_container = star_pick_section.find_parent(
                "div", class_="csTitleArea"
            ).find_next_sibling("div")
            if section_container:
                car_areas = section_container.find_all(
                    "div", class_="area", attrs={"data-car-seq": True}
                )
                for area in car_areas:
                    listing = self._parse_single_car_listing(area)
                    if listing:
                        star_pick_listings.append(listing)

        return star_pick_listings

    def _parse_certified_section(self, soup: BeautifulSoup) -> List[KBCarListing]:
        """Parse certified/diagnosed section"""
        certified_listings = []

        # Find certified section
        certified_section = soup.find("h2", string=re.compile(r"인증 및 진단"))
        if certified_section:
            section_container = certified_section.find_parent(
                "div", class_="csTitleArea"
            ).find_next_sibling("div")
            if section_container:
                car_areas = section_container.find_all(
                    "div", class_="area", attrs={"data-car-seq": True}
                )
                for area in car_areas:
                    listing = self._parse_single_car_listing(area)
                    if listing:
                        certified_listings.append(listing)

        return certified_listings

    def _parse_single_car_listing(self, area_element) -> Optional[KBCarListing]:
        """Parse individual car listing from area element"""
        try:
            # Extract car sequence ID
            car_seq = area_element.get("data-car-seq")
            if not car_seq:
                return None

            # Extract badge (인증, 진단, etc.)
            badges = []
            badge_element = area_element.find("span", class_="check-bedge")
            if badge_element:
                badge_text = badge_element.find("span", class_="txt")
                if badge_text:
                    badges.append(badge_text.get_text(strip=True))

            # Extract images
            images = []
            img_elements = area_element.find_all("img")
            for img in img_elements:
                src = img.get("src")
                if src and "noimage" not in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = urljoin(self.base_url, src)
                    images.append(src)

            # Extract thumbnail info
            thumbnail_info = None
            thumbnail_bottom = area_element.find("div", class_="thumbnail-bottom")
            if thumbnail_bottom:
                thumbnail_info = thumbnail_bottom.get_text(strip=True)

            # Extract main car information
            title_element = area_element.find("strong", class_="tit")
            if not title_element:
                return None

            title = title_element.get_text(strip=True)

            # Extract data line (year, mileage, location)
            data_line_element = area_element.find("div", class_="data-line")
            year, mileage, location = None, None, None
            if data_line_element:
                spans = data_line_element.find_all("span")
                if len(spans) >= 1:
                    year = spans[0].get_text(strip=True)
                if len(spans) >= 2:
                    mileage = spans[1].get_text(strip=True)
                if len(spans) >= 3:
                    location = spans[2].get_text(strip=True)

            # Extract tags
            tags = []
            tag_elements = area_element.find_all("span", class_="tag")
            for tag_elem in tag_elements:
                tags.append(tag_elem.get_text(strip=True))

            # Extract price
            price_element = area_element.find("span", class_="price")
            price = 0
            price_text = ""
            if price_element:
                price_text = price_element.get_text(strip=True)
                # Extract numeric price
                price_match = re.search(r"(\d+(?:,\d+)?)", price_text.replace(",", ""))
                if price_match:
                    price = int(price_match.group(1))

            # Extract detail URL
            link_element = area_element.find("a", href=True)
            url = ""
            if link_element:
                href = link_element.get("href")
                if href.startswith("/"):
                    url = urljoin(self.base_url, href)
                else:
                    url = href

            # Parse title to extract maker and model
            maker, model = self._parse_title_for_maker_model(title)

            return KBCarListing(
                carSeq=car_seq,
                title=title,
                maker=maker,
                model=model,
                year=year,
                mileage=mileage,
                location=location,
                price=price,
                price_text=price_text,
                images=images,
                tags=tags,
                badges=badges,
                url=url,
                thumbnail_info=thumbnail_info,
            )

        except Exception as e:
            logger.warning(f"Failed to parse single car listing: {str(e)}")
            return None

    def _parse_title_for_maker_model(self, title: str) -> Tuple[str, str]:
        """Extract maker and model from car title"""
        try:
            # Common Korean car makers
            makers = [
                "현대",
                "기아",
                "대우",
                "쌍용",
                "르노삼성",
                "벤츠",
                "BMW",
                "아우디",
                "폭스바겐",
                "렉서스",
                "토요타",
                "닛산",
                "혼다",
                "마쯔다",
            ]

            for maker in makers:
                if title.startswith(maker):
                    # Extract model (everything after maker until parentheses or specific keywords)
                    model_part = title[len(maker) :].strip()
                    model_match = re.match(r"^([^(]+)", model_part)
                    if model_match:
                        model = model_match.group(1).strip()
                        return maker, model

            # Fallback: split by first space
            parts = title.split(" ", 1)
            if len(parts) >= 2:
                return parts[0], parts[1]

            return title, ""

        except Exception:
            return title, ""

    def parse_search_results_html(
        self, html_content: str, page: int = 1
    ) -> Dict[str, Any]:
        """
        Parse search results from filtered list

        Args:
            html_content: HTML response from search
            page: Current page number

        Returns:
            Dict with search results
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            # Find all car listings in search results
            car_areas = soup.find_all(
                "div", class_="area", attrs={"data-car-seq": True}
            )
            listings = []

            for area in car_areas:
                listing = self._parse_single_car_listing(area)
                if listing:
                    listings.append(listing)

            # Check if there are more pages (look for pagination or "load more")
            has_next_page = self._has_next_page(soup)

            return {
                "success": True,
                "listings": listings,
                "total_count": len(listings),
                "page": page,
                "has_next_page": has_next_page,
                "meta": {
                    "parser": "kbchachacha_search",
                    "response_size": len(html_content),
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse search results HTML: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_search"},
            }

    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there are more pages available"""
        try:
            # Look for pagination indicators
            pagination = soup.find("div", class_=re.compile(r"pagination|paging"))
            if pagination:
                next_btn = pagination.find("a", string=re.compile(r"다음|next|>"))
                return next_btn is not None

            # Look for "load more" button
            load_more = soup.find("button", string=re.compile(r"더보기|load.*more"))
            return load_more is not None

        except Exception:
            return False
