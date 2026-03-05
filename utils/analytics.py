"""
Business analytics and metrics tracking system.
Tracks user behavior, usage patterns, and business metrics.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
import json

try:
    import streamlit as st
except ImportError:
    st = None


@dataclass
class UserMetric:
    """Represents a user behavior metric."""
    user_id: int
    metric_type: str
    metric_name: str
    value: Any
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class AnalysisMetric:
    """Represents an analysis execution metric."""
    submission_id: int
    user_id: int
    files_count: int
    suspicious_pairs_count: int
    avg_similarity: float
    max_similarity: float
    processing_time: float
    language: str
    threshold: float
    timestamp: datetime


class AnalyticsEngine:
    """
    Analytics engine for tracking business metrics.
    Collects and aggregates user behavior and system usage data.
    """
    
    def __init__(self):
        self._user_metrics: List[UserMetric] = []
        self._analysis_metrics: List[AnalysisMetric] = []
        self._daily_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(int))
        self._max_metrics_size = 10000
    
    def track_user_action(self, user_id: int, action: str, metadata: Dict[str, Any] = None):
        """
        Track user action for analytics.
        
        Args:
            user_id: User ID
            action: Action name (e.g., 'login', 'upload', 'analyze')
            metadata: Additional metadata
        """
        metric = UserMetric(
            user_id=user_id,
            metric_type='action',
            metric_name=action,
            value=1,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self._user_metrics.append(metric)
        self._trim_metrics('user')
        
        date_key = datetime.now().strftime('%Y-%m-%d')
        self._daily_stats[date_key][f'action_{action}'] += 1
    
    def track_analysis(self, submission_id: int, user_id: int, files_count: int,
                       suspicious_pairs_count: int, avg_similarity: float,
                       max_similarity: float, processing_time: float,
                       language: str, threshold: float):
        """
        Track analysis execution.
        
        Args:
            submission_id: Submission ID
            user_id: User ID
            files_count: Number of files analyzed
            suspicious_pairs_count: Number of suspicious pairs found
            avg_similarity: Average similarity score
            max_similarity: Maximum similarity score
            processing_time: Processing time in seconds
            language: Programming language
            threshold: Similarity threshold used
        """
        metric = AnalysisMetric(
            submission_id=submission_id,
            user_id=user_id,
            files_count=files_count,
            suspicious_pairs_count=suspicious_pairs_count,
            avg_similarity=avg_similarity,
            max_similarity=max_similarity,
            processing_time=processing_time,
            language=language,
            threshold=threshold,
            timestamp=datetime.now()
        )
        
        self._analysis_metrics.append(metric)
        self._trim_metrics('analysis')
        
        date_key = datetime.now().strftime('%Y-%m-%d')
        self._daily_stats[date_key]['analyses'] += 1
        self._daily_stats[date_key]['total_files'] += files_count
        self._daily_stats[date_key]['total_pairs'] += suspicious_pairs_count
        self._daily_stats[date_key]['total_time'] += processing_time
    
    def track_feature_usage(self, user_id: int, feature: str, details: Dict[str, Any] = None):
        """
        Track feature usage.
        
        Args:
            user_id: User ID
            feature: Feature name
            details: Feature usage details
        """
        metric = UserMetric(
            user_id=user_id,
            metric_type='feature',
            metric_name=feature,
            value=1,
            timestamp=datetime.now(),
            metadata=details or {}
        )
        
        self._user_metrics.append(metric)
        self._trim_metrics('user')
        
        date_key = datetime.now().strftime('%Y-%m-%d')
        self._daily_stats[date_key][f'feature_{feature}'] += 1
    
    def track_performance(self, operation: str, duration: float, success: bool, metadata: Dict[str, Any] = None):
        """
        Track operation performance.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            success: Whether operation succeeded
            metadata: Additional metadata
        """
        metric_type = 'performance'
        
        date_key = datetime.now().strftime('%Y-%m-%d')
        self._daily_stats[date_key][f'perf_{operation}_count'] += 1
        self._daily_stats[date_key][f'perf_{operation}_time'] += duration
        
        if not success:
            self._daily_stats[date_key][f'perf_{operation}_errors'] += 1
    
    def _trim_metrics(self, metric_type: str):
        """Trim metrics to max size."""
        if metric_type == 'user':
            if len(self._user_metrics) > self._max_metrics_size:
                self._user_metrics = self._user_metrics[-self._max_metrics_size:]
        elif metric_type == 'analysis':
            if len(self._analysis_metrics) > self._max_metrics_size:
                self._analysis_metrics = self._analysis_metrics[-self._max_metrics_size:]
    
    def get_user_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to include
            
        Returns:
            User statistics
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        user_actions = [
            m for m in self._user_metrics
            if m.user_id == user_id and m.timestamp > cutoff
        ]
        
        user_analyses = [
            m for m in self._analysis_metrics
            if m.user_id == user_id and m.timestamp > cutoff
        ]
        
        action_counts = defaultdict(int)
        for action in user_actions:
            action_counts[action.metric_name] += 1
        
        total_files = sum(m.files_count for m in user_analyses)
        total_pairs = sum(m.suspicious_pairs_count for m in user_analyses)
        total_time = sum(m.processing_time for m in user_analyses)
        
        language_counts = defaultdict(int)
        for analysis in user_analyses:
            language_counts[analysis.language] += 1
        
        return {
            'total_actions': len(user_actions),
            'total_analyses': len(user_analyses),
            'total_files': total_files,
            'total_suspicious_pairs': total_pairs,
            'total_processing_time': total_time,
            'action_breakdown': dict(action_counts),
            'language_breakdown': dict(language_counts),
            'avg_similarity': sum(m.avg_similarity for m in user_analyses) / len(user_analyses) if user_analyses else 0,
            'max_similarity': max(m.max_similarity for m in user_analyses) if user_analyses else 0
        }
    
    def get_global_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get global statistics.
        
        Args:
            days: Number of days to include
            
        Returns:
            Global statistics
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        date_keys = [
            (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(days)
        ]
        
        stats = {
            'total_analyses': 0,
            'total_files': 0,
            'total_suspicious_pairs': 0,
            'total_processing_time': 0.0,
            'unique_users': set(),
            'languages': defaultdict(int),
            'daily_breakdown': []
        }
        
        for date_key in date_keys:
            if date_key in self._daily_stats:
                day_stats = self._daily_stats[date_key]
                stats['total_analyses'] += day_stats.get('analyses', 0)
                stats['total_files'] += day_stats.get('total_files', 0)
                stats['total_suspicious_pairs'] += day_stats.get('total_pairs', 0)
                stats['total_processing_time'] += day_stats.get('total_time', 0.0)
                
                stats['daily_breakdown'].append({
                    'date': date_key,
                    'analyses': day_stats.get('analyses', 0),
                    'files': day_stats.get('total_files', 0),
                    'pairs': day_stats.get('total_pairs', 0),
                    'time': day_stats.get('total_time', 0.0)
                })
        
        recent_analyses = [
            m for m in self._analysis_metrics
            if m.timestamp > cutoff
        ]
        
        for analysis in recent_analyses:
            stats['unique_users'].add(analysis.user_id)
            stats['languages'][analysis.language] += 1
        
        stats['unique_users'] = len(stats['unique_users'])
        stats['languages'] = dict(stats['languages'])
        
        if recent_analyses:
            stats['avg_similarity'] = sum(m.avg_similarity for m in recent_analyses) / len(recent_analyses)
            stats['max_similarity'] = max(m.max_similarity for m in recent_analyses)
            stats['avg_processing_time'] = sum(m.processing_time for m in recent_analyses) / len(recent_analyses)
        else:
            stats['avg_similarity'] = 0
            stats['max_similarity'] = 0
            stats['avg_processing_time'] = 0
        
        return stats
    
    def get_usage_patterns(self, days: int = 7) -> Dict[str, Any]:
        """
        Get usage patterns.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Usage patterns
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        hourly_usage = defaultdict(int)
        daily_usage = defaultdict(int)
        language_usage = defaultdict(int)
        threshold_usage = defaultdict(int)
        
        for metric in self._analysis_metrics:
            if metric.timestamp > cutoff:
                hour_key = metric.timestamp.strftime('%Y-%m-%d %H:00')
                hourly_usage[hour_key] += 1
                
                day_key = metric.timestamp.strftime('%Y-%m-%d')
                daily_usage[day_key] += 1
                
                language_usage[metric.language] += 1
                threshold_usage[f"{metric.threshold:.1f}"] += 1
        
        hourly_peak = max(hourly_usage.values()) if hourly_usage else 0
        peak_hour = max(hourly_usage.keys(), key=lambda k: hourly_usage[k]) if hourly_usage else None
        
        return {
            'hourly_usage': dict(hourly_usage),
            'daily_usage': dict(daily_usage),
            'language_distribution': dict(language_usage),
            'threshold_distribution': dict(threshold_usage),
            'peak_hour': peak_hour,
            'peak_usage': hourly_peak,
            'average_daily_usage': sum(daily_usage.values()) / len(daily_usage) if daily_usage else 0
        }
    
    def get_trending_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get trending metrics for dashboard.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Trending metrics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_analyses = [
            m for m in self._analysis_metrics
            if m.timestamp > cutoff
        ]
        
        if not recent_analyses:
            return {
                'analyses_count': 0,
                'avg_processing_time': 0,
                'avg_similarity': 0,
                'files_per_analysis': 0,
                'trend': 'stable'
            }
        
        analyses_count = len(recent_analyses)
        avg_processing_time = sum(m.processing_time for m in recent_analyses) / analyses_count
        avg_similarity = sum(m.avg_similarity for m in recent_analyses) / analyses_count
        files_per_analysis = sum(m.files_count for m in recent_analyses) / analyses_count
        
        if len(recent_analyses) >= 2:
            half_point = len(recent_analyses) // 2
            recent_half = recent_analyses[-half_point:]
            older_half = recent_analyses[:half_point]
            
            recent_count = len(recent_half)
            older_count = len(older_half)
            
            if older_count == 0:
                trend = 'increasing'
            else:
                rate_change = (recent_count - older_count) / older_count
                
                if rate_change > 0.2:
                    trend = 'increasing'
                elif rate_change < -0.2:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'analyses_count': analyses_count,
            'avg_processing_time': avg_processing_time,
            'avg_similarity': avg_similarity,
            'files_per_analysis': files_per_analysis,
            'trend': trend
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        Export metrics for external analysis.
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Exported metrics string
        """
        if format == 'json':
            data = {
                'user_metrics': [
                    {
                        'user_id': m.user_id,
                        'type': m.metric_type,
                        'name': m.metric_name,
                        'value': m.value,
                        'timestamp': m.timestamp.isoformat(),
                        'metadata': m.metadata
                    }
                    for m in self._user_metrics
                ],
                'analysis_metrics': [
                    {
                        'submission_id': m.submission_id,
                        'user_id': m.user_id,
                        'files_count': m.files_count,
                        'suspicious_pairs_count': m.suspicious_pairs_count,
                        'avg_similarity': m.avg_similarity,
                        'max_similarity': m.max_similarity,
                        'processing_time': m.processing_time,
                        'language': m.language,
                        'threshold': m.threshold,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in self._analysis_metrics
                ]
            }
            return json.dumps(data, indent=2)
        
        elif format == 'csv':
            lines = ['type,user_id,name,value,timestamp']
            
            for m in self._user_metrics:
                lines.append(f"action,{m.user_id},{m.metric_name},{m.value},{m.timestamp.isoformat()}")
            
            for m in self._analysis_metrics:
                lines.append(f"analysis,{m.user_id},files_count,{m.files_count},{m.timestamp.isoformat()}")
                lines.append(f"analysis,{m.user_id},suspicious_pairs,{m.suspicious_pairs_count},{m.timestamp.isoformat()}")
                lines.append(f"analysis,{m.user_id},processing_time,{m.processing_time},{m.timestamp.isoformat()}")
            
            return '\n'.join(lines)
        
        return ''


_global_analytics: Optional[AnalyticsEngine] = None


def get_analytics() -> AnalyticsEngine:
    """Get global analytics engine instance."""
    global _global_analytics
    if _global_analytics is None:
        _global_analytics = AnalyticsEngine()
    return _global_analytics


def track_user_action(user_id: int, action: str, metadata: Dict[str, Any] = None):
    """Quick function to track user action."""
    analytics = get_analytics()
    analytics.track_user_action(user_id, action, metadata)


def track_analysis(submission_id: int, user_id: int, files_count: int,
                   suspicious_pairs_count: int, avg_similarity: float,
                   max_similarity: float, processing_time: float,
                   language: str, threshold: float):
    """Quick function to track analysis."""
    analytics = get_analytics()
    analytics.track_analysis(
        submission_id, user_id, files_count, suspicious_pairs_count,
        avg_similarity, max_similarity, processing_time, language, threshold
    )


def display_analytics_dashboard():
    """Display analytics dashboard in Streamlit."""
    if st is None:
        return
    
    analytics = get_analytics()
    
    st.markdown("### 📊 Analytics Dashboard")
    
    global_stats = analytics.get_global_stats(days=30)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total de Análises",
            global_stats['total_analyses'],
            help="Análises realizadas nos últimos 30 dias"
        )
    
    with col2:
        st.metric(
            "Usuários Únicos",
            global_stats['unique_users'],
            help="Usuários ativos nos últimos 30 dias"
        )
    
    with col3:
        st.metric(
            "Arquivos Analisados",
            global_stats['total_files'],
            help="Total de arquivos processados"
        )
    
    with col4:
        st.metric(
            "Tempo Médio",
            f"{global_stats['avg_processing_time']:.2f}s",
            help="Tempo médio de processamento"
        )
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "📊 Padrões", "🎯 Trends"])
    
    with tab1:
        _render_global_overview(global_stats)
    
    with tab2:
        usage_patterns = analytics.get_usage_patterns(days=7)
        _render_usage_patterns(usage_patterns)
    
    with tab3:
        trending = analytics.get_trending_metrics(hours=24)
        _render_trending(trending)


def _render_global_overview(global_stats: Dict[str, Any]):
    """Render global statistics."""
    st.markdown("#### 📈 Estatísticas Globais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Por Linguagem:**")
        if global_stats['languages']:
            for lang, count in sorted(global_stats['languages'].items(), 
                                     key=lambda x: x[1], reverse=True):
                st.write(f"- {lang}: {count} análises")
        else:
            st.info("Nenhum dado disponível")
    
    with col2:
        st.markdown("**Métricas de Similaridade:**")
        st.metric("Similaridade Média", f"{global_stats['avg_similarity']:.2%}")
        st.metric("Similaridade Máxima", f"{global_stats['max_similarity']:.2%}")
    
    if global_stats['daily_breakdown']:
        st.markdown("#### 📅 Análises por Dia")
        
        for day in global_stats['daily_breakdown'][-7:]:
            st.write(f"**{day['date']}**: {day['analyses']} análises, {day['files']} arquivos")


def _render_usage_patterns(usage_patterns: Dict[str, Any]):
    """Render usage patterns."""
    st.markdown("#### 📊 Padrões de Uso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Por Linguagem:**")
        if usage_patterns['language_distribution']:
            for lang, count in sorted(usage_patterns['language_distribution'].items(),
                                     key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"- {lang}: {count} análises")
    
    with col2:
        st.markdown("**Por Threshold:**")
        if usage_patterns['threshold_distribution']:
            for threshold, count in sorted(usage_patterns['threshold_distribution'].items()):
                st.write(f"- {threshold}: {count} análises")
    
    if usage_patterns['peak_hour']:
        st.markdown("#### ⏰ Pico de Uso")
        st.write(f"**Horário de pico**: {usage_patterns['peak_hour']}")
        st.write(f"**Uso máximo**: {usage_patterns['peak_usage']} análises/hora")
        st.write(f"**Média diária**: {usage_patterns['average_daily_usage']:.1f} análises/dia")


def _render_trending(trending: Dict[str, Any]):
    """Render trending metrics."""
    st.markdown("#### 🎯 Tendências (24h)")
    
    trend_emoji = {
        'increasing': '📈',
        'decreasing': '📉',
        'stable': '➡️'
    }
    
    emoji = trend_emoji.get(trending['trend'], '➡️')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Análises", trending['analyses_count'])
        st.metric("Tempo Médio", f"{trending['avg_processing_time']:.2f}s")
    
    with col2:
        st.metric("Arquivos/Análise", f"{trending['files_per_analysis']:.1f}")
        st.metric("Similaridade Média", f"{trending['avg_similarity']:.2%}")
    
    st.markdown(f"**Tendência**: {emoji} {trending['trend'].capitalize()}")