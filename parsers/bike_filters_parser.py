"""
Parser for bobaedream.co.kr bike filter API responses
Handles JSON parsing with Korean encoding and filter hierarchy
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from bs4.dammit import UnicodeDammit
from bs4 import BeautifulSoup
from schemas.bike_filters import FilterOption, FilterLevel, FilterValues

logger = logging.getLogger(__name__)


class BikeFiltersParser:
    """
    Parser for bike filter API responses from bobaedream.co.kr
    Handles Korean encoding issues and JSON structure parsing
    """

    def __init__(self):
        self.parser_version = "1.0"
        self.encoding_fallbacks = ["utf-8", "euc-kr", "cp949"]

    def parse_filter_response(
        self, response_text: str, filter_level: int
    ) -> FilterLevel:
        """
        Parse filter response (JSON or HTML)

        Args:
            response_text: Response text (JSON array or HTML)
            filter_level: Filter level depth

        Returns:
            FilterLevel with parsed options
        """
        try:
            if not response_text or response_text.strip() == "":
                logger.warning(f"Empty response for filter level {filter_level}")
                return FilterLevel(
                    success=False,
                    options=[],
                    level=filter_level,
                    meta={"error": "Empty response"},
                )

            # Fix Korean encoding first
            response_text = self._fix_korean_encoding(response_text)

            # Try to parse as JSON first (most common case)
            options = self._parse_json_response(response_text)

            if options:
                logger.info(
                    f"Parsed {len(options)} options from JSON for filter level {filter_level}"
                )
                return FilterLevel(
                    success=True,
                    options=options,
                    level=filter_level,
                    meta={
                        "parser": "bike_filters_parser",
                        "response_length": len(response_text),
                        "options_count": len(options),
                        "data_type": "json",
                    },
                )

            # Fallback to HTML parsing
            clean_text = self._clean_js_response(response_text)
            if clean_text:
                options = self._parse_filter_options(clean_text)

                logger.info(
                    f"Parsed {len(options)} options from HTML for filter level {filter_level}"
                )
                return FilterLevel(
                    success=True,
                    options=options,
                    level=filter_level,
                    meta={
                        "parser": "bike_filters_parser",
                        "response_length": len(response_text),
                        "cleaned_length": len(clean_text),
                        "options_count": len(options),
                        "data_type": "html",
                    },
                )

            logger.warning(f"No valid data found in response for level {filter_level}")
            return FilterLevel(
                success=False,
                options=[],
                level=filter_level,
                meta={"error": "No valid data in response"},
            )

        except Exception as e:
            logger.error(
                f"Error parsing filter response for level {filter_level}: {str(e)}"
            )
            return FilterLevel(
                success=False,
                options=[],
                level=filter_level,
                meta={"error": str(e), "parser": "bike_filters_parser"},
            )

    def _parse_json_response(self, response_text: str) -> List[FilterOption]:
        """
        Parse JSON response from filter API

        Args:
            response_text: JSON response text

        Returns:
            List of FilterOption objects
        """
        try:
            # Clean up the response text
            response_text = response_text.strip()

            # Try to parse as JSON array
            if response_text.startswith("[") and response_text.endswith("]"):
                json_data = json.loads(response_text)
                options = []

                for item in json_data:
                    if isinstance(item, dict):
                        sno = str(item.get("sno", ""))
                        cname = str(item.get("cname", ""))
                        cnt = str(item.get("cnt", "0"))
                        chk = str(item.get("chk", ""))

                        # Skip empty or invalid entries
                        if sno and cname and sno != cname:
                            options.append(
                                FilterOption(sno=sno, cname=cname, cnt=cnt, chk=chk)
                            )

                return options

        except json.JSONDecodeError as e:
            logger.debug(f"JSON parsing failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing JSON response: {str(e)}")

        return []

    def _clean_js_response(self, response_text: str) -> str:
        """Clean JavaScript response to extract data"""
        try:
            # Remove JavaScript wrapper and get content
            # Look for patterns like: document.write('...') or innerHTML = '...'
            patterns = [
                r"document\.write\s*\(\s*['\"](.+?)['\"]\s*\)",
                r"innerHTML\s*=\s*['\"](.+?)['\"]",
                r"['\"](.+?)['\"]",  # Fallback: any quoted content
            ]

            for pattern in patterns:
                matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
                if matches:
                    # Combine all matches
                    combined = "".join(matches)
                    # Unescape HTML entities and clean up
                    combined = combined.replace("\\'", "'").replace('\\"', '"')
                    combined = re.sub(r"\\n", "\n", combined)
                    combined = re.sub(r"\\t", "\t", combined)
                    return combined

            # If no patterns match, try to extract any HTML-like content
            if "<" in response_text and ">" in response_text:
                return response_text

            return ""

        except Exception as e:
            logger.error(f"Error cleaning JS response: {str(e)}")
            return ""

    def _parse_filter_options(self, html_content: str) -> List[FilterOption]:
        """Parse filter options from HTML content"""
        try:
            options = []

            # Try to parse as HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Look for different patterns of filter options
            # Pattern 1: onclick handlers with parameters
            onclick_elements = soup.find_all(attrs={"onclick": True})
            for element in onclick_elements:
                onclick = element.get("onclick", "")
                option = self._extract_option_from_onclick(onclick, element)
                if option:
                    options.append(option)

            # Pattern 2: option elements in select tags
            option_elements = soup.find_all("option")
            for option_elem in option_elements:
                value = option_elem.get("value", "")
                text = option_elem.get_text(strip=True)
                if value and text and value != "":
                    options.append(FilterOption(sno=value, cname=text, cnt="0", chk=""))

            # Pattern 3: Direct text parsing for simple lists
            if not options:
                options = self._parse_text_options(html_content)

            # Remove duplicates
            seen = set()
            unique_options = []
            for option in options:
                key = f"{option.sno}_{option.cname}"
                if key not in seen:
                    seen.add(key)
                    unique_options.append(option)

            return unique_options

        except Exception as e:
            logger.error(f"Error parsing filter options: {str(e)}")
            return []

    def _extract_option_from_onclick(self, onclick: str, element) -> FilterOption:
        """Extract filter option from onclick handler"""
        try:
            # Look for patterns like: onclick="select_option('id', 'name', count)"
            patterns = [
                r"select_option\s*\(\s*['\"](.+?)['\"],\s*['\"](.+?)['\"]",
                r"choose\s*\(\s*['\"](.+?)['\"],\s*['\"](.+?)['\"]",
                r"['\"](\d+)['\"],\s*['\"](.+?)['\"]",
            ]

            for pattern in patterns:
                match = re.search(pattern, onclick)
                if match:
                    groups = match.groups()
                    sno = groups[0]
                    cname = groups[1] if len(groups) > 1 else sno
                    cnt = groups[2] if len(groups) > 2 and groups[2] else "0"

                    return FilterOption(sno=sno, cname=cname, cnt=cnt, chk="")

            # Fallback: extract from element text
            text = element.get_text(strip=True)
            if text:
                # Look for count in parentheses
                count_match = re.search(r"\((\d+)\)", text)
                cnt = count_match.group(1) if count_match else "0"
                clean_text = re.sub(r"\(\d+\)", "", text).strip()

                return FilterOption(sno=clean_text, cname=clean_text, cnt=cnt, chk="")

        except Exception as e:
            logger.error(f"Error extracting option from onclick: {str(e)}")

        return None

    def _parse_text_options(self, text: str) -> List[FilterOption]:
        """Parse options from plain text"""
        try:
            options = []
            lines = text.split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Look for patterns like "name (count)" or just "name"
                match = re.match(r"(.+?)\s*\((\d+)\)", line)
                if match:
                    name = match.group(1).strip()
                    count = match.group(2)
                    options.append(
                        FilterOption(sno=name, cname=name, cnt=count, chk="")
                    )
                elif line:
                    options.append(FilterOption(sno=line, cname=line, cnt="0", chk=""))

            return options

        except Exception as e:
            logger.error(f"Error parsing text options: {str(e)}")
            return []

    def parse_filter_values_from_html(self, html_content: str) -> FilterValues:
        """
        Parse all available filter values from HTML form page

        Args:
            html_content: HTML content of the filter page

        Returns:
            FilterValues with all available options
        """
        try:
            # Handle Korean encoding
            html_content = self._fix_korean_encoding(html_content)
            soup = BeautifulSoup(html_content, "html.parser")

            filter_values = FilterValues()

            # Parse fuel types
            fuel_select = soup.find("select", {"name": "fuel"})
            if fuel_select:
                filter_values.fuel_types = self._parse_select_options(fuel_select)

            # Parse transmission types
            method_select = soup.find("select", {"name": "method"})
            if method_select:
                filter_values.transmission_types = self._parse_select_options(
                    method_select
                )

            # Parse colors
            color_select = soup.find("select", {"name": "car_color"})
            if color_select:
                filter_values.colors = self._parse_select_options(color_select)

            # Parse selling methods
            sell_way_select = soup.find("select", {"name": "sell_way"})
            if sell_way_select:
                filter_values.selling_methods = self._parse_select_options(
                    sell_way_select
                )

            # Parse provinces
            addr_1_select = soup.find("select", {"name": "addr_1"})
            if addr_1_select:
                filter_values.provinces = self._parse_select_options(addr_1_select)

            # Parse engine sizes
            cc_select = soup.find("select", {"name": "cc"})
            if cc_select:
                filter_values.engine_sizes = self._parse_select_options(cc_select)

            # Parse price ranges
            price1_select = soup.find("select", {"name": "price1"})
            if price1_select:
                filter_values.price_ranges = self._parse_select_options(price1_select)

            # Parse mileage ranges
            km_select = soup.find("select", {"name": "km"})
            if km_select:
                filter_values.mileage_ranges = self._parse_select_options(km_select)

            # Parse year ranges
            year_select = soup.find("select", {"name": "buy_year1_1"})
            if year_select:
                filter_values.year_ranges = self._parse_select_options(year_select)

            logger.info("Successfully parsed filter values from HTML")
            return filter_values

        except Exception as e:
            logger.error(f"Error parsing filter values from HTML: {str(e)}")
            return FilterValues()

    def _fix_korean_encoding(self, content: str) -> str:
        """Fix Korean encoding issues in content (HTML or JSON)"""
        try:
            if not isinstance(content, str):
                return content

            # Check if content is JSON
            is_json = content.strip().startswith("[") or content.strip().startswith("{")

            # Method 1: Try to detect and fix mojibake for Korean text
            for encoding in self.encoding_fallbacks:
                try:
                    # Convert string to bytes and back with correct encoding
                    text_bytes = content.encode("latin1")
                    decoded = text_bytes.decode(encoding)

                    # Test if the decoding worked by checking for Korean characters
                    if is_json:
                        # For JSON, try to parse it to validate
                        try:
                            json.loads(decoded)
                            logger.info(
                                f"Successfully fixed JSON encoding with: {encoding}"
                            )
                            return decoded
                        except json.JSONDecodeError:
                            continue
                    else:
                        # For HTML, test if parsing works
                        BeautifulSoup(decoded[:1000], "html.parser")
                        logger.info(
                            f"Successfully fixed HTML encoding with: {encoding}"
                        )
                        return decoded

                except (UnicodeDecodeError, UnicodeEncodeError):
                    continue

            # Method 2: Use UnicodeDammit as fallback
            try:
                from bs4.dammit import UnicodeDammit

                text_bytes = content.encode("latin1")
                dammit = UnicodeDammit(text_bytes, self.encoding_fallbacks)
                if dammit.unicode_markup:
                    logger.info(
                        f"Fixed encoding with UnicodeDammit: {dammit.original_encoding}"
                    )
                    return dammit.unicode_markup
            except Exception:
                pass

            # Method 3: Try direct encoding fixes for common Korean mojibake patterns
            try:
                # Common Korean mojibake patterns
                mojibake_fixes = {
                    "ë": "대",  # 대림
                    "ë¦¼": "림",
                    "í": "혼",  # 혼다
                    "ë¤": "다",
                    "ì¼": "야",  # 야마하
                    "ë§": "마",
                    "í": "하",
                    "ì¤": "스",  # 스즈키
                    "ì¦": "즈",
                    "í": "키",
                }

                fixed_content = content
                for mojibake, correct in mojibake_fixes.items():
                    fixed_content = fixed_content.replace(mojibake, correct)

                if fixed_content != content:
                    logger.info("Applied mojibake fixes for Korean text")
                    return fixed_content

            except Exception:
                pass

            # If all else fails, return original content
            logger.debug("Could not fix encoding, using original content")
            return content

        except Exception as e:
            logger.error(f"Encoding fix failed: {str(e)}")
            return content

    def _parse_select_options(self, select_element) -> List[FilterOption]:
        """Parse options from a select element"""
        try:
            options = []
            option_elements = select_element.find_all("option")

            for option_elem in option_elements:
                value = option_elem.get("value", "")
                text = option_elem.get_text(strip=True)

                # Skip empty options
                if not value or not text or value == "" or text == "선택":
                    continue

                # Extract count if present in text
                count_match = re.search(r"(\d+)", text)
                cnt = count_match.group(1) if count_match else "0"

                options.append(FilterOption(sno=value, cname=text, cnt=cnt, chk=""))

            return options

        except Exception as e:
            logger.error(f"Error parsing select options: {str(e)}")
            return []

    def filter_options_by_availability(
        self, options: List[FilterOption], min_count: int = 1
    ) -> List[FilterOption]:
        """
        Filter options that have available items
        """
        try:
            available_options = []
            for option in options:
                try:
                    count = int(option.cnt)
                    if count >= min_count:
                        available_options.append(option)
                except ValueError:
                    # If count is not a number, include the option
                    available_options.append(option)

            logger.info(
                f"Filtered {len(available_options)} available options from {len(options)} total"
            )
            return available_options

        except Exception as e:
            logger.warning(f"Failed to filter options by availability: {str(e)}")
            return options

    def get_popular_categories(self, categories: List[FilterOption]) -> List[str]:
        """Get popular category IDs based on item count"""
        try:
            # Sort by count (descending) and take top categories
            sorted_categories = sorted(
                categories,
                key=lambda x: int(x.cnt) if x.cnt.isdigit() else 0,
                reverse=True,
            )

            # Return top 5 category IDs
            return [cat.sno for cat in sorted_categories[:5]]

        except Exception as e:
            logger.warning(f"Failed to get popular categories: {str(e)}")
            return []

    def get_popular_manufacturers(self, manufacturers: List[FilterOption]) -> List[str]:
        """Get popular manufacturer IDs based on item count"""
        try:
            # Sort by count (descending) and take top manufacturers
            sorted_manufacturers = sorted(
                manufacturers,
                key=lambda x: int(x.cnt) if x.cnt.isdigit() else 0,
                reverse=True,
            )

            # Return top 8 manufacturer IDs
            return [manu.sno for manu in sorted_manufacturers[:8]]

        except Exception as e:
            logger.warning(f"Failed to get popular manufacturers: {str(e)}")
            return []
