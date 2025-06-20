import requests
import asyncio
import random
import time
from typing import Dict, List, Optional, Union, Annotated
from fastapi import FastAPI, Query, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uuid

# New imports for bike functionality
from schemas.bikes import BikeSearchParams, BikeSearchResponse, BikeDetailResponse
from schemas.bike_filters import (
    FilterLevel,
    FilterInfo,
    FilterSearchParams,
    BikeSearchFilters,
)
from services.bike_service import BikeService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LiPan Auto Proxy", version="1.0")

# CORS — разрешаем все origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация residential прокси
PROXY_CONFIGS = [
    {
        "name": "Decodo Proxy",
        "proxy": "kr.decodo.com:10000",
        "auth": "sp8oh1di2c:ToD5yssi98gmSmX9=j",
        "location": "South Korea",
        "provider": "decodo",
    },
]


def get_proxy_config(proxy_info):
    """Формирует конфигурацию прокси для requests"""
    proxy_url = f"http://{proxy_info['auth']}@{proxy_info['proxy']}"
    return {"http": proxy_url, "https": proxy_url}


# Расширенный набор User-Agent для ротации
USER_AGENTS = [
    # Desktop Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.78 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.61 Safari/537.36",
    # Desktop Firefox
    "Mozilla/5.0 (Windows NT 10.0; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.113 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.78 Mobile Safari/537.36",
]


# Базовые заголовки
BASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en,ru;q=0.9,en-CA;q=0.8,la;q=0.7,fr;q=0.6,ko;q=0.5",
    "origin": "https://cars.prokorea.trading",
    "priority": "u=1, i",
    "referer": "https://cars.prokorea.trading/",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}


