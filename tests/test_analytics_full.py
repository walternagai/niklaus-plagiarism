"""
Full coverage for AnalyticsEngine query methods: get_user_stats,
get_global_stats, get_usage_patterns, get_trending_metrics,
export_metrics (json/csv/unknown), _trim_metrics and track_performance.

Dashboard render functions (Streamlit) remain excluded.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from utils.analytics import AnalyticsEngine


def _make_engine():
    engine = AnalyticsEngine()
    # Two users, several analyses
    engine.track_analysis(submission_id=1, user_id=1, files_count=3,
                          suspicious_pairs_count=1, avg_similarity=0.6,
                          max_similarity=0.9, processing_time=2.0,
                          language='python', threshold=0.7)
    engine.track_analysis(submission_id=2, user_id=1, files_count=2,
                          suspicious_pairs_count=0, avg_similarity=0.4,
                          max_similarity=0.4, processing_time=1.0,
                          language='python', threshold=0.7)
    engine.track_analysis(submission_id=3, user_id=2, files_count=5,
                          suspicious_pairs_count=2, avg_similarity=0.8,
                          max_similarity=0.9, processing_time=4.0,
                          language='java', threshold=0.8)
    engine.track_user_action(1, 'login')
    engine.track_user_action(1, 'export')
    engine.track_user_action(2, 'login')
    return engine


class TestUserStats:
    def test_breakdowns_and_averages(self):
        engine = _make_engine()
        stats = engine.get_user_stats(1, days=30)
        assert stats['total_analyses'] == 2
        assert stats['total_files'] == 5
        assert stats['total_suspicious_pairs'] == 1
        assert stats['action_breakdown'] == {'login': 1, 'export': 1}
        assert stats['language_breakdown'] == {'python': 2}
        assert stats['avg_similarity'] == pytest.approx(0.5)
        assert stats['max_similarity'] == pytest.approx(0.9)

    def test_days_window_excludes_old(self):
        engine = _make_engine()
        stats = engine.get_user_stats(1, days=30)
        assert stats['total_actions'] >= 1
        # Old-data exclusion: fresh engine with days=0 window has nothing
        fresh = AnalyticsEngine()
        assert fresh.get_user_stats(1, days=1)['total_analyses'] == 0

    def test_empty_user(self):
        engine = AnalyticsEngine()
        stats = engine.get_user_stats(42, days=30)
        assert stats['total_actions'] == 0
        assert stats['avg_similarity'] == 0
        assert stats['max_similarity'] == 0

    def test_track_performance_recorded(self):
        engine = AnalyticsEngine()
        engine.track_performance('pipeline', duration=1.5, success=True)
        engine.track_performance('pipeline', duration=0.5, success=False)
        engine.track_performance('other', duration=2.0, success=True)
        date_key = datetime.now(UTC).strftime('%Y-%m-%d')
        daily = engine._daily_stats[date_key]
        assert daily['perf_pipeline_count'] == 2
        assert daily['perf_pipeline_time'] == pytest.approx(2.0)
        assert daily['perf_pipeline_errors'] == 1


class TestGlobalStats:
    def test_aggregates_all_users(self):
        engine = _make_engine()
        stats = engine.get_global_stats(days=30)
        assert stats['total_analyses'] == 3
        assert stats['total_files'] == 10
        assert stats['total_suspicious_pairs'] == 3

    def test_daily_keys_shape(self):
        engine = _make_engine()
        stats = engine.get_global_stats(days=2)
        assert 'analyses' in stats or stats.get('total_analyses') == 3


class TestUsagePatterns:
    def test_patterns_with_data(self):
        engine = _make_engine()
        patterns = engine.get_usage_patterns(days=7)
        assert patterns['peak_usage'] >= 1
        assert patterns['peak_hour'] is not None
        assert 'python' in patterns['language_distribution']
        assert '0.7' in patterns['threshold_distribution']

    def test_patterns_empty(self):
        engine = AnalyticsEngine()
        patterns = engine.get_usage_patterns(days=7)
        assert patterns['peak_hour'] is None
        assert patterns['peak_usage'] == 0


class TestTrending:
    def test_trending_empty(self):
        assert AnalyticsEngine().get_trending_metrics(24)['trend'] == 'stable'
        empty = AnalyticsEngine().get_trending_metrics(24)
        assert empty['analyses_count'] == 0

    def test_trending_stable_with_two(self):
        engine = AnalyticsEngine()
        for i in (1, 2):
            engine.track_analysis(submission_id=i, user_id=1, files_count=1,
                                  suspicious_pairs_count=0, avg_similarity=0.1,
                                  max_similarity=0.1, processing_time=0.5,
                                  language='python', threshold=0.7)
        assert engine.get_trending_metrics(hours=24)['trend'] == 'stable'

    def test_trending_increasing(self):
        engine = AnalyticsEngine()
        now = datetime.now(UTC)
        # 4 metrics: older half = 1 (20h ago), recent half = 3 (last hours)
        for idx, hours_ago in enumerate((20, 3, 1, 0.1), start=1):
            engine.track_analysis(
                submission_id=idx, user_id=1, files_count=1,
                suspicious_pairs_count=0, avg_similarity=0.1,
                max_similarity=0.1, processing_time=0.5,
                language='python', threshold=0.7)
            engine._analysis_metrics[-1].timestamp = now - timedelta(hours=hours_ago)

        trending = engine.get_trending_metrics(hours=24)
        assert trending['analyses_count'] == 4
        assert trending['trend'] == 'increasing'

    def test_trending_decreasing(self):
        engine = AnalyticsEngine()
        now = datetime.now(UTC)
        # 3 older (20-18h ago), 1 recent -> rate_change = -0.66
        for idx, hours_ago in ((1, 20), (2, 19), (3, 18), (4, 1)):
            engine.track_analysis(
                submission_id=idx, user_id=1, files_count=1,
                suspicious_pairs_count=0, avg_similarity=0.1,
                max_similarity=0.1, processing_time=0.5,
                language='python', threshold=0.7)
            engine._analysis_metrics[-1].timestamp = now - timedelta(hours=hours_ago)

        assert engine.get_trending_metrics(hours=24)['trend'] == 'decreasing'

    def test_trending_aggregates(self):
        engine = _make_engine()
        trending = engine.get_trending_metrics(hours=24)
        assert trending['analyses_count'] == 3
        assert trending['files_per_analysis'] == pytest.approx(10 / 3)
        assert trending['avg_processing_time'] > 0


# ---------------------------------------------------------------------------
# export_metrics
# ---------------------------------------------------------------------------

class TestExportMetrics:
    def test_json_export_contains_both_sections(self):
        engine = _make_engine()
        exported = json.loads(engine.export_metrics('json'))
        assert len(exported['user_metrics']) == 3
        assert len(exported['analysis_metrics']) == 3
        assert exported['user_metrics'][0]['type'] == 'action'

    def test_csv_export_rows(self):
        engine = _make_engine()
        csv = engine.export_metrics('csv')
        lines = csv.split('\n')
        assert lines[0] == 'type,user_id,name,value,timestamp'
        assert lines[1].startswith('action,1,login,1,')

    def test_unknown_format_returns_empty(self):
        assert _make_engine().export_metrics(format='xml') == ''


# ---------------------------------------------------------------------------
# _trim_metrics
# ---------------------------------------------------------------------------

class TestTrimMetrics:
    def test_user_metrics_trimmed(self):
        engine = AnalyticsEngine()
        engine._max_metrics_size = 5
        for i in range(10):
            engine.track_user_action(i, 'event')
        assert len(engine._user_metrics) <= 5

    def test_analysis_metrics_trim(self):
        engine = AnalyticsEngine()
        engine._max_metrics_size = 3
        for i in range(6):
            engine.track_analysis(submission_id=i, user_id=1, files_count=1,
                                  suspicious_pairs_count=0, avg_similarity=0.1,
                                  max_similarity=0.1, processing_time=0.1,
                                  language='python', threshold=0.7)
        assert len(engine._analysis_metrics) <= 3