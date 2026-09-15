"""
Tests for caching/lazy/async utilities.

Covers utils/distributed_cache.py (InMemoryCache, DistributedCache),
utils/lazy_loader.py (LazyModule) and utils/async_processing.py
(processors). Redis-dependent and Streamlit-dependent paths are tested
via fallback/mocking.
"""

import asyncio

import pytest

from utils.async_processing import (
    AsyncProcessor,
    BatchProcessor,
    ChunkedProcessor,
)
from utils.distributed_cache import DistributedCache, InMemoryCache
from utils.lazy_loader import LazyModule


# ---------------------------------------------------------------------------
# InMemoryCache
# ---------------------------------------------------------------------------

class TestInMemoryCache:
    def test_set_get_roundtrip(self):
        cache = InMemoryCache()
        assert cache.set('k', {'a': 1}) is True
        assert cache.get('k') == {'a': 1}

    def test_missing_key_returns_none(self):
        assert InMemoryCache().get('missing') is None

    def test_ttl_expiry(self):
        cache = InMemoryCache()
        cache.set('exp', 'value', ttl=0)
        # expires_at is now + 0s; a fresh get is already past expiry
        assert cache.get('exp') is None

    def test_delete_and_exists(self):
        cache = InMemoryCache()
        cache.set('k', 1)
        assert cache.exists('k') is True
        assert cache.delete('k') is True
        assert cache.delete('k') is False
        assert cache.exists('k') is False

    def test_clear(self):
        cache = InMemoryCache()
        cache.set('a', 1)
        cache.set('b', 2)
        assert cache.clear() is True
        assert cache.get('a') is None

    def test_eviction_when_full(self):
        cache = InMemoryCache(maxsize=10)
        for i in range(20):
            cache.set(f'key{i}', i)
        assert len(cache._cache) < 20  # evicted oldest tenth


# ---------------------------------------------------------------------------
# DistributedCache (memory fallback)
# ---------------------------------------------------------------------------

class TestDistributedCache:
    def test_memory_fallback_by_default(self):
        cache = DistributedCache()
        assert cache.is_redis is False
        assert cache.set('k', 'v') is True
        assert cache.get('k') == 'v'

    def test_stats_memory(self):
        cache = DistributedCache()
        cache.set('k', 'v')
        stats = cache.get_stats()
        assert stats['backend'] == 'memory'
        assert stats['is_redis'] is False
        assert stats['size'] == 1

    def test_no_backend_raises(self):
        with pytest.raises(RuntimeError):
            DistributedCache(fallback_to_memory=False)

    def test_delete_exists_clear(self):
        cache = DistributedCache()
        cache.set('k', 'v')
        assert cache.exists('k') is True
        assert cache.delete('k') is True
        assert cache.exists('k') is False
        assert cache.clear() is True

    def test_backend_exception_returns_safe_default(self):
        cache = DistributedCache()
        cache._backend = BrokenBackend()
        assert cache.get('k') is None
        assert cache.set('k', 'v') is False
        assert cache.delete('k') is False
        assert cache.exists('k') is False
        assert cache.clear() is False


class BrokenBackend:
    """Backend that always fails — verifies safe error handling."""

    def get(self, key):
        raise RuntimeError('boom')

    def set(self, key, value, ttl=300):
        raise RuntimeError('boom')

    def delete(self, key):
        raise RuntimeError('boom')

    def exists(self, key):
        raise RuntimeError('boom')

    def clear(self):
        raise RuntimeError('boom')


# ---------------------------------------------------------------------------
# LazyModule
# ---------------------------------------------------------------------------

class TestLazyModule:
    def test_deferred_attribute_access(self):
        lazy = LazyModule('math')
        assert lazy.sqrt(16) == 4.0

    def test_dir_loads_module(self):
        lazy = LazyModule('math')
        assert 'sqrt' in dir(lazy)
        assert lazy._module is not None

    def test_module_caching(self):
        lazy = LazyModule('math')
        first = lazy._load_module()
        second = lazy._load_module()
        assert first is second


# ---------------------------------------------------------------------------
# Async / Batch / Chunked processors
# ---------------------------------------------------------------------------

class TestAsyncProcessor:
    def test_run_async(self):
        processor = AsyncProcessor(max_workers=2)

        def double(x):
            return x * 2

        result = asyncio.run(processor.run_async(double, 21))
        assert result == 42


class TestBatchProcessor:
    def test_process_batch_preserves_count(self):
        processor = BatchProcessor(batch_size=2, max_workers=2)
        results = processor.process_batch(lambda x: x * 10, [1, 2, 3, 4, 5])
        assert sorted(results) == [10, 20, 30, 40, 50]

    def test_progress_callback_called(self):
        processor = BatchProcessor(batch_size=2, max_workers=1)
        calls = []
        processor.process_batch(str.upper, ['a', 'b', 'c'],
                                progress_callback=lambda cur, total: calls.append((cur, total)))
        assert calls[-1] == (3, 3)

    def test_item_failure_yields_none(self):
        processor = BatchProcessor(batch_size=2, max_workers=2)

        def maybe_fail(x):
            if x == 2:
                raise ValueError('fail')
            return x

        results = processor.process_batch(maybe_fail, [1, 2, 3])
        assert results == [1, None, 3]


class TestChunkedProcessor:
    def test_process_file_chunks(self):
        import io

        processor = ChunkedProcessor(chunk_size=16)
        file_obj = io.BytesIO(b'x' * 40)
        seen = processor.process_file_chunks(file_obj, lambda chunk, num: (num, len(chunk)))
        assert seen == [(0, 16), (1, 16), (2, 8)]

    def test_chunk_error_yields_none(self):
        import io

        processor = ChunkedProcessor(chunk_size=16)
        file_obj = io.BytesIO(b'x' * 40)

        def always_fail(chunk, num):
            raise ValueError('chunk fail')

        results = processor.process_file_chunks(file_obj, always_fail)
        assert results == [None, None, None]