class EncarProxyClient:
    """Продвинутый клиент для обхода защиты Encar API с residential прокси"""

    def __init__(self):
        self.session = requests.Session()
        self.current_proxy_index = 0
        self.request_count = 0
        self.last_request_time = 0
        self.session_rotation_count = 0

        # Базовая конфигурация сессии
        self.session.timeout = (10, 30)  # connect timeout, read timeout
        self.session.max_redirects = 3

        # Устанавливаем первый residential прокси
        self._rotate_proxy()

    def _get_dynamic_headers(self) -> Dict[str, str]:
        ua = random.choice(USER_AGENTS)

        # Подбираем headers под User-Agent
        headers = BASE_HEADERS.copy()
        headers["user-agent"] = ua

        # Chrome версия (нужно для sec-ch-ua)
        if "Chrome/125" in ua:
            headers["sec-ch-ua"] = (
                '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"'
            )
        elif "Chrome/124" in ua:
            headers["sec-ch-ua"] = (
                '"Google Chrome";v="124", "Chromium";v="124", "Not.A/Brand";v="24"'
            )
        elif "Chrome/123" in ua:
            headers["sec-ch-ua"] = (
                '"Google Chrome";v="123", "Chromium";v="123", "Not.A/Brand";v="24"'
            )
        else:
            headers["sec-ch-ua"] = '"Chromium";v="125", "Not.A/Brand";v="24"'

        # Платформа и мобильность
        if "Android" in ua:
            headers["sec-ch-ua-platform"] = '"Android"'
            headers["sec-ch-ua-mobile"] = "?1"
        elif "iPhone" in ua:
            headers["sec-ch-ua-platform"] = '"iOS"'
            headers["sec-ch-ua-mobile"] = "?1"
        elif "Macintosh" in ua:
            headers["sec-ch-ua-platform"] = '"macOS"'
            headers["sec-ch-ua-mobile"] = "?0"
        elif "Windows" in ua:
            headers["sec-ch-ua-platform"] = '"Windows"'
            headers["sec-ch-ua-mobile"] = "?0"
        else:
            headers["sec-ch-ua-platform"] = '"Unknown"'
            headers["sec-ch-ua-mobile"] = "?0"

        return headers

    def _rotate_proxy(self):
        """Ротация residential прокси"""
        if PROXY_CONFIGS:
            proxy_info = PROXY_CONFIGS[self.current_proxy_index % len(PROXY_CONFIGS)]
            proxy_config = get_proxy_config(proxy_info)
            self.session.proxies = proxy_config
            self.current_proxy_index += 1
            logger.info(
                f"Switched to {proxy_info['name']} ({proxy_info['location']}) via {proxy_info['provider']}"
            )
            logger.info(f"Proxy: {proxy_info['proxy']}")

    def _create_new_session(self):
        """Создает новую сессию для полного сброса IP"""
        logger.info("Creating new session to reset IP address...")

        # Закрываем старую сессию
        self.session.close()

        # Создаем новую сессию
        self.session = requests.Session()
        self.session.timeout = (10, 30)
        self.session.max_redirects = 3

        # Принудительно меняем прокси на следующий
        self._rotate_proxy()
        self.session_rotation_count += 1

        logger.info(f"New session created (rotation #{self.session_rotation_count})")

    def _rate_limit(self):
        """Простая защита от rate limiting"""
        current_time = time.time()
        if current_time - self.last_request_time < 0.5:  # Минимум 500ms между запросами
            time.sleep(0.5 - (current_time - self.last_request_time))
        self.last_request_time = time.time()

        # Каждые 15 запросов - ротация прокси для избежания rate limits
        if self.request_count % 15 == 0 and self.request_count > 0:
            self._rotate_proxy()

        # Каждые 50 запросов - полная ротация сессии для профилактики
        if self.request_count % 50 == 0 and self.request_count > 0:
            logger.info("Preventive session rotation")
            self._create_new_session()

        self.request_count += 1

    async def make_request(self, url: str, max_retries: int = 3) -> Dict:
        """Выполняет запрос с retry логикой и обходом защиты"""

        for attempt in range(max_retries):
            try:
                # Rate limiting
                self._rate_limit()

                # Получаем свежие заголовки
                headers = self._get_dynamic_headers()

                logger.info(f"Attempt {attempt + 1}/{max_retries}: {url}")
                logger.info(f"Using UA: {headers['user-agent'][:50]}...")

                # Выполняем запрос в отдельном потоке
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.session.get(url, headers=headers)
                )

                logger.info(f"Response status: {response.status_code}")

                if response.status_code == 200:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "text": response.text,
                        "headers": dict(response.headers),
                        "url": url,
                        "attempt": attempt + 1,
                    }
                elif response.status_code == 403:
                    logger.warning(f"IP blacklisted (403) - creating new session")
                    self._create_new_session()
                    # Дополнительная пауза при блокировке IP
                    await asyncio.sleep(3 + random.uniform(0, 2))
                    continue
                elif response.status_code == 407:
                    logger.warning("Proxy authentication failed - rotating proxy")
                    self._rotate_proxy()
                    continue
                elif response.status_code in [429, 503]:
                    logger.warning(
                        f"Rate limited ({response.status_code}) - waiting and rotating proxy"
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    self._rotate_proxy()
                    continue
                else:
                    logger.warning(
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "text": response.text,
                        "error": f"HTTP {response.status_code}",
                        "url": url,
                        "attempt": attempt + 1,
                    }

            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error: {str(e)}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": f"Timeout: {str(e)}", "url": url}
                await asyncio.sleep(1)
                continue

            except requests.exceptions.ProxyError as e:
                logger.error(f"Proxy error: {str(e)} - creating new session")
                self._create_new_session()
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Proxy error: {str(e)}",
                        "url": url,
                    }
                await asyncio.sleep(2)
                continue

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {str(e)} - creating new session")
                self._create_new_session()
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Connection error: {str(e)}",
                        "url": url,
                    }
                await asyncio.sleep(3)
                continue

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Unexpected error: {str(e)}",
                        "url": url,
                    }
                await asyncio.sleep(1)
                continue

        return {"success": False, "error": "Max retries exceeded", "url": url}


# Глобальный клиент
proxy_client = EncarProxyClient()

# Initialize bike service
bike_service = BikeService(proxy_client)


@app.on_event("shutdown")
async def shutdown_event():
    """Корректное закрытие сессий при выключении сервера"""
    logger.info("Shutting down server...")
    if hasattr(proxy_client, "session"):
        proxy_client.session.close()
    logger.info("Sessions closed")


