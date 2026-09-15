"""
Tests for utils/lazy_loader.py with a mocked Streamlit session_state.

Covers LazyModule, LazyTabLoader, lazy_tab decorator, ComponentCache,
cached_component decorator, preload_essential_modules and get_lazy_imports.
"""

from unittest.mock import MagicMock, patch

import pytest

from utils.lazy_loader import (
    ComponentCache,
    LazyModule,
    LazyTabLoader,
    cached_component,
    get_lazy_imports,
    lazy_tab,
    preload_essential_modules,
)


class FakeSessionState(dict):
    """dict-backed st.session_state double."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_st():
    fake = MagicMock()
    fake.session_state = FakeSessionState()
    with patch('utils.lazy_loader.st', fake):
        yield fake


# ---------------------------------------------------------------------------
# LazyModule
# ---------------------------------------------------------------------------

class TestLazyModule:
    def test_deferred_import(self):
        lazy = LazyModule('math')
        assert lazy._module is None  # not imported yet
        assert lazy.sqrt(25) == 5.0
        assert lazy._module is not None

    def test_dir_reflects_module(self):
        lazy = LazyModule('json')
        assert 'dumps' in dir(lazy)

    def test_package_parameter(self):
        lazy = LazyModule('pathlib', package=None)
        assert lazy.Path('.') is not None

    def test_import_error_propagates(self):
        lazy = LazyModule('module_that_does_not_exist_xyz')
        with pytest.raises(Exception):
            _ = lazy.anything


# ---------------------------------------------------------------------------
# LazyTabLoader + lazy_tab decorator
# ---------------------------------------------------------------------------

class TestLazyTabLoader:
    def test_mark_and_is_loaded(self, fake_st):
        loader = LazyTabLoader()
        assert loader.is_tab_loaded('results') is False
        loader.mark_tab_loaded('results', data={'x': 1})
        assert loader.is_tab_loaded('results') is True
        assert loader.get_tab_data('results') == {'x': 1}
        assert loader.get_tab_load_time('results') is not None

    def test_get_missing_tab(self, fake_st):
        loader = LazyTabLoader()
        assert loader.get_tab_load_time('nope') is None
        assert loader.get_tab_data('nope') is None

    def test_clear_single_tab(self, fake_st):
        loader = LazyTabLoader()
        loader.mark_tab_loaded('results', data=1)
        loader.clear_tab_cache('results')
        assert loader.is_tab_loaded('results') is False
        assert loader.get_tab_data('results') is None

    def test_clear_all(self, fake_st):
        loader = LazyTabLoader()
        loader.mark_tab_loaded('a')
        loader.mark_tab_loaded('b')
        loader.clear_all_cache()
        assert loader.is_tab_loaded('a') is False
        assert loader.is_tab_loaded('b') is False
        assert loader._loaded_tabs == {}

    def test_lazy_tab_decorator_executes_when_loaded(self, fake_st):
        calls = []

        @lazy_tab('heavy')
        def render():
            calls.append(1)
            return 'rendered'

        # First call: tab not yet in session_state -> executes and marks
        assert render() == 'rendered'
        assert len(calls) == 1
        # Second call: tab IS loaded -> executes again (by design, tab is
        # "active"); load time recorded in performance_metrics
        assert render() == 'rendered'
        assert len(calls) == 2
        assert fake_st.session_state['performance_metrics']['heavy_load_time'] >= 0

    def test_lazy_tab_records_metrics_once_per_session(self, fake_st):
        @lazy_tab('metrics_tab')
        def render():
            return 'x'

        render()
        metrics = fake_st.session_state['performance_metrics']
        assert 'metrics_tab_load_time' in metrics


# ---------------------------------------------------------------------------
# ComponentCache
# ---------------------------------------------------------------------------

class TestComponentCache:
    def test_get_set(self):
        cache = ComponentCache()
        assert cache.get('k') is None
        cache.set('k', {'rendered': True})
        assert cache.get('k') == {'rendered': True}

    def test_lru_eviction(self):
        cache = ComponentCache(maxsize=2)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.get('a')            # touch a -> b becomes LRU
        cache.set('c', 3)         # evicts b (least recently used)
        assert cache.get('b') is None
        assert cache.get('a') == 1
        assert cache.get('c') == 3

    def test_delete_and_clear(self):
        cache = ComponentCache()
        cache.set('x', 1)
        cache.delete('x')
        assert cache.get('x') is None
        cache.set('y', 2)
        cache.clear()
        assert cache.get_stats()['size'] == 0

    def test_get_stats(self):
        cache = ComponentCache(maxsize=10)
        cache.set('item', 1)
        stats = cache.get_stats()
        assert stats == {'size': 1, 'maxsize': 10, 'keys': ['item']}


# ---------------------------------------------------------------------------
# cached_component decorator
# ---------------------------------------------------------------------------

class TestCachedComponent:
    def test_caches_result(self, fake_st):
        calls = []

        @cached_component('chart_')
        def render_chart(data):
            calls.append(data)
            return f'chart:{data}'

        assert render_chart(1) == 'chart:1'
        assert render_chart(1) == 'chart:1'
        assert len(calls) == 1

    def test_ttl_expiry_recomputes(self, fake_st, monkeypatch):
        import time as time_mod
        calls = []
        clock = {'now': 1000.0}
        monkeypatch.setattr(time_mod, 'time', lambda: clock['now'])

        @cached_component('ttl_', ttl=10)
        def render(data):
            calls.append(data)
            return data * 10

        assert render(2) == 20
        clock['now'] = 1005.0           # inside TTL -> cached
        assert render(2) == 20
        assert len(calls) == 1
        clock['now'] = 2000.0           # TTL expired -> recompute
        assert render(2) == 20
        assert len(calls) == 2

    def test_no_ttl_never_expires(self, fake_st):
        calls = []

        @cached_component('forever_')
        def render():
            calls.append(1)
            return 'v'

        render()
        render()
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# preload + registry
# ---------------------------------------------------------------------------

def test_preload_essential_modules_does_not_raise():
    preload_essential_modules()  # all imports valid; must not raise


def test_get_lazy_imports_keys():
    lazy = get_lazy_imports()
    assert set(lazy.keys()) == {'plotly', 'networkx', 'sklearn', 'scipy'}
    # LazyModule proxies — attribute access triggers real import
    assert lazy['networkx'].Graph is not None