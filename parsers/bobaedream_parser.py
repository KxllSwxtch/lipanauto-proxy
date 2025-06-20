"""
Advanced HTML parser for bobaedream.co.kr bike listings
Uses BeautifulSoup4 with lxml parser for maximum performance
Handles Korean EUC-KR encoding and extracts complete bike data
"""

import re
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from bs4.dammit import UnicodeDammit
from schemas.bikes import BikeItem, BikeSearchResponse, BikeDetail

logger = logging.getLogger(__name__)


class BobaeDreamBikeParser:
    """
    Advanced parser for bobaedream.co.kr bike listings
    Handles complex table structures, Korean text extraction, and encoding issues
    """

    BASE_URL = "https://www.bobaedream.co.kr"

    def __init__(self):
        self.parser_name = "lxml"  # Fastest parser as per BeautifulSoup docs

    def _detect_encoding_and_parse(self, html_content: str) -> BeautifulSoup:
        """
        Detect encoding and parse HTML with proper Korean support
        Uses UnicodeDammit for automatic encoding detection
        """
        try:
            # If it's already a string, try to detect original encoding
            if isinstance(html_content, str):
                # Try to re-encode to detect original encoding
                for encoding in ["euc-kr", "cp949", "utf-8"]:
                    try:
                        # Convert to bytes and back to test encoding
                        html_bytes = html_content.encode("latin1")
                        decoded = html_bytes.decode(encoding)
                        soup = BeautifulSoup(decoded, self.parser_name)
                        logger.info(f"Successfully parsed with encoding: {encoding}")
                        return soup
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        continue

                # Fallback: direct parsing
                soup = BeautifulSoup(html_content, self.parser_name)
                logger.warning("Used fallback parsing without encoding detection")
                return soup
            else:
                # If bytes, use UnicodeDammit
                dammit = UnicodeDammit(html_content, ["euc-kr", "cp949", "utf-8"])
                if dammit.unicode_markup:
                    soup = BeautifulSoup(dammit.unicode_markup, self.parser_name)
                    logger.info(
                        f"Successfully parsed with encoding: {dammit.original_encoding}"
                    )
                    return soup
                else:
                    soup = BeautifulSoup(html_content, self.parser_name)
                    return soup

        except Exception as e:
            logger.error(f"Encoding detection failed: {str(e)}")
            # Final fallback
            soup = BeautifulSoup(html_content, self.parser_name)
            return soup

    def parse_bike_listings(
        self, html_content: str, base_url: str = None
    ) -> BikeSearchResponse:
        """
        Parse bike listings from bobaedream.co.kr list page
        Extracts basic information for each bike listing
        """
        try:
            soup = self._detect_encoding_and_parse(html_content)
            bikes = []

            # NEW APPROACH: Find all links to bike_view.php
            bike_links = soup.find_all("a", href=lambda x: x and "bike_view.php" in x)

            logger.info(f"Parser found {len(bike_links)} bike view links")

            # Deduplicate by bike ID to avoid processing multiple links for same bike
            processed_ids = set()
            unique_links = []

            for link in bike_links:
                href = link.get("href", "")
                bike_id_match = re.search(r"no=(\d+)", href)
                if bike_id_match:
                    bike_id = bike_id_match.group(1)
                    if bike_id not in processed_ids:
                        processed_ids.add(bike_id)
                        unique_links.append(link)

            logger.info(f"After deduplication: {len(unique_links)} unique bikes")

            for link in unique_links:
                try:
                    bike_data = self._extract_bike_from_link(
                        link, base_url or self.BASE_URL
                    )
                    if bike_data:
                        bikes.append(bike_data)
                except Exception as e:
                    logger.warning(f"Failed to parse bike link: {str(e)}")
                    continue

            logger.info(f"Successfully parsed {len(bikes)} bikes")

            # Extract pagination information
            pagination_info = self._extract_pagination_info(soup)

            return BikeSearchResponse(
                success=True,
                bikes=bikes,
                total_count=len(bikes),
                current_page=pagination_info.get("current_page", 1),
                total_pages=pagination_info.get("total_pages"),
                meta={
                    "parser_version": "2.1",
                    "encoding_detected": True,
                    "bike_links_found": len(bike_links),
                    "unique_bikes_found": len(unique_links),
                    "successfully_parsed": len(bikes),
                    "pagination": pagination_info,
                },
            )

        except Exception as e:
            logger.error(f"Failed to parse bike listings: {str(e)}")
            return BikeSearchResponse(
                success=False, bikes=[], meta={"error": str(e), "parser_version": "2.1"}
            )

    def _extract_bike_from_link(self, link: Tag, base_url: str) -> Optional[BikeItem]:
        """Extract bike data from a bike_view link and its surrounding context"""
        try:
            # Extract bike ID and detail URL from href
            href = link.get("href", "")
            bike_id_match = re.search(r"no=(\d+)", href)
            if not bike_id_match:
                # Try alternative patterns
                bike_id_match = re.search(r"bike_view\.php\?.*?(\d+)", href)
                if not bike_id_match:
                    logger.warning(f"Could not extract bike ID from href: {href}")
                    return None

            bike_id = bike_id_match.group(1)

            # Build full detail URL
            if href.startswith("http"):
                detail_url = href
            elif href.startswith("/"):
                detail_url = base_url + href
            else:
                detail_url = base_url + "/" + href

            # Find the parent table row or container
            parent_tr = link.find_parent("tr")
            if not parent_tr:
                # Try to find parent container
                parent_container = link.find_parent(["td", "div"])
                if not parent_container:
                    logger.warning(
                        f"Could not find parent container for bike {bike_id}"
                    )
                    return None
                parent_tr = parent_container.find_parent("tr")
                if not parent_tr:
                    logger.warning(f"Could not find parent TR for bike {bike_id}")
                    return None

            # Extract bike information from the table row
            bike_info = self._extract_bike_info_from_row(parent_tr, link)

            # Extract image URL
            image_url = self._extract_image_url(parent_tr, link)

            # Validate that we have at least a title
            title = bike_info.get("title", "Unknown Model")
            if not title or title == "Unknown Model":
                # Try to extract title from the link href or nearby elements
                alt_title = self._extract_alternative_title(link, parent_tr)
                if alt_title:
                    title = alt_title

            return BikeItem(
                id=bike_id,
                title=title,
                year=bike_info.get("year"),
                mileage=bike_info.get("mileage"),
                engine_cc=bike_info.get("engine_cc"),
                price=bike_info.get("price"),
                seller_type=bike_info.get("seller_type"),
                location=bike_info.get("location"),
                image_url=image_url,
                detail_url=detail_url,
            )

        except Exception as e:
            logger.warning(f"Failed to extract bike from link: {str(e)}")
            return None

    def _extract_alternative_title(self, link: Tag, parent_tr: Tag) -> Optional[str]:
        """Try alternative methods to extract bike title"""
        try:
            # Method 1: Look for alt attribute in nearby images
            images = parent_tr.find_all("img")
            for img in images:
                alt_text = img.get("alt", "").strip()
                if alt_text and len(alt_text) > 3 and "바이크" not in alt_text:
                    return alt_text

            # Method 2: Look for title attribute in the link
            title_attr = link.get("title", "").strip()
            if title_attr and len(title_attr) > 3:
                return title_attr

            # Method 3: Look in the href for model information
            href = link.get("href", "")
            if "model=" in href:
                model_match = re.search(r"model=([^&]+)", href)
                if model_match:
                    return model_match.group(1).replace("%20", " ")

            return None

        except Exception as e:
            logger.warning(f"Failed to extract alternative title: {str(e)}")
            return None

    def _extract_pagination_info(self, soup: BeautifulSoup) -> Dict[str, Optional[int]]:
        """
        Extract pagination information from the page

        Returns:
            Dict with current_page and total_pages information
        """
        try:
            pagination_info = {"current_page": 1, "total_pages": None, "page_links": []}

            # Look for pagination section - usually contains page links
            # Pattern: <b>1</b> | <a href="...page=2">2</a> | ... | <a href="...page=28">28</a>

            # Find all page links
            page_links = soup.find_all("a", href=lambda x: x and "page=" in x)

            if page_links:
                page_numbers = []

                for link in page_links:
                    href = link.get("href", "")
                    page_match = re.search(r"page=(\d+)", href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        page_numbers.append(page_num)
                        pagination_info["page_links"].append(
                            {"page": page_num, "url": href}
                        )

                if page_numbers:
                    # The highest page number is likely the total pages
                    pagination_info["total_pages"] = max(page_numbers)
                    logger.info(f"Found pagination: max page = {max(page_numbers)}")

            # Look for current page indicator (usually marked with <b> tag)
            # Pattern: <b>1</b> indicates current page is 1
            current_page_elements = soup.find_all("b")
            for element in current_page_elements:
                text = element.get_text(strip=True)
                if text.isdigit():
                    # Check if this is in a pagination context
                    parent_text = element.parent.get_text() if element.parent else ""
                    # If it's surrounded by page links, it's likely the current page
                    if "|" in parent_text or "page=" in parent_text:
                        pagination_info["current_page"] = int(text)
                        logger.info(f"Found current page: {text}")
                        break

            # Alternative method: look for pagination table/container
            if not pagination_info["total_pages"]:
                # Look for elements containing multiple page numbers
                for element in soup.find_all(
                    ["td", "div"], string=re.compile(r"\d+.*\d+")
                ):
                    text = element.get_text()
                    # Look for patterns like "1 | 2 | 3 | ... | 28"
                    if "|" in text and "page=" in str(element.parent):
                        numbers = re.findall(r"\b(\d+)\b", text)
                        if numbers:
                            max_page = max(int(n) for n in numbers if int(n) > 0)
                            if max_page > 1:
                                pagination_info["total_pages"] = max_page
                                logger.info(
                                    f"Found total pages via pattern matching: {max_page}"
                                )
                                break

            # Final fallback: estimate based on number of bikes per page
            if (
                not pagination_info["total_pages"]
                and len(pagination_info["page_links"]) > 0
            ):
                # If we have page links but no clear total, use the highest link + some buffer
                max_link_page = max(
                    link["page"] for link in pagination_info["page_links"]
                )
                pagination_info["total_pages"] = max_link_page
                logger.info(f"Estimated total pages from links: {max_link_page}")

            logger.info(f"Pagination info extracted: {pagination_info}")
            return pagination_info

        except Exception as e:
            logger.warning(f"Failed to extract pagination info: {str(e)}")
            return {"current_page": 1, "total_pages": None, "page_links": []}

    def _extract_bike_info_from_row(
        self, row: Tag, link: Tag
    ) -> Dict[str, Optional[str]]:
        """Extract bike information from table row"""
        info = {}

        try:
            # Get all text from the row
            row_text = row.get_text()

            # Get all cells in the row
            cells = row.find_all(["td", "th"])

            # Extract title from link text or nearby text
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) > 2:
                # Clean up the title
                title = link_text.replace("\n", " ").replace("\t", " ").strip()
                # Remove extra spaces
                title = " ".join(title.split())
                if title and title != "Unknown Model":
                    info["title"] = title

            # Try to find title in the same cell as the link
            link_cell = link.find_parent("td")
            if link_cell and not info.get("title"):
                # Get all text nodes from the cell
                cell_text = link_cell.get_text(strip=True)
                if cell_text and len(cell_text) > 3:
                    # Clean up the text
                    title = cell_text.replace("\n", " ").replace("\t", " ").strip()
                    title = " ".join(title.split())
                    if title:
                        info["title"] = title

            # Try to find title in adjacent cells
            if not info.get("title") and link_cell:
                # Check next cell
                next_cell = link_cell.find_next_sibling("td")
                if next_cell:
                    next_text = next_cell.get_text(strip=True)
                    if next_text and len(next_text) > 3 and not next_text.isdigit():
                        info["title"] = next_text

                # Check previous cell
                prev_cell = link_cell.find_previous_sibling("td")
                if prev_cell and not info.get("title"):
                    prev_text = prev_cell.get_text(strip=True)
                    if prev_text and len(prev_text) > 3 and not prev_text.isdigit():
                        info["title"] = prev_text

            # Extract information from all cells in the row
            for i, cell in enumerate(cells):
                cell_text = cell.get_text(strip=True)
                if not cell_text or cell_text == "-":
                    continue

                # Year detection (4-digit year)
                if re.match(r"^(19|20)\d{2}$", cell_text):
                    info["year"] = cell_text

                # Engine CC detection
                if re.search(r"\d+cc", cell_text, re.IGNORECASE):
                    cc_match = re.search(r"(\d+)\s*cc", cell_text, re.IGNORECASE)
                    if cc_match:
                        info["engine_cc"] = cc_match.group(1) + "cc"

                # Price detection (Korean won)
                if "만원" in cell_text or "만" in cell_text:
                    # Extract price patterns
                    price_match = re.search(r"(\d{1,4}(?:,\d{3})*)\s*만원?", cell_text)
                    if price_match:
                        info["price"] = price_match.group(1) + "만원"

                # Mileage detection
                if (
                    "km" in cell_text.lower()
                    or "키로" in cell_text
                    or "킬로" in cell_text
                ):
                    km_match = re.search(r"(\d{1,3}(?:,\d{3})*)", cell_text)
                    if km_match:
                        info["mileage"] = km_match.group(1) + "km"

                # Seller type detection
                if cell_text in ["개인", "업체", "딜러"]:
                    info["seller_type"] = cell_text

                # Location detection (Korean location names)
                if any(
                    region in cell_text
                    for region in [
                        "서울",
                        "부산",
                        "대구",
                        "인천",
                        "광주",
                        "대전",
                        "울산",
                        "세종",
                        "경기",
                        "강원",
                        "충북",
                        "충남",
                        "전북",
                        "전남",
                        "경북",
                        "경남",
                        "제주",
                    ]
                ):
                    info["location"] = cell_text
                elif re.search(r"[가-힣]+시", cell_text) or re.search(
                    r"[가-힣]+구", cell_text
                ):
                    info["location"] = cell_text

            # Additional pattern matching on the full row text
            if not info.get("year"):
                year_match = re.search(r"(20\d{2})", row_text)
                if year_match:
                    info["year"] = year_match.group(1)

            if not info.get("engine_cc"):
                cc_match = re.search(r"(\d+)\s*cc", row_text, re.IGNORECASE)
                if cc_match:
                    info["engine_cc"] = cc_match.group(1) + "cc"

            if not info.get("price"):
                # More flexible price patterns
                price_patterns = [
                    r"(\d{1,4})\s*만원",
                    r"(\d{1,4})\s*만",
                    r"(\d{1,4}),(\d{3})\s*만원?",
                ]

                for pattern in price_patterns:
                    price_match = re.search(pattern, row_text)
                    if price_match:
                        if len(price_match.groups()) == 2:
                            info["price"] = (
                                f"{price_match.group(1)},{price_match.group(2)}만원"
                            )
                        else:
                            info["price"] = f"{price_match.group(1)}만원"
                        break

            if not info.get("seller_type"):
                if "개인" in row_text:
                    info["seller_type"] = "개인"
                elif "업체" in row_text or "딜러" in row_text:
                    info["seller_type"] = "업체"

        except Exception as e:
            logger.warning(f"Failed to extract bike info from row: {str(e)}")

        return info

    def _extract_image_url(self, row: Tag, link: Tag) -> Optional[str]:
        """Extract bike image URL from row"""
        try:
            # Look for images in the same row
            images = row.find_all("img")

            for img in images:
                src = img.get("src", "")
                # Skip small icons and UI elements
                if any(
                    skip in src.lower()
                    for skip in ["icon", "btn", "bullet", "arrow", "dot"]
                ):
                    continue

                # Look for actual bike images
                if any(
                    bike_indicator in src.lower()
                    for bike_indicator in ["bike", "direct", "upload"]
                ):
                    if src.startswith("//"):
                        return "https:" + src
                    elif src.startswith("/"):
                        return self.BASE_URL + src
                    elif src.startswith("http"):
                        return src

        except Exception as e:
            logger.warning(f"Failed to extract image URL: {str(e)}")

        return None

    def parse_bike_detail(self, html_content: str, bike_id: str) -> Dict[str, Any]:
        """
        Parse detailed bike information from bike detail page
        Extracts comprehensive bike data, seller info, and metadata
        """
        try:
            soup = self._detect_encoding_and_parse(html_content)

            # Extract basic bike information
            bike_data = {
                "id": bike_id,
                "title": self._extract_bike_title(soup),
                "price": self._extract_price(soup),
                "images": self._extract_images(soup),
                "image_count": self._extract_image_count(soup),
                "main_image": self._extract_main_image(soup),
            }

            # Extract technical specifications
            specs = self._extract_specifications(soup)
            bike_data.update(specs)

            # Extract seller information
            seller_info = self._extract_seller_info(soup)
            bike_data.update(seller_info)

            # Extract documents and payment methods
            bike_data["documents"] = self._extract_documents(soup)
            bike_data["payment_methods"] = self._extract_payment_methods(soup)

            # Extract metadata
            metadata = self._extract_metadata(soup)
            bike_data.update(metadata)

            # Create BikeDetail object
            bike_detail = BikeDetail(**bike_data)

            return {
                "success": True,
                "bike": bike_detail,
                "meta": {
                    "parser_version": "2.1",
                    "bike_id": bike_id,
                    "encoding_detected": True,
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse bike detail for ID {bike_id}: {str(e)}")
            return {
                "success": False,
                "bike": None,
                "meta": {"error": str(e), "bike_id": bike_id, "parser_version": "2.1"},
            }

    def _extract_bike_title(self, soup: BeautifulSoup) -> str:
        """Extract bike model name from detail page"""
        try:
            # Look for the model name in the specifications table
            model_cell = soup.find("td", string="모델명")
            if model_cell:
                title_cell = model_cell.find_next_sibling("td")
                if title_cell:
                    return title_cell.get_text(strip=True)

            # Fallback: try to get from page title
            title_tag = soup.find("title")
            if title_tag:
                title_text = title_tag.get_text()
                if "바이크 -" in title_text:
                    return title_text.split("바이크 -")[-1].strip()

            return "Unknown Model"

        except Exception as e:
            logger.warning(f"Failed to extract bike title: {str(e)}")
            return "Unknown Model"

    def _extract_price(self, soup: BeautifulSoup) -> str:
        """Extract selling price"""
        try:
            # Look for price in the specifications table
            price_cell = soup.find("td", string="판매가격")
            if price_cell:
                price_cell = price_cell.find_next_sibling("td")
                if price_cell:
                    price_element = price_cell.find(class_="do_red_b1")
                    if price_element:
                        return price_element.get_text(strip=True)

            return "가격문의"

        except Exception as e:
            logger.warning(f"Failed to extract price: {str(e)}")
            return "가격문의"

    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract technical specifications from the detail table"""
        specs = {}

        # Mapping of Korean field names to our schema fields
        field_mapping = {
            "연식": "year",
            "주행거리": "mileage",
            "배기량": "engine_cc",
            "연료": "fuel_type",
            "변속기": "transmission",
            "색상": "color",
            "유형": "bike_type",
            "차량번호": "license_plate",
            "사고유무": "accident_history",
            "튜닝여부": "tuning_status",
            "구입경로": "purchase_route",
            "A/S보증여부": "warranty",
        }

        try:
            # Find all specification rows
            for korean_field, english_field in field_mapping.items():
                cell = soup.find("td", string=korean_field)
                if cell:
                    value_cell = cell.find_next_sibling("td")
                    if value_cell:
                        value = value_cell.get_text(strip=True)
                        if value and value != "-":
                            specs[english_field] = value

        except Exception as e:
            logger.warning(f"Failed to extract specifications: {str(e)}")

        return specs

    def _extract_seller_info(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract seller information"""
        seller_info = {}

        try:
            # Find seller information section
            seller_section = soup.find("strong", string=re.compile(r"판매자 정보"))
            if not seller_section:
                return seller_info

            # Find the seller info table
            seller_table = seller_section.find_parent("table")
            if not seller_table:
                return seller_info

            # Extract seller name and type
            name_cell = soup.find("td", string="이름")
            if name_cell:
                name_value_cell = name_cell.find_next_sibling("td")
                if name_value_cell:
                    name_text = name_value_cell.get_text(strip=True)
                    # Parse name and type (e.g., "신대식 (개인)")
                    if "(" in name_text and ")" in name_text:
                        name = name_text.split("(")[0].strip()
                        seller_type = name_text.split("(")[1].split(")")[0].strip()
                        seller_info["seller_name"] = name
                        seller_info["seller_type"] = seller_type
                    else:
                        seller_info["seller_name"] = name_text

            # Extract contact information
            contact_cell = soup.find("td", string="연락처")
            if contact_cell:
                contact_value_cell = contact_cell.find_next_sibling("td")
                if contact_value_cell:
                    # Find phone numbers
                    phone_elements = contact_value_cell.find_all(class_="do_gray_b1")
                    if len(phone_elements) >= 1:
                        seller_info["seller_mobile"] = phone_elements[0].get_text(
                            strip=True
                        )
                    if len(phone_elements) >= 2:
                        seller_info["seller_phone"] = phone_elements[1].get_text(
                            strip=True
                        )

            # Extract location
            location_cell = soup.find("td", string="지역")
            if location_cell:
                location_value_cell = location_cell.find_next_sibling("td")
                if location_value_cell:
                    seller_info["seller_location"] = location_value_cell.get_text(
                        strip=True
                    )

            # Extract email
            email_cell = soup.find("td", string="이메일")
            if email_cell:
                email_value_cell = email_cell.find_next_sibling("td")
                if email_value_cell:
                    email_link = email_value_cell.find("a")
                    if email_link and email_link.get("href", "").startswith("mailto:"):
                        seller_info["seller_email"] = email_link.get("href").replace(
                            "mailto:", ""
                        )

            # Extract company name
            company_cell = soup.find("td", string="업체명")
            if company_cell:
                company_value_cell = company_cell.find_next_sibling("td")
                if company_value_cell:
                    company_name = company_value_cell.get_text(strip=True)
                    if company_name and company_name != "-":
                        seller_info["company_name"] = company_name

            # Extract navigation address
            navi_cell = soup.find("td", string="네비주소")
            if navi_cell:
                navi_value_cell = navi_cell.find_next_sibling("td")
                if navi_value_cell:
                    seller_info["navi_address"] = navi_value_cell.get_text(strip=True)

            # Extract total listings count
            total_listings_text = soup.find(
                string=re.compile(r"판매자 보유매물 총.*대")
            )
            if total_listings_text:
                match = re.search(r"총(\d+)대", total_listings_text)
                if match:
                    seller_info["seller_total_listings"] = int(match.group(1))

        except Exception as e:
            logger.warning(f"Failed to extract seller info: {str(e)}")

        return seller_info

    def _extract_documents(self, soup: BeautifulSoup) -> List[str]:
        """Extract available documents"""
        documents = []

        try:
            # Find documents section
            docs_cell = soup.find("td", string="구비서류")
            if docs_cell:
                docs_section = docs_cell.find_next_sibling("td")
                if docs_section:
                    # Find all checked documents (detail_check01.gif = checked, detail_check02.gif = unchecked)
                    checked_docs = docs_section.find_all(
                        "img", src=re.compile(r"detail_check01\.gif")
                    )
                    for img in checked_docs:
                        # Get the text next to the checked image
                        parent = img.find_parent("td")
                        if parent:
                            next_td = parent.find_next_sibling("td")
                            if next_td:
                                doc_name = next_td.get_text(strip=True)
                                if doc_name:
                                    documents.append(doc_name)

                    # Alternative approach: look for all document names in the section
                    if not documents:
                        # Find all document labels in the section
                        doc_labels = docs_section.find_all("td", class_="p_d_black_s1")

                        # Extract all document names regardless of status for information
                        for doc_td in doc_labels:
                            doc_name = doc_td.get_text(strip=True)
                            if doc_name and doc_name.strip():
                                documents.append(f"{doc_name} (미비)")

        except Exception as e:
            logger.warning(f"Failed to extract documents: {str(e)}")

        return documents

    def _extract_payment_methods(self, soup: BeautifulSoup) -> List[str]:
        """Extract available payment methods"""
        payment_methods = []

        try:
            # Find payment methods section
            payment_cell = soup.find("td", string="판매방법")
            if payment_cell:
                payment_section = payment_cell.find_next_sibling("td")
                if payment_section:
                    # Find all checked payment methods
                    checked_payments = payment_section.find_all(
                        "img", src=re.compile(r"detail_check01\.gif")
                    )
                    for img in checked_payments:
                        parent = img.find_parent("td")
                        if parent:
                            next_td = parent.find_next_sibling("td")
                            if next_td:
                                payment_name = next_td.get_text(strip=True)
                                if payment_name:
                                    payment_methods.append(payment_name)

                    # Alternative approach: look for red colored payment methods (selected)
                    if not payment_methods:
                        red_payments = payment_section.find_all(
                            "td", class_="p_d_red_s1"
                        )
                        for payment_td in red_payments:
                            payment_name = payment_td.get_text(strip=True)
                            if payment_name:
                                payment_methods.append(payment_name)

        except Exception as e:
            logger.warning(f"Failed to extract payment methods: {str(e)}")

        return payment_methods

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract all bike images"""
        images = []

        try:
            # Find all bike images
            image_links = soup.find_all(
                "img", src=re.compile(r"file4\.bobaedream\.co\.kr/direct_bike")
            )

            for img in image_links:
                src = img.get("src")
                if src:
                    # Convert to full URL if needed
                    if src.startswith("//"):
                        src = "https:" + src
                    elif not src.startswith("http"):
                        src = urljoin(self.BASE_URL, src)

                    # Get full size image (remove _s1 suffix)
                    if "_s1.jpg" in src:
                        src = src.replace("_s1.jpg", ".jpg")

                    if src not in images:
                        images.append(src)

        except Exception as e:
            logger.warning(f"Failed to extract images: {str(e)}")

        return images

    def _extract_main_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main bike image"""
        try:
            # Find the main image element
            main_img = soup.find("img", id="BigImg")
            if main_img:
                src = main_img.get("src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif not src.startswith("http"):
                        src = urljoin(self.BASE_URL, src)
                    return src

        except Exception as e:
            logger.warning(f"Failed to extract main image: {str(e)}")

        return None

    def _extract_image_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract total image count"""
        try:
            # Look for image count indicator (e.g., "1/20")
            count_element = soup.find("span", id="nPhotoNum")
            if count_element:
                parent = count_element.find_parent("td")
                if parent:
                    count_text = parent.get_text(strip=True)
                    # Parse "1/20" format
                    if "/" in count_text:
                        total = count_text.split("/")[1]
                        return int(total)

        except Exception as e:
            logger.warning(f"Failed to extract image count: {str(e)}")

        return None

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata like registration date, views, etc."""
        metadata = {}

        try:
            # Find metadata text (registration date, views, favorites)
            # Look for the specific element containing metadata
            metadata_element = soup.find("td", class_="text_08")
            if metadata_element:
                metadata_text = metadata_element.get_text()

                # Parse registration date
                reg_match = re.search(
                    r"최초등록일:\s*(\d{4}/\d{2}/\d{2})", metadata_text
                )
                if reg_match:
                    metadata["registration_date"] = reg_match.group(1)

                # Parse view count (look for number in span with class text_12)
                view_span = metadata_element.find("span", class_="text_12")
                if view_span:
                    view_text = view_span.get_text(strip=True)
                    if view_text.isdigit():
                        metadata["view_count"] = int(view_text)

                # Parse today's views
                today_match = re.search(r"오늘:(\d+)", metadata_text)
                if today_match:
                    metadata["today_views"] = int(today_match.group(1))

                # Parse favorites
                fav_match = re.search(r"찜한회원:\s*(\d+)명", metadata_text)
                if fav_match:
                    metadata["favorites_count"] = int(fav_match.group(1))

            # Alternative approach: search in the entire page text
            if not metadata:
                metadata_text = soup.find(string=re.compile(r"최초등록일:.*조회수:"))
                if metadata_text:
                    # Parse registration date
                    reg_match = re.search(
                        r"최초등록일:\s*(\d{4}/\d{2}/\d{2})", metadata_text
                    )
                    if reg_match:
                        metadata["registration_date"] = reg_match.group(1)

                    # Parse view count
                    view_match = re.search(r"조회수:\s*(\d+)", metadata_text)
                    if view_match:
                        metadata["view_count"] = int(view_match.group(1))

                    # Parse today's views
                    today_match = re.search(r"오늘:(\d+)", metadata_text)
                    if today_match:
                        metadata["today_views"] = int(today_match.group(1))

                    # Parse favorites
                    fav_match = re.search(r"찜한회원:\s*(\d+)명", metadata_text)
                    if fav_match:
                        metadata["favorites_count"] = int(fav_match.group(1))

            # Extract image count from navigation
            photo_num_span = soup.find("span", id="nPhotoNum")
            if photo_num_span:
                # Look for the "X/Y" pattern in the parent element
                parent = photo_num_span.find_parent("td")
                if parent:
                    nav_text = parent.get_text(strip=True)
                    if "/" in nav_text:
                        try:
                            parts = nav_text.split("/")
                            if len(parts) == 2:
                                current_num = int(parts[0])
                                total_num = int(parts[1])
                                metadata["current_image"] = current_num
                                metadata["total_images"] = total_num
                        except ValueError:
                            pass

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")

        return metadata
