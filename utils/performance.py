"""
Performance monitoring and metrics collection.
Tracks execution times, memory usage, and performance bottlenecks.
"""

import time
import functools
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict
import statistics

try:
    import streamlit as st
except ImportError:
    st = None


class PerformanceMetrics:
    """
    Collects and aggregates performance metrics.
    Tracks execution times, call counts, and success rates.
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._total_times: Dict[str, float] = defaultdict(float)
    
    def record(self, name: str, execution_time: float, success: bool = True, **metadata):
        """
        Record a performance metric.
        
        Args:
            name: Metric name (e.g., 'pipeline.run')
            execution_time: Time in seconds
            success: Whether operation succeeded
            **metadata: Additional metadata
        """
        metric = {
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time,
            'success': success,
            **metadata
        }
        
        self._metrics[name].append(metric)
        self._call_counts[name] += 1
        self._total_times[name] += execution_time
        
        if not success:
            self._error_counts[name] += 1
    
    def get_stats(self, name: str) -> Dict[str, Any]:
        """
        Get statistics for a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Dictionary with avg, min, max, median, count, etc.
        """
        if name not in self._metrics or not self._metrics[name]:
            return {
                'count': 0,
                'avg_time': 0,
                'min_time': 0,
                'max_time': 0,
                'median_time': 0,
                'total_time': 0,
                'error_count': 0,
                'success_rate': 100.0
            }
        
        times = [m['execution_time'] for m in self._metrics[name]]
        errors = self._error_counts.get(name, 0)
        total = self._call_counts.get(name, 0)
        
        return {
            'count': total,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': statistics.median(times),
            'total_time': sum(times),
            'error_count': errors,
            'success_rate': ((total - errors) / total * 100) if total > 0 else 100.0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all metrics."""
        return {name: self.get_stats(name) for name in self._metrics.keys()}
    
    def get_top_slow(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N slowest operations."""
        avg_times = {
            name: stats['avg_time']
            for name, stats in self.get_all_stats().items()
        }
        
        sorted_ops = sorted(
            avg_times.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
        
        return [
            {
                'name': name,
                'avg_time': avg_time,
                **self.get_stats(name)
            }
            for name, avg_time in sorted_ops
        ]
    
    def get_top_frequent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N most frequent operations."""
        sorted_ops = sorted(
            self._call_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
        
        return [
            {
                'name': name,
                'count': count,
                **self.get_stats(name)
            }
            for name, count in sorted_ops
        ]
    
    def clear(self):
        """Clear all metrics."""
        self._metrics.clear()
        self._call_counts.clear()
        self._error_counts.clear()
        self._total_times.clear()


_global_metrics: Optional[PerformanceMetrics] = None


def get_performance_metrics() -> PerformanceMetrics:
    """Get global performance metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PerformanceMetrics()
    return _global_metrics


def track_performance(name: Optional[str] = None):
    """
    Decorator to track function performance.
    Automatically records execution time and success/failure.
    
    Args:
        name: Optional metric name (defaults to function name)
        
    Usage:
        @track_performance('database.query')
        def get_submissions(user_id):
            Automatically tracked
            ...
            
        @track_performance()
        def analyze_files(files):
            Automatically uses 'analyze_files' as metric name
            ...
    """
    def decorator(func: Callable) -> Callable:
        metric_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_performance_metrics()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                metrics.record(metric_name, execution_time, success=True)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                metrics.record(metric_name, execution_time, success=False, error=str(e))
                raise
        
        return wrapper
    
    return decorator


class PerformanceContext:
    """
    Context manager for tracking performance of code blocks.
    
    Usage:
        with PerformanceContext('database.query'):
            result = db.query(...)
            
        with PerformanceContext('file.upload') as perf:
            process_files(files)
            # perf.elapsed available after block
    """
    
    def __init__(self, name: str, **metadata):
        self.name = name
        self.metadata = metadata
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        success = exc_type is None
        
        error_msg = None
        if exc_val:
            error_msg = str(exc_val)
        
        metrics = get_performance_metrics()
        metrics.record(
            self.name,
            self.elapsed,
            success=success,
            error=error_msg,
            **self.metadata
        )
        
        return False


def measure_time(func: Callable) -> Callable:
    """
    Simple decorator that prints execution time.
    Useful for quick debugging.
    
    Usage:
        @measure_time
        def slow_function():
            will print execution time
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        print(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    
    return wrapper


def get_performance_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive performance dashboard data.
    Returns metrics suitable for display in UI.
    """
    metrics = get_performance_metrics()
    
    all_stats = metrics.get_all_stats()
    
    total_calls = sum(s['count'] for s in all_stats.values())
    total_time = sum(s['total_time'] for s in all_stats.values())
    total_errors = sum(s['error_count'] for s in all_stats.values())
    
    return {
        'summary': {
            'total_operations': len(all_stats),
            'total_calls': total_calls,
            'total_time_seconds': total_time,
            'total_errors': total_errors,
            'overall_success_rate': ((total_calls - total_errors) / total_calls * 100) if total_calls > 0 else 100.0
        },
        'top_slow': metrics.get_top_slow(5),
        'top_frequent': metrics.get_top_frequent(5),
        'all_metrics': all_stats
    }


def display_performance_report():
    """Display performance report in Streamlit."""
    if st is None:
        return
    
    dashboard = get_performance_dashboard()
    summary = dashboard['summary']
    
    st.markdown("### 📊 Performance Report")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Operations",
            summary['total_operations']
        )
    
    with col2:
        st.metric(
            "Total Calls",
            summary['total_calls']
        )
    
    with col3:
        st.metric(
            "Total Time",
            f"{summary['total_time_seconds']:.2f}s"
        )
    
    with col4:
        st.metric(
            "Success Rate",
            f"{summary['overall_success_rate']:.1f}%"
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🐢 Slowest Operations")
        slow_ops = dashboard['top_slow']
        if slow_ops:
            for op in slow_ops:
                st.write(f"**{op['name']}**: {op['avg_time']:.4f}s avg")
                st.caption(f"Min: {op['min_time']:.4f}s | Max: {op['max_time']:.4f}s | Calls: {op['count']}")
        else:
            st.info("No operations recorded")
    
    with col2:
        st.markdown("#### 📈 Most Frequent")
        freq_ops = dashboard['top_frequent']
        if freq_ops:
            for op in freq_ops:
                st.write(f"**{op['name']}**: {op['count']} calls")
                st.caption(f"Avg: {op['avg_time']:.4f}s | Total: {op['total_time']:.2f}s")
        else:
            st.info("No operations recorded")


def get_metrics_for_export() -> Dict[str, Any]:
    """Get metrics in format suitable for export (JSON/CSV)."""
    metrics = get_performance_metrics()
    
    export_data = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {}
    }
    
    for name, stats in metrics.get_all_stats().items():
        export_data['metrics'][name] = {
            'count': stats['count'],
            'avg_time_ms': stats['avg_time'] * 1000,
            'min_time_ms': stats['min_time'] * 1000,
            'max_time_ms': stats['max_time'] * 1000,
            'median_time_ms': stats['median_time'] * 1000,
            'total_time_seconds': stats['total_time'],
            'error_count': stats['error_count'],
            'success_rate': stats['success_rate']
        }
    
    return export_data