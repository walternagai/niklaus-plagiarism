"""
Tests for utils/performance.py and utils/error_handling.py.

Streamlit display functions (display_performance_report, display_error,
suggest_*) are excluded — the pure logic below is fully covered.
"""

import pytest

import utils.error_handling as error_handling
from utils.exceptions import FileValidationError
from utils.performance import (
    PerformanceContext,
    PerformanceMetrics,
    get_performance_dashboard,
    get_performance_metrics,
    measure_time,
    track_performance,
)


# ---------------------------------------------------------------------------
# PerformanceMetrics
# ---------------------------------------------------------------------------

class TestPerformanceMetrics:
    def test_record_and_get_stats(self):
        metrics = PerformanceMetrics()
        metrics.record('op', 1.0)
        metrics.record('op', 3.0)
        stats = metrics.get_stats('op')
        assert stats['count'] == 2
        assert stats['avg_time'] == 2.0
        assert stats['min_time'] == 1.0
        assert stats['max_time'] == 3.0
        assert stats['success_rate'] == 100.0

    def test_error_counting(self):
        metrics = PerformanceMetrics()
        metrics.record('flaky', 1.0, success=True)
        metrics.record('flaky', 2.0, success=False, error='boom')
        stats = metrics.get_stats('flaky')
        assert stats['error_count'] == 1
        assert stats['success_rate'] == 50.0

    def test_empty_metric_returns_zeroed_stats(self):
        stats = PerformanceMetrics().get_stats('never_recorded')
        assert stats['count'] == 0
        assert stats['avg_time'] == 0
        assert stats['success_rate'] == 100.0

    def test_get_all_stats_and_clear(self):
        metrics = PerformanceMetrics()
        metrics.record('a', 1.0)
        metrics.record('b', 2.0)
        assert set(metrics.get_all_stats().keys()) == {'a', 'b'}
        metrics.clear()
        assert metrics.get_all_stats() == {}

    def test_top_slow_orders_by_avg(self):
        metrics = PerformanceMetrics()
        metrics.record('fast', 0.1)
        metrics.record('slow', 5.0)
        top = metrics.get_top_slow(2)
        assert top[0]['name'] == 'slow'

    def test_top_frequent_orders_by_count(self):
        metrics = PerformanceMetrics()
        for _ in range(3):
            metrics.record('hot', 1.0)
        metrics.record('cold', 1.0)
        assert metrics.get_top_frequent(2)[0]['name'] == 'hot'


# ---------------------------------------------------------------------------
# track_performance / PerformanceContext / measure_time
# ---------------------------------------------------------------------------

class TestTrackPerformance:
    def setup_method(self):
        get_performance_metrics().clear()

    def test_named_metric_records_success(self):
        @track_performance('db.query')
        def query():
            return 42

        assert query() == 42
        stats = get_performance_metrics().get_stats('db.query')
        assert stats['count'] == 1
        assert stats['error_count'] == 0

    def test_default_name_is_function_name(self):
        @track_performance()
        def my_operation():
            return 'done'

        my_operation()
        assert get_performance_metrics().get_stats('my_operation')['count'] == 1

    def test_failure_recorded_and_reraised(self):
        @track_performance('failing')
        def failing():
            raise RuntimeError('x')

        with pytest.raises(RuntimeError):
            failing()
        stats = get_performance_metrics().get_stats('failing')
        assert stats['error_count'] == 1

    def test_global_singleton(self):
        assert get_performance_metrics() is get_performance_metrics()

    def test_context_manager_success_and_failure(self):
        with PerformanceContext('ctx.ok'):
            pass
        assert get_performance_metrics().get_stats('ctx.ok')['count'] == 1

        with pytest.raises(ValueError, match='boom'):
            with PerformanceContext('ctx.fail'):
                raise ValueError('boom')
        stats = get_performance_metrics().get_stats('ctx.fail')
        assert stats['error_count'] == 1
        assert stats['count'] == 1

    def test_measure_time_returns_result(self, capsys):
        @measure_time
        def add(a, b):
            return a + b

        assert add(2, 3) == 5
        assert 'add took' in capsys.readouterr().out

    def test_dashboard_aggregates(self):
        metrics = get_performance_metrics()
        metrics.record('op', 1.0)
        dashboard = get_performance_dashboard()
        assert dashboard['summary']['total_calls'] == 1
        assert 'top_slow' in dashboard and 'top_frequent' in dashboard


# ---------------------------------------------------------------------------
# error_handling — pure functions
# ---------------------------------------------------------------------------

class TestErrorHandlingPure:
    def test_estimate_analysis_time_seconds(self):
        result = error_handling.estimate_analysis_time(10, enable_ai=False, max_workers=4)
        assert 'segundos' in result

    def test_estimate_analysis_time_ai_slower(self):
        fast = error_handling.estimate_analysis_time(10, False, 4)
        slow = error_handling.estimate_analysis_time(10, True, 4)
        assert slow != fast

    def test_estimate_analysis_time_minutes(self):
        result = error_handling.estimate_analysis_time(1000, False, 1)
        assert 'minuto' in result

    def test_estimate_analysis_time_hours(self):
        result = error_handling.estimate_analysis_time(10000, True, 1)
        assert 'hora' in result

    def test_check_file_validity_ok(self):
        assert error_handling.check_file_validity(10, 5.0) is None

    def test_check_file_validity_multiple_warnings(self):
        result = error_handling.check_file_validity(150, 60.0)
        assert 'Muitos arquivos' in result
        assert 'Arquivo grande' in result

    def test_check_file_validity_minimum(self):
        assert 'Mínimo de 2 arquivos' in error_handling.check_file_validity(1, 1.0)


# ---------------------------------------------------------------------------
# error_handling — display_error with mocked Streamlit
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_st():
    """Patch streamlit inside utils.error_handling."""
    from unittest.mock import MagicMock, patch
    from types import SimpleNamespace

    fake = SimpleNamespace(
        error=MagicMock(), warning=MagicMock(), info=MagicMock(),
        markdown=MagicMock(), stop=MagicMock(), caption=MagicMock(),
    )
    with patch.object(error_handling.st, 'error', fake.error), \
         patch.object(error_handling.st, 'warning', fake.warning), \
         patch.object(error_handling.st, 'info', fake.info), \
         patch.object(error_handling.st, 'markdown', fake.markdown):
        yield fake


class TestDisplayError:
    def test_niklaus_error_custom_display(self, fake_st):
        err = FileValidationError('arquivo grande demais')
        error_handling.display_error(err)
        fake_st.error.assert_called()

    def test_generic_exception_shows_context(self, fake_st):
        error_handling.display_error(ValueError('generic failure'), context='upload')
        fake_st.error.assert_called()

    def test_display_file_error_mentions_size(self, fake_st):
        error_handling._display_file_error(
            FileValidationError('excede o tamanho máximo'))
        assert fake_st.error.called or fake_st.warning.called

    def test_display_api_error(self, fake_st):
        error_handling._display_api_error(error_handling.APIError('rate limit'))
        fake_st.error.assert_called()

    def test_suggestions_markdown(self, fake_st):
        error_handling.suggest_file_solutions()
        error_handling.suggest_performance_improvements()
        assert fake_st.markdown.call_count >= 2