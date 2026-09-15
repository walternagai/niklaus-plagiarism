"""
Tests for utils/alerts.py (AlertManager, PerformanceMonitor) and
utils/analytics.py (AnalyticsEngine).

Pure-logic tests — no Streamlit interaction (dashboard functions excluded).
"""

from datetime import UTC, datetime

from utils.alerts import AlertManager, PerformanceMonitor
from utils.analytics import AnalyticsEngine


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

class TestAlertManager:
    def test_unknown_metric_returns_none(self):
        assert AlertManager().check_metric('nonexistent_metric', 999) is None

    def test_below_threshold_returns_none(self):
        assert AlertManager().check_metric('response_time', 1.0) is None

    def test_warning_threshold_triggers_medium(self):
        alert = AlertManager().check_metric('response_time', 6.0)
        assert alert is not None
        assert alert.severity == 'medium'
        assert alert.metric_name == 'response_time'

    def test_critical_threshold_triggers_high(self):
        alert = AlertManager().check_metric('response_time', 11.0)
        assert alert.severity == 'high'

    def test_inverse_metric_cache_hit_rate(self):
        manager = AlertManager()
        # Below critical (20%) -> medium; between critical and warning -> low
        critical = manager.check_metric('cache_hit_rate', 10.0)
        warning = manager.check_metric('cache_hit_rate', 30.0)
        healthy = manager.check_metric('cache_hit_rate', 80.0)
        assert critical.severity == 'medium'
        assert warning.severity == 'low'
        assert healthy is None

    def test_custom_threshold(self):
        manager = AlertManager()
        manager.set_threshold('custom_metric', warning=1, critical=5)
        assert manager.check_metric('custom_metric', 2) is not None
        assert manager.check_metric('custom_metric', 0.5) is None

    def test_acknowledge_and_resolve(self):
        manager = AlertManager()
        alert = manager.check_metric('response_time', 6.0)
        assert manager.acknowledge_alert(alert.id) is True
        assert manager.resolve_alert(alert.id) is True
        assert manager.acknowledge_alert('missing_id') is False
        # Resolved alerts disappear from active list
        assert manager.get_active_alerts() == []

    def test_get_active_alerts_filters(self):
        manager = AlertManager()
        manager.check_metric('response_time', 6.0)     # medium
        manager.check_metric('memory_usage', 99.0)     # critical
        active = manager.get_active_alerts()
        assert len(active) == 2
        assert len(manager.get_active_alerts(severity='critical')) == 1
        assert len(manager.get_active_alerts(severity='low')) == 0

    def test_get_alert_stats(self):
        manager = AlertManager()
        alert = manager.check_metric('response_time', 6.0)
        manager.acknowledge_alert(alert.id)
        stats = manager.get_alert_stats()
        assert stats['total_alerts'] == 1
        assert stats['active_alerts'] == 1
        assert stats['acknowledged_alerts'] == 1
        assert stats['last_alert_time'] is not None

    def test_clear_old_alerts(self):
        manager = AlertManager()
        old = manager.check_metric('response_time', 6.0)
        old.timestamp = datetime.now(UTC).replace(year=2020)
        manager.clear_old_alerts(hours=24)
        assert manager._alerts == []

    def test_export_alerts_json(self):
        manager = AlertManager()
        manager.check_metric('response_time', 6.0)
        exported = manager.export_alerts()
        assert '"severity"' in exported
        assert '"metric_name": "response_time"' in exported

    def test_callback_notified_and_failure_swallowed(self):
        manager = AlertManager()
        received = []

        def callback(alert):
            received.append(alert)

        def broken_callback(alert):
            raise RuntimeError('boom')

        manager.register_callback(broken_callback)
        manager.register_callback(callback)
        manager.check_metric('response_time', 6.0)
        assert len(received) == 1  # broken callback did not stop the chain


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------

class TestPerformanceMonitor:
    def test_record_metric_stores_history_and_triggers_alert(self):
        manager = AlertManager()
        monitor = PerformanceMonitor(alert_manager=manager)
        monitor.record_metric('response_time', 1.0)
        monitor.record_metric('response_time', 6.0)  # above warning
        assert len(monitor._metrics_history['response_time']) == 2
        assert manager.get_active_alerts()  # alert fired

    def test_history_capped_at_max_size(self):
        monitor = PerformanceMonitor(alert_manager=AlertManager())
        for i in range(1010):
            monitor.record_metric('unknown_metric_no_alert', float(i))
        assert len(monitor._metrics_history['unknown_metric_no_alert']) == 1000

    def test_trend_stable_without_data(self):
        monitor = PerformanceMonitor(alert_manager=AlertManager())
        trend = monitor.get_metric_trend('missing')
        assert trend == {'values': [], 'avg': 0, 'min': 0, 'max': 0, 'trend': 'stable'}

    def test_trend_increasing(self):
        monitor = PerformanceMonitor(alert_manager=AlertManager())
        for v in [1, 2, 3, 4, 5]:
            monitor.record_metric('metric_x', float(v))
        trend = monitor.get_metric_trend('metric_x')
        assert trend['max'] == 5
        assert trend['avg'] == 3


# ---------------------------------------------------------------------------
# AnalyticsEngine
# ---------------------------------------------------------------------------

class TestAnalyticsEngine:
    def test_track_user_action_and_stats(self):
        engine = AnalyticsEngine()
        engine.track_user_action(1, 'login')
        engine.track_user_action(2, 'analysis', metadata={'lang': 'python'})
        stats = engine.get_user_stats(1, days=1)
        assert stats['total_actions'] == 1
        assert 'action_breakdown' in stats

    def test_track_analysis_populates_stats(self):
        engine = AnalyticsEngine()
        engine.track_analysis(submission_id=1, user_id=1, files_count=3,
                              suspicious_pairs_count=1, avg_similarity=0.5,
                              max_similarity=0.8, processing_time=2.0,
                              language='python', threshold=0.7)
        engine.track_analysis(submission_id=2, user_id=2, files_count=5,
                              suspicious_pairs_count=0, avg_similarity=0.2,
                              max_similarity=0.4, processing_time=3.0,
                              language='java', threshold=0.7)
        stats = engine.get_user_stats(1, days=1)
        assert stats['total_analyses'] == 1
        assert stats['total_files'] == 3

    def test_track_feature_usage(self):
        engine = AnalyticsEngine()
        engine.track_feature_usage(1, 'export_csv')
        assert engine.get_user_stats(1, days=1)['total_actions'] >= 1

    def test_daily_stats_retention_window(self):
        engine = AnalyticsEngine()
        engine.track_user_action(1, 'daily_event')
        # No crash and structure is a dict keyed by ISO date
        assert all(isinstance(v, dict) for v in engine._daily_stats.values())

    def test_get_analytics_singleton(self):
        from utils.analytics import get_analytics
        assert get_analytics() is get_analytics()

    def test_global_helpers_route_to_engine(self):
        from utils.analytics import get_analytics, track_user_action, track_analysis
        track_user_action(99, 'global_action')
        track_analysis(submission_id=1, user_id=99, files_count=1,
                       suspicious_pairs_count=0, avg_similarity=0.1,
                       max_similarity=0.1, processing_time=0.5,
                       language='python', threshold=0.7)
        stats = get_analytics().get_user_stats(99, days=1)
        assert stats['total_actions'] >= 1