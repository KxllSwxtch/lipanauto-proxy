import requests
import asyncio
import random
import time
from typing import Dict, List, Optional, Union
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Encar Advanced Proxy", version="2.0")

# CORS — разрешаем все origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация residential прокси от iproyal
IPROYAL_PROXY_CONFIGS = [
    {
        "name": "Korea Residential",
        "proxy": "geo.iproyal.com:12321",
        "auth": "oGKgjVaIooWADkOR:O8J73QYtjYWgQj4m_country-kr",
        "location": "South Korea",
    },
    {
        "name": "Japan and Korea Residential",
        "proxy": "geo.iproyal.com:12321",
        "auth": "oGKgjVaIooWADkOR:O8J73QYtjYWgQj4m_country-jp,kr",
        "location": "Japan and South Korea",
    },
]


def get_proxy_config(proxy_info):
    """Формирует конфигурацию прокси для requests"""
    proxy_url = f"http://{proxy_info['auth']}@{proxy_info['proxy']}"
    return {"http": proxy_url, "https": proxy_url}


# Расширенный набор User-Agent для ротации
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
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
        self.current_proxy_index = 0
        self.request_count = 0
        self.last_request_time = 0
        self.session_request_count = 0  # Счетчик для текущей сессии

        # Создаем первую сессию
        self._create_fresh_session()

    def _create_fresh_session(self):
        """Создает новую чистую сессию"""
        if hasattr(self, "session"):
            self.session.close()  # Закрываем старую сессию

        self.session = requests.Session()
        self.session_request_count = 0

        # Базовая конфигурация сессии
        self.session.timeout = (10, 30)  # connect timeout, read timeout
        self.session.max_redirects = 3

        # Устанавливаем прокси для новой сессии
        self._rotate_proxy()

        logger.info("Created fresh session - cleared all cookies and connections")

    def _get_dynamic_headers(self) -> Dict[str, str]:
        """Генерируем динамические заголовки с ротацией"""
        headers = BASE_HEADERS.copy()

        # Ротация User-Agent
        headers["user-agent"] = random.choice(USER_AGENTS)

        # Динамический sec-ch-ua на основе выбранного UA
        if "Chrome/137" in headers["user-agent"]:
            headers["sec-ch-ua"] = (
                '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"'
            )
        elif "Chrome/136" in headers["user-agent"]:
            headers["sec-ch-ua"] = (
                '"Google Chrome";v="136", "Chromium";v="136", "Not/A)Brand";v="24"'
            )

        return headers

    def _rotate_proxy(self):
        """Ротация residential прокси"""
        if IPROYAL_PROXY_CONFIGS:
            proxy_info = IPROYAL_PROXY_CONFIGS[
                self.current_proxy_index % len(IPROYAL_PROXY_CONFIGS)
            ]
            proxy_config = get_proxy_config(proxy_info)
            self.session.proxies = proxy_config
            self.current_proxy_index += 1
            logger.info(f"Switched to {proxy_info['name']} ({proxy_info['location']})")
            logger.info(f"Proxy: {proxy_info['proxy']}")

    def _rate_limit(self):
        """Простая защита от rate limiting"""
        current_time = time.time()
        if current_time - self.last_request_time < 0.5:  # Минимум 500ms между запросами
            time.sleep(0.5 - (current_time - self.last_request_time))
        self.last_request_time = time.time()

        # Каждые 20 запросов - ротация прокси для избежания rate limits
        if self.request_count % 20 == 0 and self.request_count > 0:
            self._rotate_proxy()

        # Каждые 50 запросов - создаем новую сессию для избежания блокировок
        if self.session_request_count >= 50:
            logger.info("Session refresh: 50 requests reached")
            self._create_fresh_session()

        self.request_count += 1
        self.session_request_count += 1

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
                elif response.status_code == 407:
                    logger.warning("Proxy authentication failed - rotating proxy")
                    self._rotate_proxy()
                    continue
                elif response.status_code == 403:
                    logger.warning(
                        "403 Forbidden - session blocked, creating fresh session"
                    )
                    self._create_fresh_session()
                    await asyncio.sleep(2**attempt)  # Exponential backoff
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
                logger.error(f"Proxy error: {str(e)} - rotating proxy")
                self._rotate_proxy()
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Proxy error: {str(e)}",
                        "url": url,
                    }
                await asyncio.sleep(1)
                continue

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {str(e)} - rotating proxy")
                self._rotate_proxy()
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Connection error: {str(e)}",
                        "url": url,
                    }
                await asyncio.sleep(2)
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


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    current_proxy_info = None
    if IPROYAL_PROXY_CONFIGS:
        current_index = (proxy_client.current_proxy_index - 1) % len(
            IPROYAL_PROXY_CONFIGS
        )
        current_proxy_info = IPROYAL_PROXY_CONFIGS[current_index]

    return {
        "status": "healthy",
        "proxy_client": {
            "request_count": proxy_client.request_count,
            "session_request_count": proxy_client.session_request_count,
            "session_health": (
                "Fresh" if proxy_client.session_request_count < 40 else "Aging"
            ),
            "current_proxy": (
                current_proxy_info["name"] if current_proxy_info else "None"
            ),
            "current_location": (
                current_proxy_info["location"] if current_proxy_info else "Direct"
            ),
            "available_proxies": len(IPROYAL_PROXY_CONFIGS),
            "proxy_type": "Residential (iproyal)",
        },
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Encar Advanced Proxy",
        "version": "2.0",
        "endpoints": ["/api/catalog", "/api/nav", "/health"],
        "features": [
            "User-Agent rotation",
            "Residential proxy rotation (Korea)",
            "Rate limiting protection",
            "Retry logic with exponential backoff",
            "Advanced error handling",
            "Proxy authentication & rotation",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