async def handle_api_request(endpoint: str, params: Dict[str, str]) -> JSONResponse:
    """Универсальный обработчик API запросов"""

    # Кодируем параметры
    encoded_params = {}
    for key, value in params.items():
        if isinstance(value, str):
            encoded_params[key] = value.replace("|", "%7C")
        else:
            encoded_params[key] = value

    # Формируем URL
    param_string = "&".join([f"{k}={v}" for k, v in encoded_params.items()])
    primary_url = f"https://encar-proxy.habsida.net/api/{endpoint}?{param_string}"

    # Backup URL с исходными параметрами
    backup_param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    backup_url = f"https://encar-proxy.habsida.net/api/{endpoint}?{backup_param_string}"

    attempts = []

    # Пробуем основной URL
    response_data = await proxy_client.make_request(primary_url)
    attempts.append(
        {
            "url": primary_url,
            "success": response_data.get("success", False),
            "status_code": response_data.get("status_code"),
            "attempt": response_data.get("attempt", 1),
        }
    )

    # Если не удалось, пробуем backup
    if not response_data.get("success") or response_data.get("status_code") != 200:
        logger.info("Primary URL failed, trying backup...")
        response_data = await proxy_client.make_request(backup_url)
        attempts.append(
            {
                "url": backup_url,
                "success": response_data.get("success", False),
                "status_code": response_data.get("status_code"),
                "attempt": response_data.get("attempt", 1),
            }
        )

    if not response_data.get("success"):
        return JSONResponse(
            status_code=502,
            content={
                "error": f"API request failed: {response_data.get('error')}",
                "attempts": attempts,
                "debug": {"endpoint": endpoint, "params": params},
            },
        )

    status_code = response_data["status_code"]
    response_text = response_data["text"]

    if status_code != 200:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": f"API returned status {status_code}",
                "attempts": attempts,
                "preview": response_text[:500] if response_text else None,
            },
        )

    # Проверяем и парсим JSON
    try:
        if not response_text or response_text.strip() == "":
            return JSONResponse(
                status_code=502,
                content={"error": "Empty response from API", "attempts": attempts},
            )

        # Проверяем на HTML вместо JSON
        if response_text.strip().startswith(("<!DOCTYPE", "<html")):
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Received HTML instead of JSON",
                    "attempts": attempts,
                    "preview": response_text[:500],
                },
            )

        import json

        json_data = json.loads(response_text)

        # Добавляем мета-информацию
        if isinstance(json_data, dict):
            json_data["_meta"] = {
                "proxy_info": {
                    "attempts": len(attempts),
                    "successful_url": response_data["url"],
                    "response_size": len(response_text),
                }
            }

        return json_data

    except json.JSONDecodeError as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": f"JSON decode error: {str(e)}",
                "attempts": attempts,
                "preview": response_text[:500] if response_text else None,
            },
        )


@app.get("/api/catalog")
async def proxy_catalog(q: str = Query(...), sr: str = Query(...)):
    """Прокси для каталога автомобилей с продвинутым обходом защиты"""
    return await handle_api_request("catalog", {"count": "true", "q": q, "sr": sr})


@app.get("/api/nav")
async def proxy_nav(
    q: str = Query(...), inav: str = Query(...), count: str = Query(default="true")
):
    """Прокси для навигации с продвинутым обходом защиты"""
    return await handle_api_request("nav", {"count": count, "q": q, "inav": inav})


@app.get("/api/bikes", response_model=BikeSearchResponse)
async def get_bikes(
    ifnew: str = Query(default="N", description="Filter: N=Used, Y=New bikes"),
    gubun: Optional[str] = Query(
        default=None, description="Type: K=Korean, I=Imported"
    ),
    tab: Optional[str] = Query(
        default=None, description="Category: 2=Verified, 3=Premium, 4=Quick sale"
    ),
    page: Optional[int] = Query(default=1, description="Page number"),
    sort: Optional[str] = Query(default=None, description="Sort order"),
):
    """
    Get bike listings from bobaedream.co.kr with advanced proxy protection

    - **ifnew**: N for used bikes, Y for new bikes
    - **gubun**: K for Korean bikes, I for imported bikes
    - **tab**: 2 for verified, 3 for premium, 4 for quick sale
    - **page**: Page number for pagination
    - **sort**: Sort order for results
    """

    try:
        # Create search parameters
        search_params = BikeSearchParams(
            ifnew=ifnew, gubun=gubun, tab=tab, page=page, sort=sort
        )

        # Execute search using service layer
        result = await bike_service.search_bikes(search_params)

        if not result.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch bike listings: {result.meta.get('error', 'Unknown error')}",
            )

        return result

    except Exception as e:
        logger.error(f"Error in /api/bikes endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/{bike_id}", response_model=BikeDetailResponse)
