"""
VLB Broker HTML Response Parser
Parses customs calculation responses from VLB broker website
"""

import re
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from schemas.vlb_customs import VLBCustomsBreakdown

logger = logging.getLogger(__name__)


class VLBCustomsParser:
    """Parser for VLB broker customs calculation HTML responses"""

    def __init__(self):
        """Initialize the VLB customs parser"""
        self.parser_name = "lxml"  # Use lxml for better performance

    def parse_customs_response(self, html_content: str) -> Optional[VLBCustomsBreakdown]:
        """
        Parse VLB customs calculation HTML response

        Args:
            html_content: HTML content from VLB API response

        Returns:
            VLBCustomsBreakdown or None if parsing failed
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            # Extract customs breakdown values
            customs_data = {}

            # Parse customs processing fee
            customs_fee = self._extract_customs_processing_fee(soup)
            if customs_fee is not None:
                customs_data["customs_processing_fee"] = customs_fee
            else:
                logger.warning("Could not extract customs processing fee")
                return None

            # Parse duty information
            duty_info = self._extract_duty_info(soup)
            if duty_info:
                customs_data.update(duty_info)
            else:
                logger.warning("Could not extract duty information")
                return None

            # Parse VAT information
            vat_info = self._extract_vat_info(soup)
            if vat_info:
                customs_data.update(vat_info)
            else:
                logger.warning("Could not extract VAT information")
                return None

            # Parse total amount
            total = self._extract_total(soup)
            if total is not None:
                customs_data["total"] = total
            else:
                logger.warning("Could not extract total amount")
                return None

            # Create and return VLBCustomsBreakdown object
            return VLBCustomsBreakdown(**customs_data)

        except Exception as e:
            logger.error(f"Failed to parse VLB customs response: {str(e)}")
            return None

    def _extract_customs_processing_fee(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Extract customs processing fee from HTML

        Expected format: "Сборы за таможенное оформление:" followed by amount like "4 269 ₽"
        """
        try:
            # Find the section with customs processing fee
            fee_section = soup.find(string=re.compile(r"Сборы за таможенное оформление"))
            if not fee_section:
                return None

            # Navigate to the parent and find the price
            fee_parent = fee_section.find_parent()
            if not fee_parent:
                return None

            # Look for price in the same section or nearby
            price_div = fee_parent.find_next('div', class_='price-breakdown__price')
            if price_div:
                price_spans = price_div.find_all('span')
                for span in price_spans:
                    amount_text = span.get_text(strip=True)
                    amount = self._parse_ruble_amount(amount_text)
                    if amount is not None:
                        return amount

            # Fallback: search for amount in the next siblings
            next_elements = fee_parent.find_next_siblings(limit=3)
            for element in next_elements:
                text = element.get_text(strip=True)
                amount = self._parse_ruble_amount(text)
                if amount is not None:
                    return amount

            return None

        except Exception as e:
            logger.error(f"Failed to extract customs processing fee: {str(e)}")
            return None

    def _extract_duty_info(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract duty information from HTML

        Expected format: "Пошлина:" followed by rate like "15%" and amount like "103 201 ₽"
        """
        try:
            duty_section = soup.find(string=re.compile(r"Пошлина"))
            if not duty_section:
                return None

            duty_parent = duty_section.find_parent()
            if not duty_parent:
                return None

            result = {}

            # Look for price breakdown section
            price_div = duty_parent.find_next('div', class_='price-breakdown__price')
            if price_div:
                spans = price_div.find_all('span')

                # First span usually contains the rate, second contains the amount
                for span in spans:
                    text = span.get_text(strip=True)

                    # Check if it's a percentage (duty rate)
                    if '%' in text:
                        result['duty_rate'] = text
                    else:
                        # Try to parse as ruble amount
                        amount = self._parse_ruble_amount(text)
                        if amount is not None:
                            result['duty'] = amount

            # If we didn't get the duty amount, try alternative parsing
            if 'duty' not in result:
                next_elements = duty_parent.find_next_siblings(limit=3)
                for element in next_elements:
                    text = element.get_text(strip=True)
                    amount = self._parse_ruble_amount(text)
                    if amount is not None:
                        result['duty'] = amount
                        break

            return result if 'duty' in result else None

        except Exception as e:
            logger.error(f"Failed to extract duty information: {str(e)}")
            return None

    def _extract_vat_info(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract VAT information from HTML

        Expected format: "НДС:" followed by rate like "20%" and amount like "158 241 ₽"
        """
        try:
            vat_section = soup.find(string=re.compile(r"НДС"))
            if not vat_section:
                return None

            vat_parent = vat_section.find_parent()
            if not vat_parent:
                return None

            result = {}

            # Look for price breakdown section
            price_div = vat_parent.find_next('div', class_='price-breakdown__price')
            if price_div:
                spans = price_div.find_all('span')

                for span in spans:
                    text = span.get_text(strip=True)

                    # Check if it's a percentage (VAT rate)
                    if '%' in text:
                        result['vat_rate'] = text
                    else:
                        # Try to parse as ruble amount
                        amount = self._parse_ruble_amount(text)
                        if amount is not None:
                            result['vat'] = amount

            # If we didn't get the VAT amount, try alternative parsing
            if 'vat' not in result:
                next_elements = vat_parent.find_next_siblings(limit=3)
                for element in next_elements:
                    text = element.get_text(strip=True)
                    amount = self._parse_ruble_amount(text)
                    if amount is not None:
                        result['vat'] = amount
                        break

            return result if 'vat' in result else None

        except Exception as e:
            logger.error(f"Failed to extract VAT information: {str(e)}")
            return None

    def _extract_total(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Extract total customs amount from HTML

        Expected format: "Итого: 265 711 ₽" in footer section
        """
        try:
            # Look for "Итого" text
            total_section = soup.find(string=re.compile(r"Итого"))
            if not total_section:
                return None

            # Get the parent element
            total_parent = total_section.find_parent()
            if not total_parent:
                return None

            # Extract the amount from the same element or parent
            total_text = total_parent.get_text(strip=True)
            amount = self._parse_ruble_amount(total_text)
            if amount is not None:
                return amount

            # Try looking in footer section
            footer = soup.find('div', class_='price-breakdown__footer')
            if footer:
                footer_text = footer.get_text(strip=True)
                amount = self._parse_ruble_amount(footer_text)
                if amount is not None:
                    return amount

            return None

        except Exception as e:
            logger.error(f"Failed to extract total amount: {str(e)}")
            return None

    def _parse_ruble_amount(self, text: str) -> Optional[int]:
        """
        Parse ruble amount from text

        Handles formats like:
        - "4 269 ₽"
        - "103 201 ₽"
        - "158 241 ₽"
        - "265 711 ₽"
        """
        if not text:
            return None

        try:
            # Remove ruble symbol and clean the text
            clean_text = text.replace('₽', '').replace('руб', '').strip()

            # Remove spaces and convert to integer
            # Handle format like "265 711" -> "265711"
            numeric_text = re.sub(r'\s+', '', clean_text)

            # Extract only digits
            digits_only = re.search(r'(\d+)', numeric_text)
            if digits_only:
                return int(digits_only.group(1))

            return None

        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse amount from '{text}': {str(e)}")
            return None

    def extract_currency_rates(self, html_content: str) -> Dict[str, str]:
        """
        Extract currency rates from VLB response

        Expected format in HTML:
        - "Курс USD: 83,0718 руб. за 1 USD"
        - "Курс KRW: 59,8198 руб. за 1000 KRW"
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            rates = {}

            # Find currency text section
            currency_section = soup.find('div', class_='currency-text')
            if currency_section:
                paragraphs = currency_section.find_all('p')

                for p in paragraphs:
                    text = p.get_text(strip=True)

                    # Parse different currency formats
                    if 'USD:' in text:
                        rate_match = re.search(r'USD:\s*([\d,]+)', text)
                        if rate_match:
                            rates['USD'] = rate_match.group(1)
                    elif 'EUR:' in text:
                        rate_match = re.search(r'EUR:\s*([\d,]+)', text)
                        if rate_match:
                            rates['EUR'] = rate_match.group(1)
                    elif 'JPY:' in text:
                        rate_match = re.search(r'JPY:\s*([\d,]+)', text)
                        if rate_match:
                            rates['JPY'] = rate_match.group(1)
                    elif 'KRW:' in text:
                        rate_match = re.search(r'KRW:\s*([\d,]+)', text)
                        if rate_match:
                            rates['KRW'] = rate_match.group(1)
                    elif 'CNY:' in text:
                        rate_match = re.search(r'CNY:\s*([\d,]+)', text)
                        if rate_match:
                            rates['CNY'] = rate_match.group(1)

            return rates

        except Exception as e:
            logger.error(f"Failed to extract currency rates: {str(e)}")
            return {}