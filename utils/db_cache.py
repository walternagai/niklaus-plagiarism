"""
Database query cache with TTL support.
Implements intelligent caching for frequent database queries.
"""

import time
from typing import Any, Optional, Dict, List, Callable, Set
from functools import wraps
import hashlib
import json

try:
    import streamlit as st
except ImportError:
    st = None


class QueryCache:
    """
    LRU cache with TTL (Time-To-Live) for database queries.
    Provides query result caching with automatic expiration.
    """
    
    def __init__(self, maxsize: int = 256, default_ttl: float = 300):
        """
        Initialize query cache.
        
        Args:
            maxsize: Maximum number of queries to cache
            default_ttl: Default time-to-live in seconds (5 min)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._hit_count = 0
        self._miss_count = 0
    
    def _generate_key(self, query: str, params: tuple = ()) -> str:
        """Generate unique cache key from query and parameters."""
        params_str = json.dumps(params, sort_keys=True, default=str)
        combined = f"{query}:{params_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(query, params)
        
        if key not in self._cache:
            self._miss_count += 1
            return None
        
        cached = self._cache[key]
        
        if time.time() - cached['timestamp'] > cached['ttl']:
            del self._cache[key]
            self._miss_count += 1
            return None
        
        self._access_times[key] = time.time()
        self._hit_count += 1
        return cached['data']
    
    def set(self, query: str, params: tuple = (), data: Any = None, ttl: Optional[float] = None):
        """
        Cache query result with TTL.
        
        Args:
            query: SQL query string
            params: Query parameters
            data: Result data to cache
            ttl: Time-to-live (uses default if None)
        """
        if len(self._cache) >= self._maxsize:
            self._evict_lru()
        
        key = self._generate_key(query, params)
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl or self._default_ttl
        }
        self._access_times[key] = time.time()
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self.delete(lru_key)
    
    def delete(self, key: str):
        """Delete specific cached query."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def invalidate(self, query: str, params: tuple = ()):
        """Invalidate specific query cache."""
        key = self._generate_key(query, params)
        self.delete(key)
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all queries matching pattern."""
        keys_to_delete = [
            k for k in self._cache.keys()
            if pattern in k
        ]
        for key in keys_to_delete:
            self.delete(key)
    
    def clear(self):
        """Clear all cached queries."""
        self._cache.clear()
        self._access_times.clear()
        self._hit_count = 0
        self._miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'maxsize': self._maxsize,
            'hits': self._hit_count,
            'misses': self._miss_count,
            'hit_rate': hit_rate,
            'total_queries': total
        }


class SubmissionCache:
    """
    Specialized cache for submission queries.
    Manages submission history with intelligent invalidation.
    """
    
    def __init__(self, query_cache: QueryCache):
        self._cache = query_cache
        self._submissions_by_user: Dict[int, Set[str]] = {}
    
    def get_user_submissions(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict] = None
    ) -> Optional[List]:
        """
        Get cached submissions for user.
        
        Args:
            user_id: User ID
            offset: Pagination offset
            limit: Page size
            filters: Optional filters
            
        Returns:
            Cached submissions or None
        """
        cache_key = f"user_{user_id}_submissions_{offset}_{limit}"
        if filters:
            filter_str = json.dumps(filters, sort_keys=True)
            cache_key += f"_{hashlib.md5(filter_str.encode()).hexdigest()}"
        
        return self._cache.get(cache_key)
    
    def set_user_submissions(
        self,
        user_id: int,
        submissions: List,
        offset: int = 0,
        limit: int = 50,
        filters: Optional[Dict] = None,
        ttl: float = 60
    ):
        """
        Cache user submissions.
        
        Args:
            user_id: User ID
            submissions: Submission list
            offset: Pagination offset
            limit: Page size
            filters: Optional filters
            ttl: Cache TTL in seconds
        """
        cache_key = f"user_{user_id}_submissions_{offset}_{limit}"
        if filters:
            filter_str = json.dumps(filters, sort_keys=True)
            cache_key += f"_{hashlib.md5(filter_str.encode()).hexdigest()}"
        
        self._cache.set(cache_key, data=submissions, ttl=ttl)
        
        if user_id not in self._submissions_by_user:
            self._submissions_by_user[user_id] = set()
        self._submissions_by_user[user_id].add(cache_key)
    
    def get_submission_by_id(self, submission_id: int) -> Optional[Any]:
        """Get cached submission by ID."""
        return self._cache.get(f"submission_{submission_id}")
    
    def set_submission(self, submission: Any, ttl: float = 300):
        """Cache submission by ID."""
        self._cache.set(
            f"submission_{submission.id}",
            data=submission,
            ttl=ttl
        )
    
    def invalidate_user(self, user_id: int):
        """Invalidate all cached data for user."""
        if user_id in self._submissions_by_user:
            for cache_key in self._submissions_by_user[user_id]:
                self._cache.invalidate(cache_key)
            del self._submissions_by_user[user_id]
        
        self._cache.invalidate_pattern(f"user_{user_id}_")
    
    def invalidate_submission(self, submission_id: int):
        """Invalidate specific submission."""
        self._cache.delete(f"submission_{submission_id}")


def cached_query(ttl: float = 60, key_prefix: str = ''):
    """
    Decorator to cache function results with TTL.
    Useful for expensive database queries.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Optional prefix for cache key
        
    Usage:
        @cached_query(ttl=120, key_prefix='submissions_')
        def get_recent_submissions(user_id: int):
            # Expensive query cached for 2 minutes
            return db.query(...)
    """
    def decorator(func: Callable) -> Callable:
        _cache = QueryCache(default_ttl=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if st is not None and hasattr(st, 'session_state'):
                cache_enabled = st.session_state.get('query_cache_enabled', True)
                if not cache_enabled:
                    return func(*args, **kwargs)
            
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            cache_key = f"{key_prefix}{func.__name__}_{hashlib.md5((args_str + kwargs_str).encode()).hexdigest()}"
            
            cached_result = _cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            _cache.set(cache_key, data=result, ttl=ttl)
            
            return result
        
        wrapper.cache_clear = _cache.clear
        wrapper.cache_stats = _cache.get_stats
        
        return wrapper
    
    return decorator


def streamlit_cached_data(ttl: int = 300):
    """
    Decorator using Streamlit's native caching with TTL.
    Combines st.cache_data with TTL support.
    
    Args:
        ttl: Time-to-live in seconds
        
    Usage:
        @streamlit_cached_data(ttl=300)
        def load_user_data(user_id):
            cached for 5 minutes
            ...
    """
    def decorator(func: Callable) -> Callable:
        if st is None:
            return func
        
        @st.cache_data(ttl=ttl, show_spinner=False)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


_global_query_cache: Optional[QueryCache] = None
_global_submission_cache: Optional[SubmissionCache] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    global _global_query_cache
    if _global_query_cache is None:
        _global_query_cache = QueryCache(maxsize=512, default_ttl=180)
    return _global_query_cache


def get_submission_cache() -> SubmissionCache:
    """Get global submission cache instance."""
    global _global_submission_cache
    if _global_submission_cache is None:
        _global_submission_cache = SubmissionCache(get_query_cache())
    return _global_submission_cache


def clear_all_caches():
    """Clear all caches."""
    global _global_query_cache, _global_submission_cache
    
    if _global_query_cache:
        _global_query_cache.clear()
    
    if _global_submission_cache:
        _global_submission_cache._cache.clear()
        _global_submission_cache._submissions_by_user.clear()
    
    if st is not None and hasattr(st, 'cache_data'):
        st.cache_data.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    query_stats = _global_query_cache.get_stats() if _global_query_cache else {}
    
    return {
        'query_cache': query_stats,
        'submission_cache_size': len(_global_submission_cache._submissions_by_user) if _global_submission_cache else 0
    }
