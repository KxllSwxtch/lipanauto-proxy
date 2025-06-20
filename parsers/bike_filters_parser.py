"""
Parser for bobaedream.co.kr bike filter API responses
Handles JSON parsing with Korean encoding and filter hierarchy
"""

import json
import logging
from typing import List, Dict, Any, Optional
from bs4.dammit import UnicodeDammit
from schemas.bike_filters import FilterOption, FilterLevel

logger = logging.getLogger(__name__)


class BikeFiltersParser:
    """
    Parser for bike filter API responses from bobaedream.co.kr
    Handles Korean encoding issues and JSON structure parsing
    """

    def __init__(self):
        self.parser_version = "1.0"

    def parse_filter_response(
        self, response_text: str, filter_level: int
    ) -> FilterLevel:
        """
        Parse JSON filter response with Korean encoding support

        Args:
            response_text: Raw response text from API
            filter_level: Filter level (0=category, 1=manufacturer, 3=model)

        Returns:
            FilterLevel object with parsed options
        """
        try:
            # Handle Korean encoding issues
            cleaned_text = self._fix_encoding(response_text)

            # Parse JSON
            filter_data = json.loads(cleaned_text)

            # Convert to FilterOption objects
            options = []
            for item in filter_data:
                try:
                    option = FilterOption(
                        sno=item.get("sno", ""),
                        cname=item.get("cname", ""),
                        cnt=item.get("cnt", "0"),
                        chk=item.get("chk", ""),
                    )
                    options.append(option)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse filter option: {item}, error: {str(e)}"
                    )
                    continue

            logger.info(
                f"Successfully parsed {len(options)} filter options for level {filter_level}"
            )

            return FilterLevel(
                success=True,
                options=options,
                level=filter_level,
                meta={
                    "parser_version": self.parser_version,
                    "total_options": len(options),
                    "encoding_fixed": True,
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for filter level {filter_level}: {str(e)}")
            return FilterLevel(
                success=False,
                options=[],
                level=filter_level,
                meta={
                    "error": f"JSON decode error: {str(e)}",
                    "parser_version": self.parser_version,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to parse filter response for level {filter_level}: {str(e)}"
            )
            return FilterLevel(
                success=False,
                options=[],
                level=filter_level,
                meta={"error": str(e), "parser_version": self.parser_version},
            )

    def _fix_encoding(self, text: str) -> str:
        """
        Fix Korean encoding issues in JSON response
        """
        try:
            # Try different encoding approaches
            if isinstance(text, str):
                # Method 1: Try to detect and fix mojibake
                for encoding in ["euc-kr", "cp949", "utf-8"]:
                    try:
                        # Convert string to bytes and back with correct encoding
                        text_bytes = text.encode("latin1")
                        decoded = text_bytes.decode(encoding)
                        # Test if JSON is valid
                        json.loads(decoded)
                        logger.info(f"Successfully fixed encoding with: {encoding}")
                        return decoded
                    except (
                        UnicodeDecodeError,
                        UnicodeEncodeError,
                        json.JSONDecodeError,
                    ):
                        continue

                # Method 2: Use UnicodeDammit as fallback
                try:
                    text_bytes = text.encode("latin1")
                    dammit = UnicodeDammit(text_bytes, ["euc-kr", "cp949", "utf-8"])
                    if dammit.unicode_markup:
                        logger.info(
                            f"Fixed encoding with UnicodeDammit: {dammit.original_encoding}"
                        )
                        return dammit.unicode_markup
                except Exception:
                    pass

            # If all else fails, return original text
            logger.warning("Could not fix encoding, using original text")
            return text

        except Exception as e:
            logger.error(f"Encoding fix failed: {str(e)}")
            return text

    def get_popular_categories(self, options: List[FilterOption]) -> List[str]:
        """
        Extract popular categories based on count
        """
        try:
            # Sort by count (descending) and take top categories
            sorted_options = sorted(options, key=lambda x: int(x.cnt), reverse=True)
            popular = [opt.sno for opt in sorted_options[:6] if int(opt.cnt) > 0]
            return popular
        except Exception as e:
            logger.warning(f"Failed to extract popular categories: {str(e)}")
            return []

    def get_popular_manufacturers(self, options: List[FilterOption]) -> List[str]:
        """
        Extract popular manufacturers based on count
        """
        try:
            # Sort by count (descending) and take top manufacturers
            sorted_options = sorted(options, key=lambda x: int(x.cnt), reverse=True)
            popular = [opt.sno for opt in sorted_options[:10] if int(opt.cnt) > 0]
            return popular
        except Exception as e:
            logger.warning(f"Failed to extract popular manufacturers: {str(e)}")
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
