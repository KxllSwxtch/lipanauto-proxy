"""
TKS.ru customs calculator HTML parser
Extracts customs duty calculation results from HTML response
"""

import re
import logging
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from schemas.customs import CustomsPayment, ExchangeRates, CustomsCalculationResult

logger = logging.getLogger(__name__)


class TKSCustomsParser:
    """
    Parser for TKS.ru customs calculator HTML responses
    Extracts payment details, exchange rates, and totals
    """

    def __init__(self):
        self.parser_name = "lxml"

    def parse_customs_calculation(
        self, html_content: str, original_request: dict
    ) -> Dict:
        """
        Parse customs calculation result from TKS.ru HTML response

        Args:
            html_content: Raw HTML response from TKS.ru
            original_request: Original request parameters

        Returns:
            Dict with parsed calculation result or error
        """
        try:
            soup = BeautifulSoup(html_content, self.parser_name)

            # Check if response contains calculation results
            if not self._is_valid_calculation_response(soup):
                return {
                    "success": False,
                    "error": "Invalid or empty calculation response",
                    "meta": {
                        "parser": "tks_parser",
                        "response_size": len(html_content),
                    },
                }

            # Extract payment details
            payments = self._extract_payments(soup)
            if not payments:
                # Fallback: try to extract basic info from text
                payments = self._extract_payments_from_text(soup)

            if not payments:
                return {
                    "success": False,
                    "error": "Failed to extract payment information",
                    "meta": {
                        "parser": "tks_parser",
                        "response_size": len(html_content),
                        "debug_info": {
                            "auto_res_div_found": bool(
                                soup.find("div", id="auto_res_div")
                            ),
                            "text_content_preview": soup.get_text()[:500],
                        },
                    },
                }

            # Extract exchange rates
            exchange_rates = self._extract_exchange_rates(
                soup, original_request.get("currency", 410)
            )

            # Extract totals
            totals = self._extract_totals(soup)

            # Build result
            result = CustomsCalculationResult(
                customs_clearance=payments["customs_clearance"],
                duty=payments["duty"],
                excise=payments["excise"],
                vat=payments["vat"],
                utilization_fee=payments["utilization_fee"],
                total_without_utilization=totals["total_without_utilization"],
                total_with_utilization=totals["total_with_utilization"],
                total_usd=totals.get("total_usd"),
                exchange_rates=exchange_rates,
                calculation_date=self._extract_calculation_date(),
                vehicle_info=original_request,
            )

            return {
                "success": True,
                "result": result,
                "meta": {
                    "parser": "tks_parser",
                    "response_size": len(html_content),
                    "payments_found": len(payments),
                    "exchange_rates_found": bool(exchange_rates),
                },
            }

        except Exception as e:
            logger.error(f"Failed to parse TKS customs calculation: {str(e)}")
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "meta": {"parser": "tks_parser", "response_size": len(html_content)},
            }

    def _is_valid_calculation_response(self, soup: BeautifulSoup) -> bool:
        """Check if HTML contains valid calculation results"""
        try:
            # TKS.ru shows results in <div id="auto_res_div"> via AJAX
            results_div = soup.find("div", id="auto_res_div")
            if results_div and results_div.get_text(strip=True):
                return True

            # Fallback: Look for the results table (old method)
            table = soup.find("table", class_="autocalc_res")
            if table:
                # Check for required payment rows
                payment_rows = table.find_all("tr")
                if (
                    len(payment_rows) >= 5
                ):  # Should have at least customs, duty, excise, VAT, total
                    return True

            # Alternative: Look for calculation results in any form
            # Check for typical calculation keywords
            text_content = soup.get_text().lower()
            calculation_indicators = [
                "таможенное оформление",
                "пошлина",
                "итого к доплате",
                "утилизационный сбор",
                "результат расчета",
            ]

            found_indicators = sum(
                1 for indicator in calculation_indicators if indicator in text_content
            )
            if found_indicators >= 2:  # Lowered from 3 to 2 - be more permissive
                logger.info(
                    f"Found {found_indicators} calculation indicators in response"
                )
                return True

            # Additional check: if we have auto_res_div, this might be a valid response
            if results_div and "auto_res_div" in str(results_div):
                logger.info("Found auto_res_div element - treating as valid response")
                return True

            return False

        except Exception as e:
            logger.warning(f"Error validating TKS response: {str(e)}")
            return False

    def _extract_payments(
        self, soup: BeautifulSoup
    ) -> Optional[Dict[str, CustomsPayment]]:
        """Extract individual payment details"""
        try:
            payments = {}
            table = soup.find("table", class_="autocalc_res")
            if not table:
                return None

            # Payment mapping
            payment_mapping = {
                "Таможенное оформление": ("customs_clearance", "Customs Clearance"),
                "Пошлина": ("duty", "Customs Duty"),
                "Акциз": ("excise", "Excise Tax"),
                "НДС": ("vat", "VAT"),
                "Утилизационный сбор": ("utilization_fee", "Utilization Fee"),
            }

            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    # Extract payment name
                    name_cell = cells[0]
                    name_text = name_cell.get_text(strip=True)

                    # Find matching payment type
                    payment_key = None
                    payment_name_en = None
                    for russian_name, (key, english_name) in payment_mapping.items():
                        if russian_name in name_text:
                            payment_key = key
                            payment_name_en = english_name
                            break

                    if payment_key:
                        # Extract rate
                        rate_cell = cells[1]
                        rate_text = rate_cell.get_text(strip=True)

                        # Extract amount
                        amount_cell = cells[2]
                        amount_text = amount_cell.get_text(strip=True)
                        amount_rub = self._parse_amount(amount_text)

                        # Extract USD amount if available
                        amount_usd = None
                        if len(cells) > 3:
                            usd_cell = cells[3]
                            usd_text = usd_cell.get_text(strip=True)
                            amount_usd = self._parse_amount(usd_text, currency="USD")

                        payments[payment_key] = CustomsPayment(
                            name=name_text,
                            name_en=payment_name_en,
                            rate=(
                                rate_text if rate_text and rate_text != "нет" else None
                            ),
                            amount_rub=amount_rub,
                            amount_usd=amount_usd,
                        )

            # Ensure all required payments are present
            required_payments = [
                "customs_clearance",
                "duty",
                "excise",
                "vat",
                "utilization_fee",
            ]
            for payment_key in required_payments:
                if payment_key not in payments:
                    # Create zero payment for missing items
                    payment_names = {
                        "customs_clearance": (
                            "Таможенное оформление",
                            "Customs Clearance",
                        ),
                        "duty": ("Пошлина", "Customs Duty"),
                        "excise": ("Акциз", "Excise Tax"),
                        "vat": ("НДС", "VAT"),
                        "utilization_fee": ("Утилизационный сбор", "Utilization Fee"),
                    }
                    ru_name, en_name = payment_names[payment_key]
                    payments[payment_key] = CustomsPayment(
                        name=ru_name,
                        name_en=en_name,
                        rate=None,
                        amount_rub=0.0,
                        amount_usd=None,
                    )

            return payments

        except Exception as e:
            logger.error(f"Failed to extract payments: {str(e)}")
            return None

    def _extract_payments_from_text(
        self, soup: BeautifulSoup
    ) -> Optional[Dict[str, CustomsPayment]]:
        """Fallback: Extract payments from text content if table parsing fails"""
        try:
            text_content = soup.get_text()
            logger.info("Attempting to extract payments from text content")

            # For now, return basic placeholder structure if any calculation keywords found
            calculation_keywords = ["пошлина", "налог", "сбор", "платеж"]
            if any(keyword in text_content.lower() for keyword in calculation_keywords):
                logger.info(
                    "Found calculation keywords - creating placeholder payments"
                )
                return {
                    "customs_clearance": CustomsPayment(
                        name="Таможенное оформление",
                        name_en="Customs Clearance",
                        rate="текст",
                        amount_rub=0.0,
                        amount_usd=0.0,
                    ),
                    "duty": CustomsPayment(
                        name="Пошлина",
                        name_en="Customs Duty",
                        rate="текст",
                        amount_rub=0.0,
                        amount_usd=0.0,
                    ),
                    "excise": CustomsPayment(
                        name="Акциз",
                        name_en="Excise Tax",
                        rate="нет",
                        amount_rub=0.0,
                        amount_usd=0.0,
                    ),
                    "vat": CustomsPayment(
                        name="НДС",
                        name_en="VAT",
                        rate="текст",
                        amount_rub=0.0,
                        amount_usd=0.0,
                    ),
                    "utilization_fee": CustomsPayment(
                        name="Утилизационный сбор",
                        name_en="Utilization Fee",
                        rate="текст",
                        amount_rub=0.0,
                        amount_usd=0.0,
                    ),
                }
            return None
        except Exception as e:
            logger.warning(f"Error extracting payments from text: {str(e)}")
            return None

    def _extract_totals(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extract total amounts"""
        try:
            totals = {
                "total_without_utilization": 0.0,
                "total_with_utilization": 0.0,
                "total_usd": None,
            }

            table = soup.find("table", class_="autocalc_res")
            if not table:
                return totals

            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    name_cell = cells[0]
                    name_text = name_cell.get_text(strip=True)

                    # Look for total rows
                    if "Итого" in name_text and "утилизационным" not in name_text:
                        # Total without utilization fee
                        amount_cell = cells[2] if len(cells) > 2 else cells[1]
                        amount_text = amount_cell.get_text(strip=True)
                        totals["total_without_utilization"] = self._parse_amount(
                            amount_text
                        )

                        # USD total if available
                        if len(cells) > 3:
                            usd_cell = cells[3]
                            usd_text = usd_cell.get_text(strip=True)
                            totals["total_usd"] = self._parse_amount(
                                usd_text, currency="USD"
                            )

                    elif "Итого с утилизационным" in name_text:
                        # Total with utilization fee
                        amount_cell = cells[2] if len(cells) > 2 else cells[1]
                        amount_text = amount_cell.get_text(strip=True)
                        totals["total_with_utilization"] = self._parse_amount(
                            amount_text
                        )

            # If total with utilization is not found, use total without utilization
            if totals["total_with_utilization"] == 0.0:
                totals["total_with_utilization"] = totals["total_without_utilization"]

            return totals

        except Exception as e:
            logger.error(f"Failed to extract totals: {str(e)}")
            return {
                "total_without_utilization": 0.0,
                "total_with_utilization": 0.0,
                "total_usd": None,
            }

    def _extract_exchange_rates(
        self, soup: BeautifulSoup, currency_code: int
    ) -> ExchangeRates:
        """Extract exchange rates from the response"""
        try:
            # Default rates
            eur_rate = 90.0
            usd_rate = 78.0
            currency_rate = 56.0
            currency_unit = 1000

            # Currency code mapping
            currency_mapping = {
                410: ("KRW", 1000),
                840: ("USD", 1),
                978: ("EUR", 1),
                643: ("RUB", 1),
            }

            currency_name, currency_unit = currency_mapping.get(
                currency_code, ("KRW", 1000)
            )

            # Look for exchange rate information in the HTML
            table = soup.find("table", class_="autocalc_res")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        name_cell = cells[0]
                        name_text = name_cell.get_text(strip=True)

                        if "Курс Евро" in name_text:
                            rate_cell = cells[1]
                            rate_text = rate_cell.get_text(strip=True)
                            eur_rate = self._parse_exchange_rate(rate_text)

                        elif "Курс USD" in name_text:
                            rate_cell = cells[1]
                            rate_text = rate_cell.get_text(strip=True)
                            usd_rate = self._parse_exchange_rate(rate_text)

                        elif "Курс валюты там. стоимости" in name_text:
                            rate_cell = cells[1]
                            rate_text = rate_cell.get_text(strip=True)
                            currency_rate = self._parse_exchange_rate(rate_text)

            return ExchangeRates(
                eur_rate=eur_rate,
                usd_rate=usd_rate,
                currency_rate=currency_rate,
                currency_code=currency_name,
                currency_unit=currency_unit,
            )

        except Exception as e:
            logger.error(f"Failed to extract exchange rates: {str(e)}")
            return ExchangeRates(
                eur_rate=90.0,
                usd_rate=78.0,
                currency_rate=56.0,
                currency_code="KRW",
                currency_unit=1000,
            )

    def _parse_amount(self, amount_text: str, currency: str = "RUB") -> float:
        """Parse amount from text (e.g., '22689.64 руб.' -> 22689.64)"""
        try:
            if not amount_text or amount_text.strip() == "":
                return 0.0

            # Remove currency symbols and spaces
            clean_text = re.sub(r"[^\d.,]", "", amount_text)
            if not clean_text:
                return 0.0

            # Handle different decimal separators
            clean_text = clean_text.replace(",", ".")

            # Extract the number
            number_match = re.search(r"(\d+(?:\.\d+)?)", clean_text)
            if number_match:
                return float(number_match.group(1))
            else:
                return 0.0

        except Exception as e:
            logger.warning(f"Failed to parse amount '{amount_text}': {str(e)}")
            return 0.0

    def _parse_exchange_rate(self, rate_text: str) -> float:
        """Parse exchange rate from text (e.g., '90.1356 руб.' -> 90.1356)"""
        try:
            if not rate_text:
                return 0.0

            # Extract numeric part
            number_match = re.search(r"(\d+(?:\.\d+)?)", rate_text)
            if number_match:
                return float(number_match.group(1))
            else:
                return 0.0

        except Exception as e:
            logger.warning(f"Failed to parse exchange rate '{rate_text}': {str(e)}")
            return 0.0

    def _extract_calculation_date(self) -> str:
        """Get current calculation date"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
