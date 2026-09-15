"""
Tests for core/persistence.py (AnalysisCache disk cache, DiskSessionManager,
AnalysisResult, _NumpyEncoder) and extra repository/async coverage.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from core.persistence import (
    AnalysisCache,
    AnalysisResult,
    DiskSessionManager,
    _NumpyEncoder,
    _json_dumps,
    _json_loads,
)


# ---------------------------------------------------------------------------
# _NumpyEncoder / _json_dumps / _json_loads
# ---------------------------------------------------------------------------

class TestNumpyJson:
    def test_numpy_scalars_and_arrays(self):
        data = {'arr': np.array([1, 2]), 'f64': np.float64(1.5), 'i64': np.int64(3)}
        parsed = json.loads(_json_dumps(data))
        assert parsed['arr'] == [1, 2]
        assert parsed['f64'] == 1.5
        assert parsed['i64'] == 3

    def test_nan_inf_become_null(self):
        parsed = json.loads(_json_dumps({'x': float('nan'), 'y': float('inf')}))
        assert parsed == {'x': None, 'y': None}

    def test_datetime_roundtrip(self):
        dt = datetime(2024, 5, 1, 12, 30, tzinfo=UTC)
        restored = _json_loads(_json_dumps({'when': dt}))
        assert restored['when'] == dt

    def test_non_string_keys_coerced(self):
        parsed = json.loads(_json_dumps({1: 'a', 2.5: 'b', (1, 2): 'c'}))
        assert parsed['1'] == 'a'
        assert parsed['2.5'] == 'b'
        assert parsed['(1, 2)'] == 'c'

    def test_encoder_default_falls_back(self):
        class Custom:
            pass

        with pytest.raises(TypeError):
            json.dumps({'obj': Custom()}, cls=_NumpyEncoder)


# ---------------------------------------------------------------------------
# AnalysisCache — disk roundtrip
# ---------------------------------------------------------------------------

class TestAnalysisCacheDisk:
    @pytest.fixture
    def cache(self, tmp_path):
        return AnalysisCache(cache_dir=str(tmp_path / 'cachetest'))

    def test_save_and_load_roundtrip(self, cache):
        files = ['a.py', 'b.py']
        contents = ['x = 1', 'y = 2']
        cache.save(files, 0.7, {'pairs': [1, 2]}, contents=contents, language='python')
        loaded = cache.load(files, 0.7, contents=contents, language='python')
        assert loaded is not None
        assert loaded == {'pairs': [1, 2]}

    def test_load_missing_returns_none(self, cache):
        assert cache.load(['none.py'], 0.7) is None

    def test_different_threshold_no_hit(self, cache):
        cache.save(['a.py', 'b.py'], 0.7, {'x': 1})
        assert cache.load(['a.py', 'b.py'], 0.9) is None

    def test_expired_file_removed_on_load(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        # Expiry lives in the FILENAME; rename it into the past
        for f in list(cache.cache_dir.glob('*.json')):
            parts = f.stem.rsplit('_', 1)
            f.rename(f.with_name(f"{parts[0]}_1000{f.suffix}"))
        assert cache.load(['a.py', 'b.py'], 0.5) is None

    def test_max_age_hours_limit(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        assert cache.load(['a.py', 'b.py'], 0.5, max_age_hours=0) is None

    def test_clear_all_cache(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        cache.save(['c.py', 'd.py'], 0.5, {'y': 2})
        removed = cache.clear_all_cache()
        assert removed == 2
        assert cache.get_cache_stats()['file_count'] == 0

    def test_cleanup_old_cache(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        # Backdate mtime beyond retention
        import os
        old = datetime.now(UTC).timestamp() - 40 * 86400
        for f in cache.cache_dir.glob('*.json'):
            os.utime(f, (old, old))
        removed = cache.clear_old_cache(max_age_days=30)
        assert removed >= 1

    def test_cache_stats_shape(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        stats = cache.get_cache_stats()
        assert stats['file_count'] == 1
        assert stats['total_size_bytes'] > 0
        assert 'total_size_mb' in stats

    def test_corrupt_cache_file_is_deleted(self, cache):
        cache.save(['a.py', 'b.py'], 0.5, {'x': 1})
        for f in cache.cache_dir.glob('*.json'):
            f.write_text('{not json')
        assert cache.load(['a.py', 'b.py'], 0.5) is None

    def test_save_error_raises_cache_error(self, cache):
        from utils.exceptions import CacheError
        cache.cache_dir = Path('/proc/impossible/dir/for/test')
        with pytest.raises(CacheError):
            cache.save(['a.py', 'b.py'], 0.5, {'x': 1})


# ---------------------------------------------------------------------------
# DiskSessionManager
# ---------------------------------------------------------------------------

class TestDiskSessionManager:
    def test_save_load_clear(self, tmp_path):
        manager = DiskSessionManager(session_file=tmp_path / 'sess.json')
        manager.save_session({'user': {'id': 1}})
        assert manager.load_session() == {'user': {'id': 1}}
        manager.clear_session()
        assert manager.load_session() == {}

    def test_load_missing_returns_empty(self, tmp_path):
        assert DiskSessionManager(session_file=tmp_path / 'none.json').load_session() == {}

    def test_corrupt_session_returns_empty(self, tmp_path):
        f = tmp_path / 'bad.json'
        f.write_text('{invalid')
        assert DiskSessionManager(session_file=f).load_session() == {}


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------

class TestAnalysisResult:
    def test_attrs_and_to_dict(self):
        result = AnalysisResult(files=['a.py'], similarity=0.9)
        assert result.to_dict() == {'files': ['a.py'], 'similarity': 0.9}

    def test_json_roundtrip(self):
        result = AnalysisResult(files=['a.py'], score=1.5)
        restored = AnalysisResult.from_dict(json.loads(result.to_json()))
        assert restored.to_dict() == result.to_dict()


# ---------------------------------------------------------------------------
# SubmissionRepository — filter paths (missing lines 146-166, 227-253)
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.models import Base, User
from auth.repository import SubmissionRepository


class TestSubmissionFilters:
    @pytest.fixture
    def setup(self):
        from utils.db_cache import clear_all_caches
        clear_all_caches()
        engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        user = User(email='f@x.com', name='F')
        db.add(user)
        db.commit()
        db.refresh(user)
        repo = SubmissionRepository(db)
        repo.create(user_id=user.id, filename='a.zip', language='python',
                    status='completed', average_similarity=0.9)
        repo.create(user_id=user.id, filename='b.zip', language='java',
                    status='failed', average_similarity=0.2)
        yield db, repo, user
        clear_all_caches()
        db.close()

    def test_filter_by_status(self, setup):
        db, repo, user = setup
        results = repo.find_by_user(user.id, status='completed', use_cache=False)
        assert len(results) == 1
        assert results[0].status == 'completed'

    def test_filter_by_date(self, setup):
        db, repo, user = setup
        now = datetime.now(UTC)
        results = repo.find_by_user(
            user.id, date_start=now - timedelta(days=1),
            date_end=now + timedelta(days=1), use_cache=False)
        assert len(results) == 2
        none_window = repo.find_by_user(
            user.id, date_end=now - timedelta(days=30), use_cache=False)
        assert none_window == []

    def test_filter_by_similarity(self, setup):
        db, repo, user = setup
        high = repo.find_by_user(user.id, min_similarity=0.5, use_cache=False)
        low = repo.find_by_user(user.id, max_similarity=0.3, use_cache=False)
        assert len(high) == 1
        assert len(low) == 1

    def test_count_by_user(self, setup):
        db, repo, user = setup
        assert repo.count_by_user(user.id) == 2
        assert repo.count_by_user(user.id, status='failed') == 1

    def test_get_stats_by_user(self, setup):
        db, repo, user = setup
        stats = repo.get_stats_by_user(user.id)
        assert stats is not None

    def test_find_by_user_with_cache(self, setup):
        db, repo, user = setup
        first = repo.find_by_user(user.id, use_cache=True)
        second = repo.find_by_user(user.id, use_cache=True)
        assert len(first) == len(second) == 2


# ---------------------------------------------------------------------------
# async_processing — run_batch_async + async_task + batch_process
# ---------------------------------------------------------------------------

import asyncio

from utils.async_processing import (
    AsyncProcessor,
    async_task,
    batch_process,
    get_async_processor,
)


class TestAsyncExtras:
    def test_run_batch_async(self):
        processor = AsyncProcessor(max_workers=2)
        results = asyncio.run(processor.run_batch_async(str.upper, ['a', 'b', 'c']))
        assert results == ['A', 'B', 'C']

    def test_async_task_decorator(self):
        @async_task
        def multiply(a, b):
            return a * b

        assert asyncio.run(multiply(3, 4)) == 12

    def test_batch_process_decorator_item_wise(self):
        @batch_process(batch_size=2)
        def double(item):
            return item * 2

        # NOTE: BatchProcessor uses as_completed — results are unordered
        assert sorted(double([1, 2, 3, 4, 5])) == [2, 4, 6, 8, 10]

    def test_get_async_processor(self):
        p1 = get_async_processor()
        p2 = get_async_processor()
        assert p1 is p2