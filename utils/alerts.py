"""
Performance alerts and monitoring system.
Automatically detects performance issues and triggers alerts.
"""

import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
import json

try:
    import streamlit as st
except ImportError:
    st = None


@dataclass
class Alert:
    """Represents a performance alert."""
    id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    category: str  # 'performance', 'error', 'cache', 'database'
    message: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: datetime
    details: Dict[str, Any]
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None


class AlertManager:
    """
    Manages performance alerts with threshold monitoring.
    Tracks alerts history and provides notification mechanisms.
    """
    
    def __init__(self):
        self._alerts: List[Alert] = []
        self._thresholds: Dict[str, Dict[str, Any]] = self._initialize_thresholds()
        self._callbacks: List[Callable] = []
    
    def _initialize_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default alert thresholds."""
        return {
            'response_time': {
                'warning': 5.0,  # 5 seconds
                'critical': 10.0,  # 10 seconds
                'severity_warning': 'medium',
                'severity_critical': 'high',
                'metric_type': 'time'
            },
            'error_rate': {
                'warning': 5.0,  # 5% error rate
                'critical': 15.0,  # 15% error rate
                'severity_warning': 'medium',
                'severity_critical': 'critical',
                'metric_type': 'percentage'
            },
            'cache_hit_rate': {
                'warning': 50.0,  # Below 50% hit rate
                'critical': 20.0,  # Below 20% hit rate
                'severity_warning': 'low',
                'severity_critical': 'medium',
                'metric_type': 'percentage',
                'inverse': True  # Lower is worse
            },
            'slow_query_count': {
                'warning': 10,  # More than 10 slow queries
                'critical': 50,  # More than 50 slow queries
                'severity_warning': 'medium',
                'severity_critical': 'high',
                'metric_type': 'count'
            },
            'memory_usage': {
                'warning': 80.0,  # 80% memory usage
                'critical': 95.0,  # 95% memory usage
                'severity_warning': 'high',
                'severity_critical': 'critical',
                'metric_type': 'percentage'
            },
            'concurrent_users': {
                'warning': 50,  # More than 50 concurrent users
                'critical': 100,  # More than 100 concurrent users
                'severity_warning': 'low',
                'severity_critical': 'medium',
                'metric_type': 'count'
            }
        }
    
    def set_threshold(self, metric_name: str, warning: float, critical: float, 
                      severity_warning: str = 'medium', severity_critical: str = 'high'):
        """Set custom threshold for a metric."""
        self._thresholds[metric_name] = {
            'warning': warning,
            'critical': critical,
            'severity_warning': severity_warning,
            'severity_critical': severity_critical,
            'metric_type': 'custom'
        }
    
    def check_metric(self, metric_name: str, value: float, details: Dict[str, Any] = None) -> Optional[Alert]:
        """
        Check if metric value triggers an alert.
        
        Args:
            metric_name: Name of the metric to check
            value: Current metric value
            details: Additional details about the metric
            
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if metric_name not in self._thresholds:
            return None
        
        threshold_config = self._thresholds[metric_name]
        threshold_warning = threshold_config['warning']
        threshold_critical = threshold_config['critical']
        inverse = threshold_config.get('inverse', False)
        
        if inverse:
            if value < threshold_critical:
                severity = threshold_config['severity_critical']
                threshold = threshold_critical
            elif value < threshold_warning:
                severity = threshold_config['severity_warning']
                threshold = threshold_warning
            else:
                return None
        else:
            if value > threshold_critical:
                severity = threshold_config['severity_critical']
                threshold = threshold_critical
            elif value > threshold_warning:
                severity = threshold_config['severity_warning']
                threshold = threshold_warning
            else:
                return None
        
        alert = Alert(
            id=f"{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            severity=severity,
            category=self._get_category(metric_name),
            message=self._generate_message(metric_name, value, threshold, severity),
            metric_name=metric_name,
            threshold=threshold,
            current_value=value,
            timestamp=datetime.now(),
            details=details or {},
            acknowledged=False
        )
        
        self._alerts.append(alert)
        self._notify_callbacks(alert)
        
        return alert
    
    def _get_category(self, metric_name: str) -> str:
        """Get alert category from metric name."""
        if 'time' in metric_name or 'response' in metric_name:
            return 'performance'
        elif 'error' in metric_name:
            return 'error'
        elif 'cache' in metric_name:
            return 'cache'
        elif 'query' in metric_name or 'database' in metric_name:
            return 'database'
        else:
            return 'general'
    
    def _generate_message(self, metric_name: str, value: float, threshold: float, 
                          severity: str) -> str:
        """Generate human-readable alert message."""
        severity_emoji = {
            'low': '⚠️',
            'medium': '🔶',
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_emoji.get(severity, '⚠️')
        metric_type = self._thresholds.get(metric_name, {}).get('metric_type', 'value')
        
        if metric_type == 'time':
            return f"{emoji} High response time for {metric_name}: {value:.2f}s (threshold: {threshold:.2f}s)"
        elif metric_type == 'percentage':
            if self._thresholds.get(metric_name, {}).get('inverse'):
                return f"{emoji} Low {metric_name}: {value:.1f}% (threshold: {threshold:.1f}%)"
            else:
                return f"{emoji} High {metric_name}: {value:.1f}% (threshold: {threshold:.1f}%)"
        elif metric_type == 'count':
            return f"{emoji} High count for {metric_name}: {value} (threshold: {threshold})"
        else:
            return f"{emoji} Alert for {metric_name}: {value} (threshold: {threshold})"
    
    def register_callback(self, callback: Callable):
        """Register a callback to be notified when alerts are triggered."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, alert: Alert):
        """Notify all registered callbacks about new alert."""
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception:
                pass
    
    def get_active_alerts(self, severity: Optional[str] = None, 
                          category: Optional[str] = None,
                          limit: int = 100) -> List[Alert]:
        """Get active (non-resolved) alerts."""
        alerts = [a for a in self._alerts if not a.resolved_at]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark alert as acknowledged."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.resolved_at = datetime.now()
                return True
        return False
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active_alerts = [a for a in self._alerts if not a.resolved_at]
        
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for alert in active_alerts:
            severity_counts[alert.severity] += 1
            category_counts[alert.category] += 1
        
        return {
            'total_alerts': len(self._alerts),
            'active_alerts': len(active_alerts),
            'acknowledged_alerts': len([a for a in active_alerts if a.acknowledged]),
            'severity_breakdown': dict(severity_counts),
            'category_breakdown': dict(category_counts),
            'last_alert_time': max(a.timestamp for a in self._alerts) if self._alerts else None
        }
    
    def clear_old_alerts(self, hours: int = 24):
        """Remove alerts older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        self._alerts = [a for a in self._alerts if a.timestamp > cutoff]
    
    def export_alerts(self) -> str:
        """Export alerts as JSON."""
        alerts_data = []
        for alert in self._alerts:
            alerts_data.append({
                'id': alert.id,
                'severity': alert.severity,
                'category': alert.category,
                'message': alert.message,
                'metric_name': alert.metric_name,
                'threshold': alert.threshold,
                'current_value': alert.current_value,
                'timestamp': alert.timestamp.isoformat(),
                'acknowledged': alert.acknowledged,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'details': alert.details
            })
        return json.dumps(alerts_data, indent=2)


class PerformanceMonitor:
    """
    Monitors application performance and triggers alerts.
    Tracks metrics over time and identifies trends.
    """
    
    def __init__(self, alert_manager: AlertManager = None):
        self.alert_manager = alert_manager or AlertManager()
        self._metrics_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._max_history_size = 1000
    
    def record_metric(self, metric_name: str, value: float, details: Dict[str, Any] = None):
        """Record a metric value and check for alerts."""
        metric_data = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self._metrics_history[metric_name].append(metric_data)
        
        if len(self._metrics_history[metric_name]) > self._max_history_size:
            self._metrics_history[metric_name] = self._metrics_history[metric_name][-self._max_history_size:]
        
        self.alert_manager.check_metric(metric_name, value, details)
    
    def get_metric_trend(self, metric_name: str, hours: int = 1) -> Dict[str, Any]:
        """Get metric trend over time."""
        if metric_name not in self._metrics_history:
            return {'values': [], 'avg': 0, 'min': 0, 'max': 0, 'trend': 'stable'}
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        recent_values = [
            m['value'] for m in self._metrics_history[metric_name]
            if m['timestamp'] > cutoff
        ]
        
        if not recent_values:
            return {'values': [], 'avg': 0, 'min': 0, 'max': 0, 'trend': 'stable'}
        
        avg_value = sum(recent_values) / len(recent_values)
        min_value = min(recent_values)
        max_value = max(recent_values)
        
        if len(recent_values) >= 2:
            recent_avg = sum(recent_values[-5:]) / min(5, len(recent_values[-5:]))
            older_avg = sum(recent_values[:5]) / min(5, len(recent_values[:5]))
            
            if recent_avg > older_avg * 1.2:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'values': recent_values,
            'avg': avg_value,
            'min': min_value,
            'max': max_value,
            'trend': trend,
            'count': len(recent_values)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary."""
        alerts_stats = self.alert_manager.get_alert_stats()
        
        metrics_summary = {}
        for metric_name in self._metrics_history.keys():
            if self._metrics_history[metric_name]:
                recent = self._metrics_history[metric_name][-1]
                metrics_summary[metric_name] = {
                    'last_value': recent['value'],
                    'last_timestamp': recent['timestamp']
                }
        
        return {
            'alerts': alerts_stats,
            'metrics': metrics_summary,
            'monitored_metrics_count': len(self._metrics_history)
        }


_global_alert_manager: Optional[AlertManager] = None
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor(get_alert_manager())
    return _global_performance_monitor


def check_performance_alerts(metrics: Dict[str, float]):
    """Check multiple performance metrics for alerts."""
    monitor = get_performance_monitor()
    
    for metric_name, value in metrics.items():
        monitor.record_metric(metric_name, value)
    
    return monitor.alert_manager.get_active_alerts()


def display_alerts_ui():
    """Display alerts in Streamlit UI."""
    if st is None:
        return
    
    alert_manager = get_alert_manager()
    active_alerts = alert_manager.get_active_alerts()
    
    if not active_alerts:
        st.success("✅ Nenhum alerta ativo")
        return
    
    st.warning(f"⚠️ {len(active_alerts)} alerta(s) ativo(s)")
    
    for alert in active_alerts[:10]:
        severity_colors = {
            'low': '🟡',
            'medium': '🟠',
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_colors.get(alert.severity, '⚠️')
        
        with st.expander(f"{emoji} {alert.message}", expanded=(alert.severity in ['high', 'critical'])):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Categoria:** {alert.category}")
                st.markdown(f"**Severidade:** {alert.severity}")
            
            with col2:
                st.markdown(f"**Threshold:** {alert.threshold}")
                st.markdown(f"**Atual:** {alert.current_value:.2f}")
            
            with col3:
                st.markdown(f"**Tempo:** {alert.timestamp.strftime('%H:%M:%S')}")
                st.markdown(f"**Status:** {'✓ Confirmado' if alert.acknowledged else '⏳ Pendente'}")
            
            if alert.details:
                st.json(alert.details)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ Confirmar", key=f"ack_{alert.id}"):
                    alert_manager.acknowledge_alert(alert.id)
                    st.rerun()
            
            with col2:
                if st.button("✕ Resolver", key=f"resolve_{alert.id}"):
                    alert_manager.resolve_alert(alert.id)
                    st.rerun()