async def get_bike_details(bike_id: str):
    """
    Get detailed information for a specific bike

    - **bike_id**: Unique bike identifier from listing
    """

    try:
        result = await bike_service.get_bike_details(bike_id)

        if not result.get("success"):
            error_detail = result.get("meta", {}).get("error", "Unknown error")
            raise HTTPException(
                status_code=404,
                detail=f"Bike not found or failed to fetch: {error_detail}",
            )

        # Ensure proper serialization of the BikeDetail object
        bike_detail = result.get("bike")
        if bike_detail and hasattr(bike_detail, "model_dump"):
            # Convert BikeDetail to dict using Pydantic V2 method
            bike_dict = bike_detail.model_dump()

            # Ensure proper serialization for Pydantic V2 compatibility

            result["bike"] = bike_dict

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bike {bike_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/filters/info", response_model=FilterInfo)
async def get_bike_filters():
    """
    Get comprehensive information about available bike search filters

    Returns hierarchical filter data including:
    - Categories (스쿠터, 레플리카, 네이키드, etc.)
    - Manufacturers (혼다, 야마하, 대림, etc.)
    - Popular filter combinations
    """
    try:
        result = await bike_service.get_filter_info()
        return result
    except Exception as e:
        logger.error(f"Error getting filter info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/filters/categories", response_model=FilterLevel)
async def get_bike_categories():
    """
    Get bike categories (스쿠터, 레플리카, 네이키드, etc.)

    First level of filter hierarchy - bike types
    """
    try:
        result = await bike_service.get_categories()
        if not result.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch categories: {result.meta.get('error', 'Unknown error')}",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/filters/manufacturers", response_model=FilterLevel)
async def get_bike_manufacturers():
    """
    Get bike manufacturers (혼다, 야마하, 대림, etc.)

    Second level of filter hierarchy - bike brands
    """
    try:
        result = await bike_service.get_manufacturers()
        if not result.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch manufacturers: {result.meta.get('error', 'Unknown error')}",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting manufacturers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/filters/models/{manufacturer_id}", response_model=FilterLevel)
