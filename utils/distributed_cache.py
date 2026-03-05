"""
Distributed cache with Redis support.
Provides optional Redis backend for distributed caching.
Can fallback to in-memory cache if Redis is not available.
"""

import json
import zlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


class CacheBackend:
    """Base class for cache backends."""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError
    
    def clear(self) -> bool:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """In-memory cache for single-process usage."""
    
    def __init__(self, maxsize: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._maxsize = maxsize
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        cached = self._cache[key]
        
        if datetime.now() > cached['expires_at']:
            del self._cache[key]
            return None
        
        return cached['value']
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if len(self._cache) >= self._maxsize:
            self._evict_oldest()
        
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'created_at': datetime.now()
        }
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        return key in self._cache
    
    def clear(self) -> bool:
        self._cache.clear()
        return True
    
    def _evict_oldest(self):
        """Evict oldest cache entries."""
        if not self._cache:
            return
        
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k]['created_at']
        )
        
        for key in sorted_keys[:self._maxsize // 10]:
            del self._cache[key]


class RedisCache(CacheBackend):
    """Redis-based distributed cache."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 prefix: str = 'niklaus:'):
        
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not installed. Install with: pip install redis")
        
        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False
        )
        self._prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self._prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        prefixed_key = self._make_key(key)
        value = self._client.get(prefixed_key)
        
        if value is None:
            return None
        
        try:
            decompressed = zlib.decompress(value)
            return json.loads(decompressed.decode('utf-8'))
        except (zlib.error, json.JSONDecodeError):
            try:
                return json.loads(value.decode('utf-8'))
            except:
                return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        prefixed_key = self._make_key(key)
        
        try:
            serialized = json.dumps(value)
            compressed = zlib.compress(serialized.encode('utf-8'))
            
            return self._client.setex(prefixed_key, ttl, compressed)
        except:
            try:
                serialized = json.dumps(value)
                return self._client.setex(prefixed_key, ttl, serialized.encode('utf-8'))
            except:
                return False
    
    def delete(self, key: str) -> bool:
        prefixed_key = self._make_key(key)
        return bool(self._client.delete(prefixed_key))
    
    def exists(self, key: str) -> bool:
        prefixed_key = self._make_key(key)
        return bool(self._client.exists(prefixed_key))
    
    def clear(self) -> bool:
        """Clear all cache keys with prefix."""
        keys = self._client.keys(f"{self._prefix}*")
        if keys:
            return bool(self._client.delete(*keys))
        return True


class DistributedCache:
    """
    Distributed cache with automatic fallback.
    Uses Redis if available, otherwise falls back to in-memory cache.
    """
    
    def __init__(self, redis_host: str = None, redis_port: int = 6379,
                 redis_password: str = None, fallback_to_memory: bool = True):
        
        self._backend: CacheBackend = None
        self._is_redis = False
        
        if redis_host and REDIS_AVAILABLE:
            try:
                self._backend = RedisCache(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password
                )
                self._is_redis = True
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                if fallback_to_memory:
                    self._backend = InMemoryCache()
                    logger.info("Fallback to in-memory cache")
        elif fallback_to_memory:
            self._backend = InMemoryCache()
            logger.info("Using in-memory cache")
        else:
            raise RuntimeError("No cache backend available")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            return self._backend.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        try:
            return self._backend.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return self._backend.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return self._backend.exists(key)
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache."""
        try:
            return self._backend.clear()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'backend': 'redis' if self._is_redis else 'memory',
            'is_redis': self._is_redis
        }
        
        if isinstance(self._backend, InMemoryCache):
            stats['size'] = len(self._backend._cache)
            stats['maxsize'] = self._backend._maxsize
        elif isinstance(self._backend, RedisCache):
            info = self._backend._client.info('memory')
            stats['used_memory'] = info.get('used_memory', 0)
            stats['used_memory_human'] = info.get('used_memory_human', '0B')
            
            dbsize = self._backend._client.dbsize()
            stats['key_count'] = dbsize
        
        return stats
    
    @property
    def is_redis(self) -> bool:
        """Check if using Redis backend."""
        return self._is_redis


