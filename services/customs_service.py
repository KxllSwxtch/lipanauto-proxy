"""
Customs Calculator Service
Integrates with TKS.ru for customs duty calculations using CapSolver for CAPTCHA solving
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional, Any
import requests
from urllib.parse import urlencode

from schemas.customs import (
    CustomsCalculationRequest,
    CustomsCalculationResponse,
    CaptchaSolutionRequest,
    CaptchaSolutionResponse,
)
from parsers.tks_parser import TKSCustomsParser

logger = logging.getLogger(__name__)


class CustomsCalculatorService:
    """
    Service for calculating customs duties via TKS.ru
    Handles CAPTCHA solving via CapSolver API
    """

    def __init__(self, proxy_client=None):
        self.proxy_client = proxy_client
        self.parser = TKSCustomsParser()

        # CapSolver configuration
        self.capsolver_api_key = "CAP-C4D53EC5DFCB61861DD241B5BDAA0680"
        self.capsolver_base_url = "https://api.capsolver.com"

        # TKS.ru configuration
        self.tks_base_url = "https://www.tks.ru"
        self.tks_calculator_url = f"{self.tks_base_url}/auto/calc/"

        # reCAPTCHA configuration for TKS.ru
        self.recaptcha_site_key = (
            "6Lel2XIgAAAAAHk1OOPbgNBw7VGRt3Y_0YTXMfJZ"  # Extracted from TKS.ru page
        )

        # Session for requests
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Setup session with proper headers and configuration"""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Set timeout
        self.session.timeout = (10, 30)

    async def calculate_customs_duties(
        self, request: CustomsCalculationRequest
    ) -> CustomsCalculationResponse:
        """
        Calculate customs duties for a vehicle

        Args:
            request: Customs calculation parameters

        Returns:
            CustomsCalculationResponse with calculation results
        """
        try:
            logger.info(
                f"Starting customs calculation for vehicle: cost={request.cost}, volume={request.volume}cc"
            )

            # Step 1: Get TKS.ru page to extract reCAPTCHA site key
            site_key = await self._get_recaptcha_site_key()
            if not site_key:
                return CustomsCalculationResponse(
                    success=False,
                    error="Failed to extract reCAPTCHA site key from TKS.ru",
                    meta={"step": "site_key_extraction"},
                )

            # Step 2: Solve reCAPTCHA using CapSolver
            captcha_solution = await self._solve_captcha(site_key)
            if not captcha_solution.success:
                return CustomsCalculationResponse(
                    success=False,
                    error=f"CAPTCHA solving failed: {captcha_solution.error}",
                    meta={
                        "step": "captcha_solving",
                        "captcha_error": captcha_solution.error,
                    },
                )

            # Step 3: Make calculation request to TKS.ru
            calculation_result = await self._make_calculation_request(
                request, captcha_solution.solution
            )

            return calculation_result

        except Exception as e:
            logger.error(f"Customs calculation failed: {str(e)}")
            return CustomsCalculationResponse(
                success=False,
                error=f"Calculation failed: {str(e)}",
                meta={"step": "general_error"},
            )

    async def _get_recaptcha_site_key(self) -> Optional[str]:
        """
        Extract reCAPTCHA site key from TKS.ru calculator page

        Returns:
            reCAPTCHA site key or None if not found
        """
        try:
            logger.info("Extracting reCAPTCHA site key from TKS.ru")

            # Get the calculator page
            if self.proxy_client:
                response_data = await self.proxy_client.make_request(
                    self.tks_calculator_url
                )
                if not response_data.get("success"):
                    logger.error(
                        f"Failed to load TKS.ru page: {response_data.get('error')}"
                    )
                    return None
                html_content = response_data.get("text", "")
            else:
                response = self.session.get(self.tks_calculator_url)
                if response.status_code != 200:
                    logger.error(
                        f"Failed to load TKS.ru page: HTTP {response.status_code}"
                    )
                    return None
                html_content = response.text

            # Extract site key from HTML
            import re

            site_key_match = re.search(r'data-sitekey="([^"]+)"', html_content)
            if not site_key_match:
                # Try alternative patterns
                site_key_match = re.search(
                    r'sitekey["\']?\s*:\s*["\']([^"\']+)["\']', html_content
                )

            if site_key_match:
                site_key = site_key_match.group(1)
                logger.info(f"Extracted reCAPTCHA site key: {site_key[:20]}...")
                return site_key
            else:
                logger.warning("Could not extract reCAPTCHA site key, using default")
                # Return the site key we found from TKS.ru
                return "6Lel2XIgAAAAAHk1OOPbgNBw7VGRt3Y_0YTXMfJZ"

        except Exception as e:
            logger.error(f"Failed to extract reCAPTCHA site key: {str(e)}")
            return None

    async def _solve_captcha(self, site_key: str) -> CaptchaSolutionResponse:
        """
        Solve reCAPTCHA using CapSolver API

        Args:
            site_key: reCAPTCHA site key

        Returns:
            CaptchaSolutionResponse with solution or error
        """
        try:
            logger.info("Solving reCAPTCHA using CapSolver")
            start_time = time.time()

            # Create task
            task_data = {
                "clientKey": self.capsolver_api_key,
                "task": {
                    "type": "ReCaptchaV2TaskProxyLess",
                    "websiteURL": self.tks_calculator_url,
                    "websiteKey": site_key,
                },
            }

            # Submit task
            create_response = requests.post(
                f"{self.capsolver_base_url}/createTask", json=task_data, timeout=30
            )

            if create_response.status_code != 200:
                return CaptchaSolutionResponse(
                    success=False,
                    error=f"CapSolver API error: HTTP {create_response.status_code}",
                )

            create_result = create_response.json()
            if create_result.get("errorId") != 0:
                return CaptchaSolutionResponse(
                    success=False,
                    error=f"CapSolver task creation failed: {create_result.get('errorDescription', 'Unknown error')}",
                )

            task_id = create_result.get("taskId")
            if not task_id:
                return CaptchaSolutionResponse(
                    success=False, error="No task ID received from CapSolver"
                )

            logger.info(f"CapSolver task created: {task_id}")

            # Wait for solution
            max_attempts = 30  # 5 minutes maximum
            for attempt in range(max_attempts):
                await asyncio.sleep(10)  # Wait 10 seconds between checks

                # Get task result
                result_data = {"clientKey": self.capsolver_api_key, "taskId": task_id}

                result_response = requests.post(
                    f"{self.capsolver_base_url}/getTaskResult",
                    json=result_data,
                    timeout=30,
                )

                if result_response.status_code != 200:
                    continue

                result = result_response.json()

                if result.get("errorId") != 0:
                    return CaptchaSolutionResponse(
                        success=False,
                        error=f"CapSolver task failed: {result.get('errorDescription', 'Unknown error')}",
                        task_id=task_id,
                    )

                status = result.get("status")
                if status == "ready":
                    solution = result.get("solution", {}).get("gRecaptchaResponse")
                    if solution:
                        solving_time = time.time() - start_time
                        logger.info(
                            f"reCAPTCHA solved successfully in {solving_time:.1f}s"
                        )
                        return CaptchaSolutionResponse(
                            success=True,
                            solution=solution,
                            task_id=task_id,
                            solving_time=solving_time,
                        )
                elif status == "processing":
                    logger.info(
                        f"CapSolver task in progress... (attempt {attempt + 1}/{max_attempts})"
                    )
                    continue
                else:
                    return CaptchaSolutionResponse(
                        success=False,
                        error=f"Unexpected task status: {status}",
                        task_id=task_id,
                    )

            return CaptchaSolutionResponse(
                success=False,
                error="CapSolver timeout - solution not received within 5 minutes",
                task_id=task_id,
            )

        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {str(e)}")
            return CaptchaSolutionResponse(
                success=False, error=f"CAPTCHA solving error: {str(e)}"
            )

    async def _make_calculation_request(
        self, request: CustomsCalculationRequest, captcha_solution: str
    ) -> CustomsCalculationResponse:
        """
        Make calculation request to TKS.ru with solved CAPTCHA

        Args:
            request: Calculation parameters
            captcha_solution: Solved reCAPTCHA token

        Returns:
            CustomsCalculationResponse with parsed results
        """
        try:
            logger.info("Making calculation request to TKS.ru")

            # Prepare request parameters
            params = {
                "cost": request.cost,
                "volume": request.volume,
                "currency": request.currency,
                "power": request.power,
                "power_edizm": request.power_edizm,
                "country": request.country,
                "engine_type": request.engine_type,
                "age": request.age,
                "face": request.face,
                "ts_type": request.ts_type,
                "chassis": request.chassis,
                "forwarder": "true" if request.forwarder else "false",
                "caravan": "true" if request.caravan else "false",
                "offroad": "true" if request.offroad else "false",
                "buscap": request.buscap,
                "mdvs_gt_m30ed": "true" if request.mdvs_gt_m30ed else "false",
                "sequential": "true" if request.sequential else "false",
                "mode": "ajax",
                "t": "1",
                "captcha": captcha_solution,
            }

            # Add optional parameters
            if request.mass:
                params["mass"] = request.mass
            if request.boat_sea:
                params["boat_sea"] = request.boat_sea
            if request.sh2017:
                params["sh2017"] = request.sh2017
            if request.bus_municipal_cb:
                params["bus_municipal_cb"] = request.bus_municipal_cb

            # Build URL
            url = f"{self.tks_calculator_url}?{urlencode(params)}"

            # Make request
            if self.proxy_client:
                response_data = await self.proxy_client.make_request(url)
                if not response_data.get("success"):
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru request failed: {response_data.get('error')}",
                        meta={"step": "tks_request", "url": url},
                    )
                html_content = response_data.get("text", "")
            else:
                response = self.session.get(url)
                if response.status_code != 200:
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru returned HTTP {response.status_code}",
                        meta={"step": "tks_request", "url": url},
                    )
                html_content = response.text

            # Parse response
            original_request_dict = request.model_dump()
            parse_result = self.parser.parse_customs_calculation(
                html_content, original_request_dict
            )

            if not parse_result.get("success"):
                return CustomsCalculationResponse(
                    success=False,
                    error=f"Failed to parse TKS.ru response: {parse_result.get('error')}",
                    meta={
                        "step": "response_parsing",
                        "parse_meta": parse_result.get("meta", {}),
                        "response_preview": (
                            html_content[:500] if html_content else None
                        ),
                    },
                )

            return CustomsCalculationResponse(
                success=True,
                result=parse_result["result"],
                meta={
                    "step": "completed",
                    "parse_meta": parse_result.get("meta", {}),
                    "request_url": url,
                    "captcha_used": True,
                },
            )

        except Exception as e:
            logger.error(f"TKS.ru calculation request failed: {str(e)}")
            return CustomsCalculationResponse(
                success=False,
                error=f"Calculation request failed: {str(e)}",
                meta={"step": "request_error"},
            )

    async def get_balance(self) -> Dict[str, Any]:
        """
        Get CapSolver account balance

        Returns:
            Dict with balance information
        """
        try:
            balance_data = {"clientKey": self.capsolver_api_key}

            response = requests.post(
                f"{self.capsolver_base_url}/getBalance", json=balance_data, timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errorId") == 0:
                    return {
                        "success": True,
                        "balance": result.get("balance", 0),
                        "currency": "USD",
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("errorDescription", "Unknown error"),
                    }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Failed to get CapSolver balance: {str(e)}")
            return {"success": False, "error": str(e)}
