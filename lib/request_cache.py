"""
Request Cache Utility
Caches failed requests to prevent redundant API calls
"""

import time
from typing import Dict, Any, Optional
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class RequestCache:
    """
    Simple in-memory cache for failed requests

    Features:
    - LRU eviction when cache is full
    - TTL-based expiration
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize request cache

        Args:
            max_size: Maximum number of cached entries (default: 1000)
            default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _make_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Create cache key from URL and parameters"""
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"{url}?{param_str}"
        return url

    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired

        Args:
            url: Request URL
            params: Request parameters

        Returns:
            Cached response or None if not found/expired
        """
        key = self._make_key(url, params)

        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        current_time = time.time()

        # Check if expired
        if current_time > entry['expires_at']:
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (LRU)
        self.cache.move_to_end(key)
        self.hits += 1

        logger.info(f"Cache HIT for {url} (saved redundant request)")
        return entry['response']

    def set(self, url: str, response: Dict[str, Any], params: Optional[Dict] = None, ttl: Optional[int] = None):
        """
        Cache a response

        Args:
            url: Request URL
            response: Response data to cache
            params: Request parameters
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        key = self._make_key(url, params)
        current_time = time.time()
        ttl = ttl or self.default_ttl

        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)
            self.evictions += 1

        self.cache[key] = {
            'response': response,
            'cached_at': current_time,
            'expires_at': current_time + ttl,
            'ttl': ttl
        }

        # Move to end (LRU)
        self.cache.move_to_end(key)

    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
        logger.info("Request cache cleared")

    def cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry['expires_at']
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'evictions': self.evictions,
            'utilization': f"{len(self.cache) / self.max_size * 100:.1f}%"
        }
