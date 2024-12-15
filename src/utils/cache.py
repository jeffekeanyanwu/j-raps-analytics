import redis
import polars as pl
import json
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Optional
import time


class RedisCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize Redis connection and caching systems"""
        self.redis = redis.Redis(host='redis', port=6379, decode_responses=True)
        self._memory_cache = {}
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'api_calls': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with stats tracking"""
        # Try memory cache first
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry > time.time():
                self._cache_stats['hits'] += 1
                return value
            else:
                del self._memory_cache[key]

        # Try Redis cache
        try:
            value = self.redis.get(key)
            if value:
                self._cache_stats['hits'] += 1
                # Store in memory cache for faster subsequent access
                data = json.loads(value)
                if isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
                    data = pl.DataFrame(data)
                self._memory_cache[key] = (data, time.time() + 300)  # 5-minute memory cache
                return data
        except Exception as e:
            print(f"Cache error: {e}")

        self._cache_stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, expire_in: int = 3600):
        """Set value in cache with stats tracking"""
        try:
            if isinstance(value, pl.DataFrame):
                value = value.to_dict(as_series=False)

            # Store in both Redis and memory cache
            self.redis.setex(
                key,
                timedelta(seconds=expire_in),
                json.dumps(value)
            )
            self._memory_cache[key] = (value, time.time() + expire_in)
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.redis.delete(key)
            if key in self._memory_cache:
                del self._memory_cache[key]
        except Exception as e:
            print(f"Cache delete error: {e}")

    def get_stats(self) -> dict:
        """Get cache performance statistics"""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (self._cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'cache_hits': self._cache_stats['hits'],
            'cache_misses': self._cache_stats['misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'api_calls': self._cache_stats['api_calls'],
            'memory_cache_size': len(self._memory_cache),
            'timestamp': datetime.now().isoformat()
        }

    def track_api_call(self):
        """Track API call for monitoring"""
        self._cache_stats['api_calls'] += 1

    def clear(self):
        """Clear all caches"""
        try:
            self.redis.flushall()
            self._memory_cache.clear()
            self._cache_stats = {
                'hits': 0,
                'misses': 0,
                'api_calls': 0
            }
        except Exception as e:
            print(f"Cache clear error: {e}")


def cache_decorator(expire_in: int = 3600):
    """Enhanced cache decorator with performance tracking"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = RedisCache()

            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result

            # If not in cache, call function and cache result
            cache.track_api_call()
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Log execution time for monitoring
            print(f"API call to {func.__name__} took {execution_time:.2f} seconds")

            if result is not None:
                cache.set(key, result, expire_in)
            return result

        return wrapper

    return decorator
