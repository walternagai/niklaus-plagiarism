"""
Lazy loading utilities for improved performance.
Implements lazy imports and module-level caching.
"""

import importlib
import sys
import time
from typing import Any, Callable, Optional, Dict
from functools import wraps
import streamlit as st


class LazyModule:
    """
    Lazy module loader that imports modules only when accessed.
    Reduces initial load time by deferring imports.
    """
    
    def __init__(self, module_name: str, package: Optional[str] = None):
        self._module_name = module_name
        self._package = package
        self._module = None
    
    def _load_module(self):
        if self._module is None:
            self._module = importlib.import_module(
                self._module_name,
                package=self._package
            )
        return self._module
    
    def __getattr__(self, name: str) -> Any:
        module = self._load_module()
        return getattr(module, name)
    
    def __dir__(self):
        module = self._load_module()
        return dir(module)


class LazyTabLoader:
    """
    Lazy tab loader that only renders tabs when selected.
    Uses Streamlit session state for caching rendered content.
    """
    
    def __init__(self):
        self._loaded_tabs: Dict[str, float] = {}
        self._tab_data: Dict[str, Any] = {}
    
    def is_tab_loaded(self, tab_name: str) -> bool:
        """Check if tab has been loaded in this session."""
        return f"tab_{tab_name}_loaded" in st.session_state
    
    def get_tab_load_time(self, tab_name: str) -> Optional[float]:
        """Get time when tab was loaded."""
        return self._loaded_tabs.get(tab_name)
    
    def mark_tab_loaded(self, tab_name: str, data: Any = None):
        """Mark tab as loaded with optional data."""
        st.session_state[f"tab_{tab_name}_loaded"] = True
        self._loaded_tabs[tab_name] = time.time()
        if data is not None:
            self._tab_data[tab_name] = data
    
    def get_tab_data(self, tab_name: str) -> Any:
        """Get cached tab data."""
        return self._tab_data.get(tab_name)
    
    def clear_tab_cache(self, tab_name: str):
        """Clear specific tab cache."""
        key = f"tab_{tab_name}_loaded"
        if key in st.session_state:
            del st.session_state[key]
        if tab_name in self._loaded_tabs:
            del self._loaded_tabs[tab_name]
        if tab_name in self._tab_data:
            del self._tab_data[tab_name]
    
    def clear_all_cache(self):
        """Clear all tab caches."""
        keys_to_delete = [
            k for k in st.session_state.keys() 
            if k.startswith("tab_") and k.endswith("_loaded")
        ]
        for key in keys_to_delete:
            del st.session_state[key]
        self._loaded_tabs.clear()
        self._tab_data.clear()


def lazy_tab(tab_name: str):
    """
    Decorator to lazy load tab content.
    Only executes the tab rendering function when tab is active.
    
    Args:
        tab_name: Name of the tab for caching
        
    Usage:
        @lazy_tab("results")
        def render_results_tab():
            # Only rendered when tab is selected
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            loader = LazyTabLoader()
            
            if loader.is_tab_loaded(tab_name):
                return func(*args, **kwargs)
            
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            loader.mark_tab_loaded(tab_name)
            
            if 'performance_metrics' not in st.session_state:
                st.session_state['performance_metrics'] = {}
            
            st.session_state['performance_metrics'][f'{tab_name}_load_time'] = elapsed
            
            return result
        
        return wrapper
    return decorator


class ComponentCache:
    """
    LRU cache for expensive components.
    Caches rendered components to avoid re-computation.
    """
    
    def __init__(self, maxsize: int = 128):
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._maxsize = maxsize
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached component."""
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Cache component with LRU eviction."""
        if len(self._cache) >= self._maxsize:
            self._evict_lru()
        
        self._cache[key] = value
        self._access_times[key] = time.time()
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self.delete(lru_key)
    
    def delete(self, key: str):
        """Delete cached component."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def clear(self):
        """Clear all cached components."""
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'maxsize': self._maxsize,
            'keys': list(self._cache.keys())
        }


def cached_component(key_prefix: str = '', ttl: Optional[float] = None):
    """
    Decorator to cache component rendering results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds (None = no expiration)
        
    Usage:
        @cached_component('chart_', ttl=300)
        def render_chart(data):
            # Cached for 5 minutes
            ...
    """
    def decorator(func: Callable) -> Callable:
        cache_key = f"{key_prefix}{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cache_key not in st.session_state:
                result = func(*args, **kwargs)
                st.session_state[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
                return result
            
            cached = st.session_state[cache_key]
            
            if ttl is not None:
                if time.time() - cached['timestamp'] > ttl:
                    result = func(*args, **kwargs)
                    st.session_state[cache_key] = {
                        'data': result,
                        'timestamp': time.time()
                    }
                    return result
            
            return cached['data']
        
        return wrapper
    return decorator


def preload_essential_modules():
    """Preload essential modules for faster subsequent imports."""
    essential_modules = [
        'typing',
        'utils.config',
        'utils.logger',
    ]
    
    for module_name in essential_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass


def get_lazy_imports():
    """Get lazy versions of heavy modules."""
    return {
        'plotly': LazyModule('plotly.graph_objects'),
        'networkx': LazyModule('networkx'),
        'sklearn': LazyModule('sklearn'),
        'scipy': LazyModule('scipy'),
    }