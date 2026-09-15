"""
Extended tests for utils/distributed_cache.py — Redis path with a fake
redis client, CacheWarming, SmartCacheInvalidation, global helpers.
"""

import pytest

from utils.distributed_cache import (
    CacheBackend,
    CacheWarming,
    DistributedCache,
    InMemoryCache,
    RedisCache,
    SmartCacheInvalidation,
    get_distributed_cache,
)


class FakeRedis:
    """In-memory fake of the redis-py surface used by RedisCache."""

    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def setex(self, key, ttl, value):
        self._data[key] = value
        return True

    def delete(self, *keys):
        removed = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                removed += 1
        return removed

    def exists(self, key):
        return int(key in self._data)

    def keys(self, pattern):
        import fnmatch
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def info(self, section=None):
        return {'used_memory': 1024, 'used_memory_human': '1K'}

    def dbsize(self):
        return len(self._data)


@pytest.fixture
def redis_cache():
    client = FakeRedis()
    cache = RedisCache.__new__(RedisCache)
    cache._client = client
    cache._prefix = 'niklaus:'
    return cache


# ---------------------------------------------------------------------------
# RedisCache with fake client
# ---------------------------------------------------------------------------

class TestRedisCache:
    def test_set_get_roundtrip_compressed(self, redis_cache):
        assert redis_cache.set('k', {'a': 1}) is True
        assert redis_cache.get('k') == {'a': 1}

    def test_get_missing_returns_none(self, redis_cache):
        assert redis_cache.get('missing') is None

    def test_get_raw_json_fallback(self, redis_cache):
        redis_cache._client._data['niklaus:raw'] = b'{"x": 1}'
        assert redis_cache.get('raw') == {'x': 1}

    def test_get_undecodable_returns_none(self, redis_cache):
        redis_cache._client._data['niklaus:bad'] = b'\xff\xfe not json'
        assert redis_cache.get('undecodable') is None

    def test_delete_and_exists(self, redis_cache):
        redis_cache.set('k', 1)
        assert redis_cache.exists('k') is True
        assert redis_cache.delete('k') is True
        assert redis_cache.exists('k') is False

    def test_clear_with_prefix(self, redis_cache):
        redis_cache.set('k1', 1)
        redis_cache.set('k2', 2)
        assert redis_cache.clear() is True
        assert redis_cache.exists('k1') is False

    def test_clear_empty_prefix(self, redis_cache):
        assert redis_cache.clear() is True

    def test_set_fallback_on_compression_error(self, redis_cache, monkeypatch):
        def failing_compress(data, level=6):
            raise RuntimeError('zlib fail')

        monkeypatch.setattr('utils.distributed_cache.zlib.compress', failing_compress)
        # Fallback serialises plain JSON
        assert redis_cache.set('k', {'v': 1}) is True
        assert redis_cache.get('k') == {'v': 1}

    def test_set_error_returns_false(self, redis_cache, monkeypatch):
        def broken(*args, **kwargs):
            raise RuntimeError('x')

        monkeypatch.setattr('utils.distributed_cache.zlib.compress', broken)
        monkeypatch.setattr(redis_cache._client, 'setex', broken)
        assert redis_cache.set('k', {'v': 1}) is False

    def test_requires_redis_import(self, monkeypatch):
        import utils.distributed_cache as dcmod
        monkeypatch.setattr(dcmod, 'REDIS_AVAILABLE', False)
        with pytest.raises(ImportError):
            RedisCache()


# ---------------------------------------------------------------------------
# DistributedCache with Redis backend
# ---------------------------------------------------------------------------

class TestDistributedCacheRedis:
    def test_redis_backend_stats(self, monkeypatch):
        import types
        import utils.distributed_cache as dcmod
        monkeypatch.setattr(dcmod, 'REDIS_AVAILABLE', True)
        monkeypatch.setattr(dcmod, 'redis', types.SimpleNamespace(Redis=lambda **kw: FakeRedis()), raising=False)

        cache = DistributedCache(redis_host='localhost')
        assert cache.is_redis is True
        cache.set('k', {'v': 1})
        stats = cache.get_stats()
        assert stats['backend'] == 'redis'
        assert stats['key_count'] == 1
        assert stats['used_memory'] == 1024

    def test_redis_connection_failure_falls_back(self, monkeypatch):
        import types
        import utils.distributed_cache as dcmod
        monkeypatch.setattr(dcmod, 'REDIS_AVAILABLE', True)

        class FailingModule:
            @staticmethod
            def Redis(**kwargs):
                raise ConnectionError('no redis')

        monkeypatch.setattr(dcmod, 'redis', types.SimpleNamespace(Redis=FailingModule.Redis), raising=False)
        cache = DistributedCache(redis_host='localhost', fallback_to_memory=True)
        assert cache.is_redis is False  # fell back to memory
        assert cache.set('k', 1) is True


# ---------------------------------------------------------------------------
# CacheWarming
# ---------------------------------------------------------------------------

class TestCacheWarming:
    def test_warm_pattern(self):
        cache = DistributedCache()
        warming = CacheWarming(cache)
        warming.register_warming_function('user_*', lambda: {'pre': 1}, ttl=60)
        warming.warm_cache()
        assert cache.get('user_all') == {'pre': 1}

    def test_warm_single_matching_key(self):
        cache = DistributedCache()
        warming = CacheWarming(cache)
        warming.register_warming_function('user_*_subs', lambda: [1, 2])
        warming.warm_cache(keys=['user_9_subs'])
        assert cache.get('user_9_subs') == [1, 2]

    def test_warm_key_no_match_ignored(self):
        cache = DistributedCache()
        warming = CacheWarming(cache)
        warming.register_warming_function('other_*', lambda: 1)
        warming.warm_cache(keys=['nomatch_key'])
        assert cache.exists('nomatch_key') is False

    def test_warm_function_error_swallowed(self):
        cache = DistributedCache()
        warming = CacheWarming(cache)

        def boom():
            raise ValueError('fail')

        warming.register_warming_function('p_*', boom)
        warming.warm_cache(keys=['p_1'])  # must not raise
        assert cache.exists('p_1') is False


# ---------------------------------------------------------------------------
# SmartCacheInvalidation
# ---------------------------------------------------------------------------

class TestSmartCacheInvalidation:
    def test_dependency_invalidation_on_event(self):
        cache = DistributedCache()
        cache.set('submission_1', {'x': 1})
        invalidator = SmartCacheInvalidation(cache)
        invalidator.add_dependency('submission_1', ['user_7_update'])
        invalidator.invalidate_on_event('user_7_update')
        assert cache.get('submission_1') is None

    def test_unknown_event_is_noop(self):
        SmartCacheInvalidation(DistributedCache()).invalidate_on_event('nothing')

    def test_get_dependencies(self):
        invalidator = SmartCacheInvalidation(DistributedCache())
        invalidator.add_dependency('k1', ['ev1', 'ev2'])
        assert invalidator.get_dependencies('k1') == ['ev1', 'ev2']


# ---------------------------------------------------------------------------
# Global helpers
# ---------------------------------------------------------------------------

def test_get_distributed_cache_singleton():
    assert get_distributed_cache() is get_distributed_cache()


def test_cache_backend_abstract_raises():
    backend = CacheBackend()
    for call in (
        lambda: backend.get('k'),
        lambda: backend.set('k', 1),
        lambda: backend.delete('k'),
        lambda: backend.exists('k'),
        lambda: backend.clear(),
    ):
        with pytest.raises(NotImplementedError):
            call()


def test_inmemory_evict_oldest_empty():
    InMemoryCache()._evict_oldest()  # no-op on empty cache