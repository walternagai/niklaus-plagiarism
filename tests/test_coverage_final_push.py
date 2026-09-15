"""
Final coverage close-out: oauth user creation, pipeline AI path,
analytics dashboards (mocked st), performance report display,
decorators require_auth, async batch async paths.
"""

import asyncio
import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.models import Base, User
from core.pipeline import AnalysisPipeline
from utils.exceptions import AnalysisCancelledError, NiklausError


# ---------------------------------------------------------------------------
# OAuthHandler.create_user_from_oauth — real DB, mocked session factory
# ---------------------------------------------------------------------------

class TestCreateUserFromOAuth:
    @pytest.fixture
    def db(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        yield Session()
        engine.dispose()

    def _build(self, db, monkeypatch):
        import auth.oauth as oauth_mod
        monkeypatch.setattr(oauth_mod, 'get_session', lambda: db)
        return db

    def test_create_new_user(self, monkeypatch, db):
        import auth.oauth as oauth_mod
        monkeypatch.setattr(oauth_mod, 'get_session', lambda: db)
        user = oauth_mod.OAuthHandler.create_user_from_oauth(
            email='new@x.com', name='New', provider='github', oauth_id='1',
            access_token='AT', refresh_token='RT')
        assert user.id is not None
        assert user.role == 'user'
        # token persisted encrypted (not plaintext)
        assert user.oauth_access_token != 'AT'

    def test_updates_existing_user(self, monkeypatch, db):
        import auth.oauth as oauth_mod
        from auth.repository import UserRepository
        monkeypatch.setattr(oauth_mod, 'get_session', lambda: db)
        existing = User(email='known@x.com', name='Old')
        db.add(existing)
        db.commit()

        user = oauth_mod.OAuthHandler.create_user_from_oauth(
            email='known@x.com', name='Renamed', provider='google',
            oauth_id='7', access_token='TOK')
        assert user.name == 'Renamed'
        refreshed = UserRepository(db).find_by_email('known@x.com')
        assert refreshed.oauth_provider == 'google'
        assert refreshed.last_login_at is not None

    def test_handle_callback_success_path(self, monkeypatch, db):
        """Full callback: token exchange -> profile -> create user."""
        import auth.oauth as oauth_mod
        monkeypatch.setattr(oauth_mod, 'get_session', lambda: db)

        handler = oauth_mod.OAuthHandler('github')
        monkeypatch.setattr(
            'requests.post',
            lambda *a, **kw: SimpleNamespace(status_code=200, text='{}',
                                             json=lambda: {'access_token': 'AT'}))
        monkeypatch.setattr(
            'requests.get',
            lambda *a, **kw: SimpleNamespace(
                status_code=200, json=lambda: {'id': 1, 'login': 'u', 'email': 'cb@x.com'}))
        user = handler.handle_callback('code', 'state')
        assert user is not None
        assert user.email == 'cb@x.com'


# ---------------------------------------------------------------------------
# core/pipeline — full run with mocked analyzer + AI
# ---------------------------------------------------------------------------

class TestPipelineFullRun:
    def _pipeline(self):
        import numpy as np
        pipeline = AnalysisPipeline('python', use_cache=False)
        analyzer = MagicMock()
        analyzer.analyze_files.return_value = {
            'textual_similarities': [('a.py', 'b.py', 0.92)],
            'similarity_matrix': np.array([[1.0, 0.92], [0.92, 1.0]]),
            'ast_similarities': [('a.py', 'b.py', 0.85)],
            'patterns': {'a.py_b.py': {'detected': True}},
            'metrics': [],
            'cluster_data': {'clusters': [], 'labels': {}},
        }
        analyzer.get_suspicious_pairs.return_value = [('a.py', 'b.py', 0.92)]
        pipeline._analyzer = analyzer
        return pipeline

    def test_run_full_analysis_without_ai(self):
        pipeline = self._pipeline()
        results = pipeline.run_full_analysis(
            files=['a.py', 'b.py'], contents=['x=1', 'y=2'],
            threshold=0.7, enable_ai=False)
        assert results['suspicious_pairs'] == [('a.py', 'b.py', 0.92)]
        assert results['average_similarity'] == pytest.approx(0.92)
        assert results['pairwise_results'][0]['is_suspicious'] is True
        assert results['ai_analyses'] == {}

    def test_run_full_analysis_with_ai(self):
        pipeline = self._pipeline()
        pipeline._llm_client = MagicMock()
        pipeline._llm_client.analyze_plagiarism.return_value = 'IA: plágio confirmado'

        results = pipeline.run_full_analysis(
            files=['a.py', 'b.py'], contents=['x=1', 'y=2'],
            threshold=0.7, enable_ai=True)
        assert results['ai_analyses'].get('a.py_b.py') == 'IA: plágio confirmado'

    def test_run_full_analysis_cancelled(self):
        pipeline = self._pipeline()
        with pytest.raises(AnalysisCancelledError):
            pipeline.run_full_analysis(
                files=['a.py', 'b.py'], contents=['x=1', 'y=2'],
                threshold=0.7, enable_ai=False,
                cancel_check=lambda: True)

    def test_run_full_analysis_pipeline_error_wraps(self):
        pipeline = self._pipeline()
        pipeline._analyzer.analyze_files.side_effect = ValueError('kaboom')
        with pytest.raises(NiklausError, match='pipeline failed'):
            pipeline.run_full_analysis(
                files=['a.py'], contents=['x=1'], threshold=0.7, enable_ai=False)

    def test_run_textual_only(self):
        pipeline = self._pipeline()
        results = pipeline.run_textual_only(['a.py', 'b.py'], ['x=1', 'y=2'])
        assert 'suspicious_pairs' in results

    def test_run_full_analysis_with_cache_roundtrip(self, tmp_path):
        from core.persistence import AnalysisCache
        pipeline = self._pipeline()
        cache = AnalysisCache(cache_dir=str(tmp_path / 'pc'))
        pipeline._cache = cache

        first = pipeline.run_full_analysis(
            files=['a.py', 'b.py'], contents=['x=1', 'y=2'],
            threshold=0.7, enable_ai=False)
        second = pipeline.run_full_analysis(
            files=['a.py', 'b.py'], contents=['x=1', 'y=2'],
            threshold=0.7, enable_ai=False)
        # NOTE: cached pairs come back as lists (JSON roundtrip), tuples live
        assert [tuple(p) for p in second['suspicious_pairs']] == list(first['suspicious_pairs'])


# ---------------------------------------------------------------------------
# analytics dashboards — mocked streamlit
# ---------------------------------------------------------------------------

class TestAnalyticsDashboards:
    @pytest.fixture
    def fake_st(self):
        import utils.analytics as analytics_mod
        fake = MagicMock()
        fake.columns = lambda n, **kw: [MagicMock() for _ in range(n)]
        with patch.object(analytics_mod.st, 'markdown', fake.markdown), \
             patch.object(analytics_mod.st, 'metric', fake.metric), \
             patch.object(analytics_mod.st, 'caption', fake.caption), \
             patch.object(analytics_mod.st, 'expander', MagicMock(return_value=MagicMock())), \
             patch.object(analytics_mod.st, 'bar_chart', fake.bar_chart), \
             patch.object(analytics_mod.st, 'line_chart', fake.line_chart), \
             patch.object(analytics_mod.st, 'dataframe', fake.dataframe), \
             patch.object(analytics_mod.st, 'columns', fake.columns, create=True):
            yield fake

    def _seed(self):
        from utils.analytics import get_analytics
        engine = get_analytics()
        engine.track_analysis(submission_id=1, user_id=1, files_count=2,
                              suspicious_pairs_count=1, avg_similarity=0.7,
                              max_similarity=0.9, processing_time=1.0,
                              language='python', threshold=0.7)
        engine.track_user_action(1, 'login')
        return engine

    def test_display_dashboard_full(self, fake_st):
        from utils.analytics import display_analytics_dashboard
        self._seed()
        display_analytics_dashboard()
        fake_st.metric.assert_called()

    def test_dashboard_st_none_guard(self):
        import utils.analytics as analytics_mod
        with patch.object(analytics_mod, 'st', None):
            analytics_mod.display_analytics_dashboard()  # early return, no raise


# ---------------------------------------------------------------------------
# utils/performance — display report (mocked streamlit)
# ---------------------------------------------------------------------------

class TestPerformanceDisplay:
    def test_display_performance_report_with_data(self, monkeypatch):
        import utils.performance as perf_mod
        from utils.performance import get_performance_metrics

        fake = MagicMock()
        fake.columns = lambda n, **kw: [MagicMock() for _ in range(n)]
        monkeypatch.setattr(perf_mod.st, 'metric', fake.metric, raising=False)
        monkeypatch.setattr(perf_mod.st, 'markdown', fake.markdown, raising=False)
        monkeypatch.setattr(perf_mod.st, 'dataframe', fake.dataframe, raising=False)
        monkeypatch.setattr(perf_mod.st, 'caption', fake.caption, raising=False)
        monkeypatch.setattr(perf_mod.st, 'columns', fake.columns, raising=False)

        get_performance_metrics().clear()
        get_performance_metrics().record('op', 1.0)
        perf_mod.display_performance_report()
        fake.metric.assert_called()

    def test_get_metrics_for_export(self):
        from utils.performance import get_metrics_for_export, get_performance_metrics
        get_performance_metrics().clear()
        get_performance_metrics().record('export_op', 2.0)
        exported = get_metrics_for_export()
        assert isinstance(exported, dict)
        assert 'op' in str(exported) or exported


# ---------------------------------------------------------------------------
# decorators — require_auth line coverage
# ---------------------------------------------------------------------------

class TestRequireAuth:
    def test_blocks_and_passes(self, monkeypatch):
        import auth.decorators as dec

        class FakeState(dict):
            def __getattr__(self, name):
                try:
                    return self[name]
                except KeyError as exc:
                    raise AttributeError(name) from exc

            def __setattr__(self, name, value):
                self[name] = value

        state = FakeState()
        fake_st = SimpleNamespace(
            session_state=state,
            warning=MagicMock(), stop=MagicMock(side_effect=RuntimeError('stop')),
            button=MagicMock(return_value=False), switch_page=MagicMock(),
            error=MagicMock(), info=MagicMock(),
        )
        monkeypatch.setattr(dec, 'st', fake_st)

        # anonymous -> warning + stop
        with pytest.raises(RuntimeError, match='stop'):
            dec.require_auth(lambda: 'x')()

        # authenticated -> executes
        state['user'] = {'id': 1}
        assert dec.require_auth(lambda: 'ok')() == 'ok'

        # user None -> blocked again
        state['user'] = None
        with pytest.raises(RuntimeError, match='stop'):
            dec.require_auth(lambda: 'x')()


# ---------------------------------------------------------------------------
# async_processing — async batch + file async
# ---------------------------------------------------------------------------

class TestAsyncRemaining:
    def test_run_batch_async(self):
        from utils.async_processing import AsyncProcessor
        processor = AsyncProcessor(max_workers=2)
        results = asyncio.run(processor.run_batch_async(str.upper, ['x', 'y']))
        assert results == ['X', 'Y']

    def test_process_file_async(self):
        from utils.async_processing import ChunkedProcessor
        processor = ChunkedProcessor(chunk_size=16)
        file_obj = io.BytesIO(b'z' * 40)
        results = asyncio.run(processor.process_file_async(
            file_obj, lambda chunk: len(chunk)))
        assert results == [16, 16, 8]