async def get_bike_models(
    manufacturer_id: Annotated[
        str,
        Path(
            description="Manufacturer ID (e.g., '5' for Honda, '6' for Yamaha, '4' for BMW)",
            min_length=1,
            max_length=10,
            pattern=r"^\d+$",
        ),
    ],
):
    """
    Get bike models for specific manufacturer

    Third level of filter hierarchy - specific bike models

    - **manufacturer_id**: Manufacturer ID (e.g., "5" for Honda, "6" for Yamaha, "4" for BMW, "119" for Harley-Davidson)

    **Note**: Due to issues with the source API, this endpoint uses a combination of live data
    and static fallback mapping to ensure reliable results.
    """
    try:
        result = await bike_service.get_models(manufacturer_id)
        if not result.success and result.meta.get("data_source") != "static_mapping":
            logger.warning(
                f"Failed to fetch models for manufacturer {manufacturer_id}: {result.meta}"
            )
            # Still return the result even if it failed, as it contains useful error info

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting models for manufacturer {manufacturer_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/bikes/filters/suggestions")
async def get_filter_suggestions():
    """
    Get popular filter combinations and suggestions

    Returns common search patterns and popular filter combinations
    """
    return bike_service.get_filter_suggestions()


@app.post("/api/bikes/search", response_model=BikeSearchResponse)
async def search_bikes_with_filters(filters: BikeSearchFilters):
    """
    Advanced bike search with comprehensive filters

    Supports all available filter options including:
    - Category (ftype1): 1=스쿠터, 4=레플리카, 5=네이키드, etc.
    - Manufacturer (maker_no): 5=혼다, 6=야마하, 10=대림, etc.
    - Model variations (level_no2): Multi-select model options
    - Price range (price1, price2): In 만원 (10,000 KRW)
    - Year range (buy_year1_1, buy_year2_1)
    - Engine size (cc): Displacement filter
    - Location (addr_1, addr_2): Province and district
    - And many more advanced options...
    """
    try:
        result = await bike_service.search_bikes_with_filters(filters)

        if not result.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to search bikes with filters: {result.meta.get('error', 'Unknown error')}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in filtered bike search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    current_proxy_info = None
    if PROXY_CONFIGS:
        current_index = (proxy_client.current_proxy_index - 1) % len(PROXY_CONFIGS)
        current_proxy_info = PROXY_CONFIGS[current_index]

    # Собираем информацию о всех провайдерах
    providers = {}
    for config in PROXY_CONFIGS:
        provider = config["provider"]
        if provider not in providers:
            providers[provider] = 0
        providers[provider] += 1

    return {
        "status": "healthy",
        "proxy_client": {
            "request_count": proxy_client.request_count,
            "session_rotations": proxy_client.session_rotation_count,
            "current_proxy": (
                current_proxy_info["name"] if current_proxy_info else "None"
            ),
            "current_provider": (
                current_proxy_info["provider"] if current_proxy_info else "None"
            ),
            "current_location": (
                current_proxy_info["location"] if current_proxy_info else "Direct"
            ),
            "available_proxies": len(PROXY_CONFIGS),
            "providers": providers,
            "proxy_type": "Residential multi-provider with session rotation",
        },
        "services": {
            "encar_api": "✅ Active (cars)",
            "bobaedream_bikes": "✅ Active (motorcycles)",
            "parser_engine": "BeautifulSoup4 + lxml",
        },
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Multi-Platform Vehicle Proxy API",
        "version": "3.1",
        "endpoints": {
            "cars": ["/api/catalog", "/api/nav"],
            "bikes": [
                "/api/bikes",
                "/api/bikes/{bike_id}",
                "/api/bikes/filters/info",
                "/api/bikes/filters/categories",
                "/api/bikes/filters/manufacturers",
                "/api/bikes/filters/models/{manufacturer_id}",
                "/api/bikes/filters/status",
                "/api/bikes/filters/suggestions",
                "/api/bikes/search",
            ],
            "system": ["/health"],
        },
        "features": [
            "User-Agent rotation",
            "Multi-provider residential proxy rotation (Korea)",
            "Automatic session rotation on 403 errors",
            "Rate limiting protection",
            "Retry logic with exponential backoff",
            "Advanced error handling",
            "Proxy authentication & rotation",
            "BeautifulSoup4 + lxml parsing",
            "Korean site optimization",
            "Static fallback for broken API endpoints",
            "Enhanced query parameter validation",
        ],
        "platforms": {
            "encar.com": "Car listings and navigation",
            "bobaedream.co.kr": "Motorcycle listings and details",
        },
        "providers": [config["provider"] for config in PROXY_CONFIGS],
        "total_proxies": len(PROXY_CONFIGS),
        "api_status": {
            "bikes_core": "✅ Fully operational",
            "bikes_filters": "⚠️ Partial (with static fallback)",
            "cars_core": "✅ Fully operational",
        },
    }


@app.get("/api/bikes/filters/status")
async def get_filters_status():
    """
    Get status information about bike filters and data sources

    Returns information about which filter endpoints are working properly
    and which ones use fallback data due to API issues.
    """
    try:
        # Test a few key manufacturers to check API status
        test_manufacturers = ["5", "6", "4", "119"]  # Honda, Yamaha, BMW, Harley
        api_status = {}

        for manufacturer_id in test_manufacturers:
            try:
                result = await bike_service.get_models(manufacturer_id)
                api_status[manufacturer_id] = {
                    "success": result.success,
                    "data_source": result.meta.get("data_source", "unknown"),
                    "model_count": len(result.options),
                    "manufacturer_name": {
                        "5": "Honda",
                        "6": "Yamaha",
                        "4": "BMW",
                        "119": "Harley-Davidson",
                    }.get(manufacturer_id, "Unknown"),
                }
            except Exception as e:
                api_status[manufacturer_id] = {
                    "success": False,
                    "error": str(e),
                    "data_source": "error",
                }

        return {
            "filter_endpoints": {
                "categories": "✅ Working (API)",
                "manufacturers": "✅ Working (API)",
                "models": "⚠️ Partial (API + Static Fallback)",
                "search": "✅ Working (API)",
            },
            "api_issues": {
                "models_endpoint": "bobaedream.co.kr API returns incorrect manufacturer-model mappings",
                "solution": "Using static fallback mapping for popular models",
            },
            "manufacturer_status": api_status,
            "static_fallback_available": list(
                bike_service.filters_service.POPULAR_MODELS_MAPPING.keys()
            ),
            "recommendations": {
                "frontend": [
                    "Use categories and manufacturers filters normally",
                    "Models filter works but may show static data for some manufacturers",
                    "Consider hiding model filter if only live API data is required",
                    "Use search endpoint for advanced filtering",
                ]
            },
        }

    except Exception as e:
        logger.error(f"Error getting filter status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
