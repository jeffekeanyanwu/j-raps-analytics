import redis
import json
from functools import wraps
from datetime import timedelta
from typing import Any, Optional
import polars as pl
import os


class RedisCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
            # Get Redis URL from environment or use default
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            cls._instance.redis = redis.from_url(redis_url)
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, expire_in: int = 300):
        """Set value in cache with expiration"""
        try:
            # Convert Polars DataFrame to dict for JSON serialization
            if isinstance(value, pl.DataFrame):
                value = value.to_dict(as_series=False)

            self.redis.setex(
                key,
                timedelta(seconds=expire_in),
                json.dumps(value)
            )
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.redis.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")


def cache_decorator(expire_in: int = 300):
    """Decorator to cache function results"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = RedisCache()

            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                # Convert back to Polars DataFrame if necessary
                if isinstance(result, dict) and all(isinstance(v, list) for v in result.values()):
                    return pl.DataFrame(result)
                return result

            # If not in cache, call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, expire_in)
            return result

        return wrapper

    return decorator
