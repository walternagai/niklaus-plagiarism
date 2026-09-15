"""
Final coverage push: llm_client retries, parallel comparator/rate limiter,
alerts trends/summary/helpers, decorators require_auth, db_cache helpers,
exceptions, logger, compression edge cases.
"""

from unittest.mock import MagicMock, patch

import openai
import pytest

from utils.alerts import PerformanceMonitor, check_performance_alerts, get_alert_manager
from utils.compression import CompressionStats, get_compression_stats
from utils.db_cache import cached_query, streamlit_cached_data
from utils.exceptions import (
    AnalysisCancelledError,
    CacheError,
    LanguageDetectionError,
    MaritacaAPIError,
    NiklausError,
    ZipExtractionError,
)
from utils.logger import get_logger
from utils.parallel import (
    BatchProcessor,
    ParallelComparator,
    RateLimiter,
)


# ---------------------------------------------------------------------------
# core/llm_client — retry paths (mocked openai client)
# ---------------------------------------------------------------------------

def _api_error(cls, message, status_code=429):
    """Build an openai APIError subclass with a minimal httpx response."""
    import httpx
    response = httpx.Response(status_code=status_code, request=httpx.Request('POST', 'https://api'))
    return cls(message, response=response, body=None)


class TestMaritacaRetries:
    def _build_client(self):
        from core.llm_client import MaritacaClient
        with patch('core.llm_client.openai.OpenAI'):
            client = MaritacaClient(api_key='KEY', model='m1')
        return client

    def _run_generate(self, client, side_effects):
        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content='OK'))]
        with patch.object(client.client.chat.completions, 'create', side_effect=side_effects):
            with patch.object(client.rate_limiter, 'wait'):
                with patch('core.llm_client.time.sleep') as slept:
                    return client.analyze_plagiarism(
                        'a', 'b', 'f1', 'f2',
                        textual_similarity=0.9, ast_similarity=0.8,
                        plagiarism_type='VARIABLE_RENAMING', confidence=0.7,
                    ), slept

    def test_success_first_try(self):
        client = self._build_client()
        result, _ = self._run_generate(client, side_effects=[MagicMock(
            choices=[MagicMock(message=MagicMock(content='analysis text'))])])
        assert result == 'analysis text'

    def test_retry_on_rate_limit_then_success(self):
        client = self._build_client()
        client.max_retries = 2
        import openai
        error = openai.APIError('rate limited', request=None, body=None)
        response = MagicMock(choices=[MagicMock(message=MagicMock(content='ok'))])
        result, slept = self._run_generate(client, side_effects=[error, response])
        assert result == 'ok'
        assert slept.called

    def test_rate_limit_exhausted_raises(self):
        from core.llm_client import RateLimitError
        client = self._build_client()
        client.max_retries = 1
        error = _api_error(openai.RateLimitError, 'rate')
        with pytest.raises(RateLimitError):
            self._run_generate(client, side_effects=[error])

    def test_api_error_exhausted_raises_maritaca(self):
        client = self._build_client()
        client.max_retries = 1
        error = _api_error(openai.InternalServerError, 'server down', status_code=500)
        with pytest.raises(MaritacaAPIError):
            self._run_generate(client, side_effects=[error])

    def test_test_connection_ok_and_fail(self):
        client = self._build_client()
        with patch.object(client.client.chat.completions, 'create',
                          return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='OK'))])):
            with patch.object(client.rate_limiter, 'wait'):
                assert client.test_connection() is True
        with patch.object(client.client.chat.completions, 'create',
                          side_effect=ConnectionError('down')):
            with patch.object(client.rate_limiter, 'wait'):
                assert client.test_connection() is False


# ---------------------------------------------------------------------------
# utils/parallel
# ---------------------------------------------------------------------------

class TestParallelComparator:
    def test_compare_all_pairs(self):
        comparator = ParallelComparator(max_workers=2)

        def compare(a, b):
            return 1.0 if a == b else 0.0

        results = comparator.compare_all_pairs(['x', 'x', 'x'], compare)
        assert len(results) == 3
        assert all(sim == 1.0 for _, _, sim in results)

    def test_compare_with_failing_func(self):
        comparator = ParallelComparator(max_workers=1)

        def compare(a, b):
            if a == 'poison':
                raise ValueError('boom')
            return 0.5

        results = comparator.compare_all_pairs(['poison', 'ok'], compare)
        sims = [sim for _, _, sim in results]
        assert 0.0 in sims  # failure recorded as 0.0

    def test_progress_callback(self):
        comparator = ParallelComparator(max_workers=2)
        seen = []
        # 10 files = 45 pairs; callback fires every 10 completions
        comparator.compare_all_pairs([str(i) for i in range(10)],
                                     lambda a, b: 1.0,
                                     progress_callback=lambda c, t: seen.append((c, t)))
        assert seen[-1][1] == 45

    def test_analyze_parallel_map(self):
        comparator = ParallelComparator(max_workers=2)
        results = comparator.map_parallel(str.upper, ['a', 'b', 'c'])
        assert sorted(results) == ['A', 'B', 'C']


