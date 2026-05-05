import time
from typing import Dict, Any, Optional

class SimpleCache:
    """
    A simple thread-safe (in the context of asyncio) in-memory cache with TTL.
    """
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        if time.time() > item["expires_at"]:
            del self._cache[key]
            return None
        
        return item["data"]

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        expiry = ttl if ttl is not None else self.default_ttl
        self._cache[key] = {
            "data": data,
            "expires_at": time.time() + expiry
        }

    def clear(self):
        self._cache.clear()

# Global cache instance
query_cache = SimpleCache(default_ttl=300)
