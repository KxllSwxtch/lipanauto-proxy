"""
Customs Calculator Service
Integrates with TKS.ru for customs duty calculations using CapSolver for CAPTCHA solving
OPTIMIZED: With CAPTCHA token caching and pre-solving for faster responses
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional, Any, List
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass

from schemas.customs import (
    CustomsCalculationRequest,
    CustomsCalculationResponse,
    CaptchaSolutionRequest,
    CaptchaSolutionResponse,
)
from parsers.tks_parser import TKSCustomsParser

logger = logging.getLogger(__name__)


@dataclass
class CachedCaptchaToken:
    """Cached CAPTCHA token with expiration"""

    token: str
    created_at: datetime
    used_count: int = 0
    max_uses: int = 3  # Reduced from 5 to 3 for cloud reliability
    expiry_minutes: int = 5  # Reduced from 10 to 5 minutes for cloud reliability

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return (
            datetime.now() - self.created_at > timedelta(minutes=self.expiry_minutes)
            or self.used_count >= self.max_uses
        )

    def use_token(self) -> str:
        """Mark token as used and return it"""
        self.used_count += 1
        return self.token


class CustomsCalculatorService:
    """
    OPTIMIZED Service for calculating customs duties via TKS.ru
    Features:
    - CAPTCHA token caching (reuse tokens for 10 minutes or 5 uses)
    - Background pre-solving of CAPTCHA tokens
    - Fast response times (< 2 seconds when cached tokens available)
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

        # Session for requests with cookie persistence
        self.session = requests.Session()
        # Enable cookie jar
        self.session.cookies = requests.cookies.RequestsCookieJar()
        self._setup_session()

        # OPTIMIZATION: CAPTCHA token cache
        self.captcha_cache: List[CachedCaptchaToken] = []
        self.cache_lock = threading.Lock()
        self.min_cached_tokens = 2  # Reduced from 3 to 2 for faster updates
        self.max_cached_tokens = 5  # Reduced from 10 to 5 to keep tokens fresh

        # Background task for pre-solving CAPTCHA
        self.background_task_running = False
        self._start_background_captcha_solver()

        # Performance metrics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_generated": 0,
            "avg_response_time": 0,
        }

    def _setup_session(self):
        """Setup session with proper headers and configuration"""
        # First, visit the calculator page to get cookies
        try:
            logger.info("Initializing TKS.ru session with cookies...")
            init_response = self.session.get(self.tks_calculator_url, timeout=10)
            if init_response.status_code == 200:
                logger.info(
                    f"✅ TKS.ru session initialized, cookies: {len(self.session.cookies)}"
                )
            else:
                logger.warning(
                    f"⚠️ TKS.ru session init returned {init_response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize TKS.ru session: {str(e)}")

        # Update headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "Referer": "https://www.tks.ru/auto/calc/",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        # Set timeout
        self.session.timeout = (10, 30)

    def _start_background_captcha_solver(self):
        """Start background thread for pre-solving CAPTCHA tokens"""
        if not self.background_task_running:
            self.background_task_running = True
            background_thread = threading.Thread(
                target=self._background_captcha_loop, daemon=True
            )
            background_thread.start()
            logger.info("🚀 Background CAPTCHA solver started")

    def _background_captcha_loop(self):
        """Background loop to maintain cached CAPTCHA tokens"""
        while self.background_task_running:
            try:
                # Clean expired tokens
                self._clean_expired_tokens()

                # Check if we need more tokens
                active_tokens = len([t for t in self.captcha_cache if not t.is_expired])

                if active_tokens < self.min_cached_tokens:
                    tokens_needed = self.min_cached_tokens - active_tokens
                    logger.info(f"🔄 Pre-solving {tokens_needed} CAPTCHA tokens...")

                    for _ in range(tokens_needed):
                        if len(self.captcha_cache) >= self.max_cached_tokens:
                            break

                        # Solve CAPTCHA in background
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            solution = loop.run_until_complete(
                                self._solve_captcha_internal(self.recaptcha_site_key)
                            )

                            if solution.success:
                                with self.cache_lock:
                                    cached_token = CachedCaptchaToken(
                                        token=solution.solution,
                                        created_at=datetime.now(),
                                    )
                                    self.captcha_cache.append(cached_token)
                                    self.stats["tokens_generated"] += 1

                                logger.info(
                                    f"✅ Pre-solved CAPTCHA token cached ({len(self.captcha_cache)} total)"
                                )
                            else:
                                logger.warning(
                                    f"❌ Failed to pre-solve CAPTCHA: {solution.error}"
                                )

                        except Exception as e:
                            logger.error(f"Background CAPTCHA solving error: {str(e)}")
                        finally:
                            loop.close()

                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Background CAPTCHA loop error: {str(e)}")
                time.sleep(60)  # Wait longer on error

    def _clean_expired_tokens(self):
        """Remove expired tokens from cache"""
        with self.cache_lock:
            before_count = len(self.captcha_cache)
            self.captcha_cache = [t for t in self.captcha_cache if not t.is_expired]
            after_count = len(self.captcha_cache)

            if before_count > after_count:
                logger.info(
                    f"🧹 Cleaned {before_count - after_count} expired CAPTCHA tokens"
                )

    def _invalidate_all_tokens(self):
        """Invalidate all cached tokens (used when CAPTCHA error detected)"""
        with self.cache_lock:
            count = len(self.captcha_cache)
            self.captcha_cache = []
            logger.warning(
                f"🗑️ Invalidated ALL {count} cached CAPTCHA tokens due to error"
            )

    def _get_cached_captcha_token(self) -> Optional[str]:
        """Get a cached CAPTCHA token if available"""
        with self.cache_lock:
            for token in self.captcha_cache:
                if not token.is_expired:
                    used_token = token.use_token()
                    self.stats["cache_hits"] += 1
                    logger.info(
                        f"⚡ Using cached CAPTCHA token (uses: {token.used_count}/{token.max_uses})"
                    )
                    return used_token

        self.stats["cache_misses"] += 1
        return None

    async def calculate_customs_duties(
        self, request: CustomsCalculationRequest
    ) -> CustomsCalculationResponse:
        """
        OPTIMIZED: Calculate customs duties for a vehicle
        Uses cached CAPTCHA tokens for fast response (< 2 seconds when cached)

        Args:
            request: Customs calculation parameters

        Returns:
            CustomsCalculationResponse with calculation results
        """
        start_time = time.time()

        try:
            logger.info(
                f"Starting OPTIMIZED customs calculation: cost={request.cost}, volume={request.volume}cc"
            )

            # Step 1: Try to get cached CAPTCHA token first
            captcha_solution = self._get_cached_captcha_token()

            if captcha_solution:
                logger.info("⚡ Using cached CAPTCHA token - FAST PATH")
                # Update cache stats
                self.stats["cache_hits"] += 1
            else:
                logger.info("🐌 No cached token available - solving new CAPTCHA")
                # Update cache stats
                self.stats["cache_misses"] += 1

                # Step 2: Get site key (usually cached)
                site_key = await self._get_recaptcha_site_key()
                if not site_key:
                    logger.error("Failed to get reCAPTCHA site key")
                    return CustomsCalculationResponse(
                        success=False,
                        error="Failed to extract reCAPTCHA site key from TKS.ru",
                        meta={
                            "step": "site_key_extraction",
                            "optimization": "cache_miss",
                            "site_key_configured": bool(self.recaptcha_site_key),
                        },
                    )

                # Step 3: Solve new CAPTCHA
                logger.info(f"Solving CAPTCHA with site key: {site_key[:20]}...")
                captcha_response = await self._solve_captcha_internal(site_key)
                if not captcha_response.success:
                    logger.error(f"CAPTCHA solving failed: {captcha_response.error}")
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"CAPTCHA solving failed: {captcha_response.error}",
                        meta={
                            "step": "captcha_solving",
                            "captcha_error": captcha_response.error,
                            "task_id": getattr(captcha_response, "task_id", None),
                            "optimization": "cache_miss",
                            "capsolver_balance_check": "Check /api/customs/balance",
                        },
                    )

                captcha_solution = captcha_response.solution
                logger.info(
                    f"✅ CAPTCHA solved successfully: {len(captcha_solution)} chars"
                )

            # Step 4: Make calculation request to TKS.ru
            logger.info("Starting TKS.ru calculation request...")
            calculation_result = await self._make_calculation_request(
                request, captcha_solution
            )

            # Add performance metrics
            response_time = time.time() - start_time
            self.stats["avg_response_time"] = (
                self.stats["avg_response_time"] + response_time
            ) / 2

            if calculation_result.success:
                logger.info(f"✅ Customs calculation completed in {response_time:.1f}s")
                calculation_result.meta["optimization"] = {
                    "response_time": f"{response_time:.1f}s",
                    "cache_hit": captcha_solution
                    != getattr(
                        locals().get("captcha_response", object()), "solution", None
                    ),
                    "cache_stats": self.get_cache_stats(),
                }
            else:
                logger.error(
                    f"❌ Customs calculation failed: {calculation_result.error}"
                )
                # Add debug info to error response
                if not calculation_result.meta:
                    calculation_result.meta = {}
                calculation_result.meta.update(
                    {
                        "optimization": {
                            "response_time": f"{response_time:.1f}s",
                            "cache_hit": captcha_solution
                            != getattr(
                                locals().get("captcha_response", object()),
                                "solution",
                                None,
                            ),
                            "cache_stats": self.get_cache_stats(),
                        },
                        "debug_info": {
                            "captcha_solution_length": (
                                len(captcha_solution) if captcha_solution else 0
                            ),
                            "request_params": {
                                "cost": request.cost,
                                "volume": request.volume,
                                "currency": request.currency,
                                "age": request.age,
                            },
                        },
                    }
                )

            return calculation_result

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(
                f"OPTIMIZED customs calculation failed with exception: {str(e)}",
                exc_info=True,
            )
            return CustomsCalculationResponse(
                success=False,
                error=f"Calculation failed: {str(e)}",
                meta={
                    "step": "general_error",
                    "optimization": {
                        "response_time": f"{response_time:.1f}s",
                        "cache_stats": self.get_cache_stats(),
                    },
                    "exception_type": type(e).__name__,
                    "exception_details": str(e),
                },
            )

    async def _get_recaptcha_site_key(self) -> Optional[str]:
        """
        Extract reCAPTCHA site key from TKS.ru calculator page
        OPTIMIZED: Returns cached site key immediately

        Returns:
            reCAPTCHA site key or None if not found
        """
        # Return cached site key immediately (we know it doesn't change)
        return self.recaptcha_site_key

    async def _solve_captcha_internal(self, site_key: str) -> CaptchaSolutionResponse:
        """
        Internal method to solve reCAPTCHA using CapSolver API
        Used by both foreground and background solving

        Args:
            site_key: reCAPTCHA site key

        Returns:
            CaptchaSolutionResponse with solution or error
        """
        try:
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

            # Wait for solution with optimized polling
            max_attempts = 24  # Reduced from 30 for faster timeout
            poll_interval = 5  # Reduced from 10 seconds

            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)

                # Get task result
                result_data = {"clientKey": self.capsolver_api_key, "taskId": task_id}

                result_response = requests.post(
                    f"{self.capsolver_base_url}/getTaskResult",
                    json=result_data,
                    timeout=15,  # Reduced timeout
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
                        return CaptchaSolutionResponse(
                            success=True,
                            solution=solution,
                            task_id=task_id,
                            solving_time=solving_time,
                        )
                elif status == "processing":
                    continue
                else:
                    return CaptchaSolutionResponse(
                        success=False,
                        error=f"Unexpected task status: {status}",
                        task_id=task_id,
                    )

            return CaptchaSolutionResponse(
                success=False,
                error="CapSolver timeout - solution not received within 2 minutes",
                task_id=task_id,
            )

        except Exception as e:
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
            logger.info(f"TKS.ru URL: {url[:100]}...")
            logger.info(
                f"CAPTCHA token being used: {captcha_solution[:50]}...{captcha_solution[-20:] if len(captcha_solution) > 70 else ''}"
            )

            # Make request with improved error handling for cloud environments
            if self.proxy_client:
                logger.info("Using proxy client for TKS.ru request")
                response_data = await self.proxy_client.make_request(url)
                if not response_data.get("success"):
                    error_msg = response_data.get("error", "Unknown proxy error")
                    logger.error(f"Proxy request failed: {error_msg}")
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru request failed via proxy: {error_msg}",
                        meta={
                            "step": "tks_request",
                            "url": url[:100] + "...",
                            "proxy_error": True,
                            "proxy_response": response_data,
                        },
                    )
                html_content = response_data.get("text", "")
                logger.info(f"Received HTML response: {len(html_content)} bytes")
            else:
                logger.info("Using direct connection for TKS.ru request")
                try:
                    # Log cookies before request
                    logger.info(f"Session cookies: {len(self.session.cookies)} items")

                    # Enhanced timeout and error handling for cloud environments
                    response = self.session.get(
                        url, timeout=(15, 45)
                    )  # Increased timeouts
                    logger.info(f"TKS.ru response: {response.status_code}")
                    logger.info(f"Response headers: {dict(response.headers)}")

                    if response.status_code != 200:
                        logger.error(
                            f"TKS.ru returned HTTP {response.status_code}: {response.text[:200]}"
                        )
                        return CustomsCalculationResponse(
                            success=False,
                            error=f"TKS.ru returned HTTP {response.status_code}",
                            meta={
                                "step": "tks_request",
                                "url": url[:100] + "...",
                                "http_status": response.status_code,
                                "response_preview": response.text[:200],
                            },
                        )
                    html_content = response.text
                    logger.info(f"Received HTML response: {len(html_content)} bytes")

                except requests.exceptions.Timeout as e:
                    logger.error(f"TKS.ru request timeout: {str(e)}")
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru request timeout: {str(e)}",
                        meta={"step": "tks_request", "timeout": True},
                    )
                except requests.exceptions.ConnectionError as e:
                    logger.error(f"TKS.ru connection error: {str(e)}")
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru connection error: {str(e)}",
                        meta={"step": "tks_request", "connection_error": True},
                    )
                except requests.exceptions.RequestException as e:
                    logger.error(f"TKS.ru request error: {str(e)}")
                    return CustomsCalculationResponse(
                        success=False,
                        error=f"TKS.ru request error: {str(e)}",
                        meta={"step": "tks_request", "request_exception": True},
                    )

            # Validate HTML content
            if not html_content or len(html_content) < 100:
                logger.error(
                    f"Invalid HTML response: {len(html_content) if html_content else 0} bytes"
                )
                return CustomsCalculationResponse(
                    success=False,
                    error="Empty or invalid HTML response from TKS.ru",
                    meta={
                        "step": "response_validation",
                        "content_length": len(html_content) if html_content else 0,
                        "content_preview": html_content[:100] if html_content else None,
                    },
                )

            # Check for CAPTCHA error in response
            if (
                "На форму расчёта установлена CAPTCHA" in html_content
                or "captcha" in html_content.lower()
            ):
                logger.error(
                    "❌ CAPTCHA error detected in response - invalidating cache"
                )

                # Invalidate all cached tokens as they're likely expired
                self._invalidate_all_tokens()

                # Save HTML for debugging (only in development/debug mode)
                if os.getenv("DEBUG", "").lower() == "true":
                    with open("debug_captcha_error.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    logger.info(
                        "Saved CAPTCHA error response to debug_captcha_error.html"
                    )

                return CustomsCalculationResponse(
                    success=False,
                    error="CAPTCHA validation failed - tokens have been invalidated",
                    meta={
                        "step": "captcha_validation",
                        "response_preview": (
                            html_content[:300] if html_content else None
                        ),
                        "captcha_token_length": len(captcha_solution),
                        "cache_invalidated": True,
                        "recommendation": "Try again - new CAPTCHA will be solved",
                    },
                )

            # Parse response
            logger.info("Parsing TKS.ru response...")
            original_request_dict = request.model_dump()
            parse_result = self.parser.parse_customs_calculation(
                html_content, original_request_dict
            )

            if not parse_result.get("success"):
                parse_error = parse_result.get("error", "Unknown parse error")
                logger.error(f"Parse failed: {parse_error}")
                logger.error(f"HTML preview: {html_content[:300]}...")

                return CustomsCalculationResponse(
                    success=False,
                    error=f"Failed to parse TKS.ru response: {parse_error}",
                    meta={
                        "step": "response_parsing",
                        "parse_meta": parse_result.get("meta", {}),
                        "response_preview": (
                            html_content[:500] if html_content else None
                        ),
                        "response_size": len(html_content),
                        "captcha_solution_length": len(captcha_solution),
                    },
                )

            logger.info("✅ TKS.ru calculation successful")
            return CustomsCalculationResponse(
                success=True,
                result=parse_result["result"],
                meta={
                    "step": "completed",
                    "parse_meta": parse_result.get("meta", {}),
                    "request_url": url[:100] + "...",
                    "captcha_used": True,
                    "response_size": len(html_content),
                },
            )

        except Exception as e:
            logger.error(
                f"TKS.ru calculation request failed with exception: {str(e)}",
                exc_info=True,
            )
            return CustomsCalculationResponse(
                success=False,
                error=f"Calculation request failed: {str(e)}",
                meta={
                    "step": "request_error",
                    "exception_type": type(e).__name__,
                    "exception_details": str(e),
                },
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

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the CAPTCHA cache"""
        with self.cache_lock:
            active_tokens = len([t for t in self.captcha_cache if not t.is_expired])
            total_tokens = len(self.captcha_cache)

        return {
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "tokens_generated": self.stats["tokens_generated"],
            "avg_response_time": f"{self.stats['avg_response_time']:.1f}s",
            "active_tokens": active_tokens,
            "total_tokens": total_tokens,
            "cache_hit_rate": f"{(self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100:.1f}%",
        }

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get detailed optimization status"""
        return {
            "optimization_enabled": True,
            "background_solver_running": self.background_task_running,
            "cache_configuration": {
                "min_cached_tokens": self.min_cached_tokens,
                "max_cached_tokens": self.max_cached_tokens,
                "token_expiry_minutes": 5,
                "max_uses_per_token": 3,
            },
            "performance_improvement": "Up to 90% faster (< 2s vs 17s)",
            "cache_stats": self.get_cache_stats(),
        }
