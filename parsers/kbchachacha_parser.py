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
                # Map className to modelName for consistency
                if "className" in model_data and "modelName" not in model_data:
                    model_data["modelName"] = model_data["className"]
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
                            codeModel=model_data.get("modelCode", ""),
                            nameModel=model_data.get("modelName", ""),
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

    def parse_car_detail_html(self, html_content: str, car_seq: str) -> Dict[str, Any]:
        """
        Parse car detail page HTML to extract comprehensive car information

        Args:
            html_content: HTML content from car detail page
            car_seq: Car sequence ID

        Returns:
            Dict with parsed car detail data
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            # Extract JSON-LD structured data
            json_ld_data = self._extract_json_ld_data(soup)

            # Extract technical specifications from table
            specifications = self._extract_specifications_table(soup)

            # Extract pricing information
            pricing = self._extract_pricing_info(soup, json_ld_data)

            # Extract condition and inspection info
            condition = self._extract_condition_info(soup)

            # Extract options
            options = self._extract_options_info(soup)

            # Extract seller information
            seller = self._extract_seller_info(soup)

            # Extract basic info
            basic_info = self._extract_basic_info(soup, json_ld_data)

            # Extract images
            images = self._extract_images(json_ld_data)

            # Extract tags and badges
            tags, badges = self._extract_tags_badges(soup)

            # Extract description
            description = self._extract_description(soup)

            return {
                "success": True,
                "car_seq": car_seq,
                "title": basic_info.get("title", ""),
                "brand": basic_info.get("brand", ""),
                "model": basic_info.get("model", ""),
                "full_name": basic_info.get("full_name", ""),
                "images": images,
                "main_image": images[0] if images else None,
                "specifications": specifications,
                "pricing": pricing,
                "condition": condition,
                "options": options,
                "seller": seller,
                "description": description,
                "tags": tags,
                "badges": badges,
                "detail_url": f"https://www.kbchachacha.com/public/car/detail.kbc?carSeq={car_seq}",
                "meta": {
                    "parser": "kbchachacha_car_detail",
                    "car_seq": car_seq,
                    "extracted_sections": [
                        "json_ld",
                        "specifications",
                        "pricing",
                        "condition",
                        "options",
                        "seller",
                        "images",
                        "description",
                    ],
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse car detail HTML: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "kbchachacha_car_detail", "car_seq": car_seq},
            }

    def _extract_json_ld_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract JSON-LD structured data from script tag"""
        try:
            json_ld_script = soup.find("script", {"type": "application/ld+json"})
            if json_ld_script:
                return json.loads(json_ld_script.string)
            return {}
        except Exception as e:
            logger.error(f"Failed to extract JSON-LD data: {str(e)}")
            return {}

    def _extract_specifications_table(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract technical specifications from detail-info-table"""
        try:
            specs = {}

            # Find the main specifications table
            spec_table = soup.find("table", class_="detail-info-table")
            if spec_table:
                rows = spec_table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["th", "td"])
                    if len(cells) >= 2:
                        for i in range(0, len(cells), 2):
                            if i + 1 < len(cells):
                                key = cells[i].get_text(strip=True)
                                value = cells[i + 1].get_text(strip=True)

                                # Map Korean headers to English fields
                                if key == "차량번호":
                                    specs["license_plate"] = value
                                elif key == "연식":
                                    specs["model_year"] = value
                                elif key == "주행거리":
                                    specs["mileage"] = value
                                elif key == "연료":
                                    specs["fuel_type"] = value
                                elif key == "변속기":
                                    specs["transmission"] = value
                                elif key == "사용구분":
                                    specs["car_class"] = value
                                elif key == "배기량":
                                    specs["engine_displacement"] = value
                                elif key == "색상":
                                    specs["color"] = value
                                elif key == "연비":
                                    specs["fuel_efficiency"] = value
                                elif key == "구동방식":
                                    specs["drivetrain"] = value
                                elif key == "승차인원":
                                    specs["seating_capacity"] = value

            return specs

        except Exception as e:
            logger.error(f"Failed to extract specifications: {str(e)}")
            return {}

    def _extract_pricing_info(
        self, soup: BeautifulSoup, json_ld_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract pricing information from various sources"""
        try:
            pricing = {}

            # Get price from JSON-LD
            if json_ld_data.get("offers", {}).get("price"):
                pricing["current_price"] = int(json_ld_data["offers"]["price"])

            # Extract formatted price text
            price_elements = soup.find_all(
                ["strong", "span"], string=re.compile(r"\d+만원")
            )
            for element in price_elements:
                price_text = element.get_text(strip=True)
                if "만원" in price_text and "price-sum" not in element.get("class", []):
                    pricing["current_price_text"] = price_text
                    break

            # Extract market price range
            market_price = soup.find("strong", class_="price")
            if market_price:
                pricing["market_price_range"] = market_price.get_text(strip=True)

            # Extract price confidence indicator
            price_confidence = soup.find("div", class_="price-range-bar__current-mark")
            if price_confidence:
                pricing["market_price_confidence"] = "high"  # Based on styling

            return pricing

        except Exception as e:
            logger.error(f"Failed to extract pricing info: {str(e)}")
            return {}

    def _extract_condition_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract car condition and inspection information"""
        try:
            condition = {}

            # Extract mileage analysis
            mileage_analysis = soup.find("div", class_="km-txt")
            if mileage_analysis:
                condition["mileage_analysis"] = mileage_analysis.get_text(strip=True)

            # Extract inspection/diagnosis status
            diag_elements = soup.find_all(
                ["div", "span"], string=re.compile(r"진단|인증|검사")
            )
            for element in diag_elements:
                if "진단" in element.get_text():
                    condition["inspection_status"] = element.get_text(strip=True)
                    break

            return condition

        except Exception as e:
            logger.error(f"Failed to extract condition info: {str(e)}")
            return {}

    def _extract_options_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract car options and features"""
        try:
            options = {
                "safety_options": [],
                "convenience_options": [],
                "exterior_options": [],
                "interior_options": [],
                "multimedia_options": [],
                "other_options": [],
            }

            # Find options section
            options_section = soup.find("div", id="divCarOption")
            if options_section:
                option_elements = options_section.find_all(["li", "span", "div"])
                for element in option_elements:
                    option_text = element.get_text(strip=True)
                    if option_text and len(option_text) > 2:
                        # Categorize options based on keywords
                        if any(
                            keyword in option_text
                            for keyword in ["안전", "에어백", "ABS", "ESP"]
                        ):
                            options["safety_options"].append(option_text)
                        elif any(
                            keyword in option_text
                            for keyword in ["네비", "오디오", "스피커", "USB"]
                        ):
                            options["multimedia_options"].append(option_text)
                        elif any(
                            keyword in option_text
                            for keyword in ["시트", "열선", "가죽", "파워윈도우"]
                        ):
                            options["interior_options"].append(option_text)
                        elif any(
                            keyword in option_text
                            for keyword in ["썬루프", "휠", "램프", "범퍼"]
                        ):
                            options["exterior_options"].append(option_text)
                        elif any(
                            keyword in option_text
                            for keyword in ["하이패스", "블랙박스", "스마트키"]
                        ):
                            options["convenience_options"].append(option_text)
                        else:
                            options["other_options"].append(option_text)

            return options

        except Exception as e:
            logger.error(f"Failed to extract options info: {str(e)}")
            return {
                "safety_options": [],
                "convenience_options": [],
                "exterior_options": [],
                "interior_options": [],
                "multimedia_options": [],
                "other_options": [],
            }

    def _extract_seller_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract seller information"""
        try:
            seller = {}

            # Extract seller description
            seller_desc = soup.find("div", class_="seller-comment")
            if seller_desc:
                seller["seller_description"] = seller_desc.get_text(strip=True)

            # Extract seller location
            location_elements = soup.find_all(
                ["span", "div"],
                string=re.compile(
                    r"인천|서울|부산|대구|대전|광주|울산|경기|강원|충북|충남|전북|전남|경북|경남|제주"
                ),
            )
            for element in location_elements:
                location_text = element.get_text(strip=True)
                if any(
                    city in location_text
                    for city in ["인천", "서울", "부산", "대구", "대전", "광주", "울산"]
                ):
                    seller["location"] = location_text
                    break

            return seller

        except Exception as e:
            logger.error(f"Failed to extract seller info: {str(e)}")
            return {}

    def _extract_basic_info(
        self, soup: BeautifulSoup, json_ld_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract basic car information"""
        try:
            basic_info = {}

            # Extract from JSON-LD
            if json_ld_data:
                basic_info["title"] = json_ld_data.get("name", "")
                basic_info["full_name"] = json_ld_data.get("name", "")
                if json_ld_data.get("brand", {}).get("name"):
                    basic_info["brand"] = json_ld_data["brand"]["name"]

            # Extract from HTML title
            title_element = soup.find("title")
            if title_element:
                title_text = title_element.get_text(strip=True)
                if not basic_info.get("title"):
                    basic_info["title"] = title_text

                # Extract brand and model from title
                if not basic_info.get("brand"):
                    if "현대" in title_text:
                        basic_info["brand"] = "현대"
                    elif "기아" in title_text:
                        basic_info["brand"] = "기아"
                    elif "벤츠" in title_text:
                        basic_info["brand"] = "벤츠"
                    elif "BMW" in title_text:
                        basic_info["brand"] = "BMW"

                # Extract model from title
                if "벨로스터" in title_text:
                    basic_info["model"] = "벨로스터"
                elif "그랜저" in title_text:
                    basic_info["model"] = "그랜저"
                elif "아반떼" in title_text:
                    basic_info["model"] = "아반떼"

            return basic_info

        except Exception as e:
            logger.error(f"Failed to extract basic info: {str(e)}")
            return {}

    def _extract_images(self, json_ld_data: Dict[str, Any]) -> List[str]:
        """Extract car images from JSON-LD data"""
        try:
            images = []

            if json_ld_data.get("image"):
                image_data = json_ld_data["image"]
                if isinstance(image_data, list):
                    images = image_data
                elif isinstance(image_data, str):
                    images = [image_data]

            return images

        except Exception as e:
            logger.error(f"Failed to extract images: {str(e)}")
            return []

    def _extract_tags_badges(self, soup: BeautifulSoup) -> Tuple[List[str], List[str]]:
        """Extract car tags and badges"""
        try:
            tags = []
            badges = []

            # Extract badges (인증, 진단, etc.)
            badge_elements = soup.find_all(
                ["span", "div"], class_=re.compile(r"badge|tag|cert")
            )
            for element in badge_elements:
                badge_text = element.get_text(strip=True)
                if badge_text and len(badge_text) < 10:  # Short badges
                    badges.append(badge_text)

            # Extract tags from specific sections
            tag_elements = soup.find_all(
                ["span", "div"], string=re.compile(r"실차주|헛걸음보상|무사고|저가격")
            )
            for element in tag_elements:
                tag_text = element.get_text(strip=True)
                if tag_text and len(tag_text) < 20:  # Reasonable tag length
                    tags.append(tag_text)

            return tags, badges

        except Exception as e:
            logger.error(f"Failed to extract tags/badges: {str(e)}")
            return [], []

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract car description from seller comments"""
        try:
            # Find seller description section
            desc_elements = soup.find_all(
                ["div", "p"], string=re.compile(r"설명|소개|차량|상태")
            )
            for element in desc_elements:
                parent = element.parent
                if (
                    parent and len(parent.get_text(strip=True)) > 50
                ):  # Substantial description
                    return parent.get_text(strip=True)

            # Fallback to any large text block
            large_text_elements = soup.find_all(
                ["div", "p"], string=lambda text: text and len(text) > 100
            )
            if large_text_elements:
                return large_text_elements[0].get_text(strip=True)

            return ""

        except Exception as e:
            logger.error(f"Failed to extract description: {str(e)}")
            return ""