class CacheWarming:
    """
    Cache warming for frequently accessed data.
    Pre-loads data into cache to improve performance.
    """
    
    def __init__(self, cache: DistributedCache):
        self._cache = cache
        self._warming_functions: Dict[str, callable] = {}
    
    def register_warming_function(self, key_pattern: str, func: callable, ttl: int = 300):
        """
        Register a function to warm cache.
        
        Args:
            key_pattern: Pattern for cache keys (e.g., 'user_*_submissions')
            func: Function that returns data to cache
            ttl: Cache TTL in seconds
        """
        self._warming_functions[key_pattern] = {
            'function': func,
            'ttl': ttl
        }
    
    def warm_cache(self, keys: list = None):
        """
        Warm cache for specified keys or all registered patterns.
        
        Args:
            keys: Specific keys to warm (optional)
        """
        if keys:
            for key in keys:
                self._warm_key(key)
        else:
            for key_pattern in self._warming_functions:
                self._warm_pattern(key_pattern)
    
    def _warm_key(self, key: str):
        """Warm a single cache key."""
        for pattern, config in self._warming_functions.items():
            if self._matches_pattern(key, pattern):
                try:
                    data = config['function']()
                    self._cache.set(key, data, config['ttl'])
                    logger.debug(f"Warmed cache key: {key}")
                except Exception as e:
                    logger.error(f"Cache warming failed for {key}: {e}")
    
    def _warm_pattern(self, pattern: str):
        """Warm all keys matching pattern."""
        config = self._warming_functions.get(pattern)
        if config:
            try:
                data = config['function']()
                cache_key = pattern.replace('*', 'all')
                self._cache.set(cache_key, data, config['ttl'])
                logger.debug(f"Warmed cache pattern: {pattern}")
            except Exception as e:
                logger.error(f"Cache warming failed for pattern {pattern}: {e}")
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)


class SmartCacheInvalidation:
    """
    Intelligent cache invalidation.
    Invalidates related cache entries based on dependencies.
    """
    
    def __init__(self, cache: DistributedCache):
        self._cache = cache
        self._dependencies: Dict[str, list] = {}
    
    def add_dependency(self, key: str, depends_on: list):
        """
        Add cache dependency.
        
        Args:
            key: Cache key
            depends_on: List of events that should invalidate this key
        """
        for event in depends_on:
            if event not in self._dependencies:
                self._dependencies[event] = []
            if key not in self._dependencies[event]:
                self._dependencies[event].append(key)
    
    def invalidate_on_event(self, event: str):
        """
        Invalidate all cache entries dependent on event.
        
        Args:
            event: Event name (e.g., 'user_123_update')
        """
        if event not in self._dependencies:
            return
        
        keys_to_invalidate = self._dependencies[event]
        
        for key in keys_to_invalidate:
            self._cache.delete(key)
            logger.debug(f"Invalidated cache key: {key} (event: {event})")
        
        del self._dependencies[event]
    
    def get_dependencies(self, key: str) -> list:
        """Get dependencies for a cache key."""
        events = []
        for event, keys in self._dependencies.items():
            if key in keys:
                events.append(event)
        return events


_global_cache: Optional[DistributedCache] = None


def get_distributed_cache(redis_host: str = None, redis_port: int = 6379,
                          redis_password: str = None) -> DistributedCache:
    """Get global distributed cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = DistributedCache(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password
        )
    return _global_cache


def init_redis_cache(host: str = 'localhost', port: int = 6379, 
                     password: str = None) -> DistributedCache:
    """
    Initialize Redis cache.
    
    Args:
        host: Redis host
        port: Redis port
        password: Redis password (optional)
        
    Returns:
        DistributedCache instance
    """
    global _global_cache
    _global_cache = DistributedCache(
        redis_host=host,
        redis_port=port,
        redis_password=password
    )
    return _global_cache