class TestRateLimiter:
    def test_wait_respects_interval(self):
        limiter = RateLimiter(calls_per_second=1000)
        limiter.wait()
        limiter.wait()  # second call may sleep briefly — must not raise

    def test_batch_processor_batches(self):
        processor = BatchProcessor(batch_size=2)
        results = processor.process_in_batches([1, 2, 3, 4, 5], lambda batch: [x * 10 for x in batch])
        assert sorted(results) == [10, 20, 30, 40, 50]


# ---------------------------------------------------------------------------
# utils/alerts — trends, summary, helpers
# ---------------------------------------------------------------------------

class TestAlertsHelpers:
    def test_trend_increasing(self):
        monitor = PerformanceMonitor(get_alert_manager())
        monitor.record_metric('m', 1.0)
        monitor.record_metric('m', 5.0)
        monitor.record_metric('m', 9.0)
        trend = monitor.get_metric_trend('m', hours=1)
        assert trend['trend'] in ('increasing', 'stable')
        assert trend['max'] == 9.0

    def test_trend_with_old_data_excluded(self):
        from datetime import UTC, datetime, timedelta
        monitor = PerformanceMonitor(get_alert_manager())
        monitor.record_metric('m', 5.0)
        # Backdate beyond cutoff
        monitor._metrics_history['m'][0]['timestamp'] = (
            datetime.now(UTC) - timedelta(hours=48)).isoformat()
        trend = monitor.get_metric_trend('m', hours=1)
        assert trend == {'values': [], 'avg': 0, 'min': 0, 'max': 0, 'trend': 'stable'}

    def test_get_summary(self):
        monitor = PerformanceMonitor(get_alert_manager())
        monitor.record_metric('cpu', 55.0)
        summary = monitor.get_summary()
        assert summary['monitored_metrics_count'] == 1
        assert summary['metrics']['cpu']['last_value'] == 55.0
        assert 'alerts' in summary

    def test_global_singletons(self):
        assert get_alert_manager() is get_alert_manager()
        from utils.alerts import get_performance_monitor
        assert get_performance_monitor() is get_performance_monitor()

    def test_check_performance_alerts_fires(self):
        alerts = check_performance_alerts({'response_time': 99.0})
        assert any(a.metric_name == 'response_time' for a in alerts)

    def test_streamlit_guard_when_no_runtime(self):
        # display_alerts_ui early-returns without raising when st is None
        import utils.alerts as alerts_mod
        with patch.object(alerts_mod, 'st', None):
            alerts_mod.display_alerts_ui()  # must not raise


# ---------------------------------------------------------------------------
# utils/db_cache — remaining helpers
# ---------------------------------------------------------------------------

class TestDbCacheHelpers:
    def test_cached_query_decorator(self):
        calls = []

        @cached_query(ttl=60, key_prefix='test_')
        def fetch(x):
            calls.append(x)
            return x * 2

        assert fetch(5) == 10
        assert fetch(5) == 10
        assert len(calls) == 1

    def test_streamlit_cached_data_no_runtime(self):
        # Without a Streamlit runtime the decorator falls back to direct call
        @streamlit_cached_data(ttl=10)
        def data(x):
            return x + 1

        assert data(1) == 2

    def test_get_cache_stats_shape(self):
        from utils.db_cache import get_cache_stats
        stats = get_cache_stats()
        assert 'query_cache' in stats


# ---------------------------------------------------------------------------
# utils/exceptions + utils/logger + compression edges
# ---------------------------------------------------------------------------

class TestExceptionsAndMisc:
    def test_exception_hierarchy_str(self):
        for exc, message in (
            (NiklausError, 'base'),
            (ZipExtractionError, 'zip failed'),
            (LanguageDetectionError, 'unknown language'),
            (MaritacaAPIError, 'api down'),
            (CacheError, 'cache write failed'),
            (AnalysisCancelledError, 'cancelled'),
        ):
            assert message in str(exc(message))

    def test_logger_singleton_per_name(self):
        assert get_logger('same-name') is get_logger('same-name')

    def test_compression_stats_zero_original(self):
        stats = CompressionStats()
        assert stats.get_total_savings()['savings_percentage'] == 0

    def test_decompress_result_quick_function(self):
        from utils.compression import compress_result, decompress_result
        data = {'a': [1, 2, 3]}
        assert decompress_result(compress_result(data, level=1)) == data

    def test_get_compression_stats_singleton(self):
        assert get_compression_stats() is get_compression_stats()