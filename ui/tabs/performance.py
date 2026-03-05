"""
Performance dashboard tab component.
Displays performance metrics and system statistics.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any

from utils.performance import get_performance_dashboard, get_metrics_for_export
from utils.db_cache import get_cache_stats


def render_performance_dashboard():
    """Render performance dashboard tab."""
    
    st.markdown("### 📊 Dashboard de Performance")
    
    dashboard_data = get_performance_dashboard()
    cache_stats = get_cache_stats()
    
    _render_summary_metrics(dashboard_data['summary'])
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Visão Geral",
        "🐢 Operações Lentas",
        "📊 Operações Frequentes",
        "💾 Cache"
    ])
    
    with tab1:
        _render_overview_tab(dashboard_data)
    
    with tab2:
        _render_slow_operations_tab(dashboard_data['top_slow'])
    
    with tab3:
        _render_frequent_operations_tab(dashboard_data['top_frequent'])
    
    with tab4:
        _render_cache_tab(cache_stats)


def _render_summary_metrics(summary: Dict[str, Any]):
    """Render summary metrics."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Operações",
            summary['total_operations'],
            help="Total de tipos de operações monitoradas"
        )
    
    with col2:
        st.metric(
            "Chamadas",
            summary['total_calls'],
            help="Total de chamadas realizadas"
        )
    
    with col3:
        st.metric(
            "Tempo Total",
            f"{summary['total_time_seconds']:.2f}s",
            help="Tempo total de execução"
        )
    
    with col4:
        st.metric(
            "Erros",
            summary['total_errors'],
            delta_color="inverse"
        )
    
    with col5:
        st.metric(
            "Taxa de Sucesso",
            f"{summary['overall_success_rate']:.1f}%",
            help="Porcentagem de operações bem-sucedidas"
        )


def _render_overview_tab(dashboard_data: Dict[str, Any]):
    """Render overview tab."""
    st.markdown("#### Métricas por Categoria")
    
    all_metrics = dashboard_data['all_metrics']
    
    if not all_metrics:
        st.info("Nenhuma métrica disponível ainda. Execute análises para coletar dados de performance.")
        return
    
    categories = {}
    for metric_name, stats in all_metrics.items():
        category = metric_name.split('.')[0] if '.' in metric_name else 'other'
        if category not in categories:
            categories[category] = []
        categories[category].append((metric_name, stats))
    
    for category, metrics in sorted(categories.items()):
        with st.expander(f"📁 {category.upper()} ({len(metrics)} métricas)", expanded=False):
            for metric_name, stats in metrics:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                name_display = metric_name.split('.')[-1] if '.' in metric_name else metric_name
                
                with col1:
                    st.markdown(f"**{name_display}**")
                
                with col2:
                    st.caption(f"Calls: {stats['count']}")
                
                with col3:
                    st.caption(f"Avg: {stats['avg_time']*1000:.2f}ms")
                
                with col4:
                    success_rate_color = "green" if stats['success_rate'] >= 95 else "orange" if stats['success_rate'] >= 80 else "red"
                    st.caption(f"✓ {stats['success_rate']:.1f}%")


def _render_slow_operations_tab(slow_ops: list):
    """Render slow operations tab."""
    st.markdown("#### 🐢 Operações Mais Lentas")
    
    if not slow_ops:
        st.info("Nenhuma operação registrada ainda.")
        return
    
    st.markdown("""
    Estas são as operações que levam mais tempo para executar.
    Considere otimizar se estiverem muito lentas.
    """)
    
    for i, op in enumerate(slow_ops, 1):
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**{i}. {op['name']}**")
                st.caption(f"Avg: {op['avg_time']*1000:.2f}ms")
            
            with col2:
                st.caption(f"Min: {op['min_time']*1000:.2f}ms | Max: {op['max_time']*1000:.2f}ms")
                st.caption(f"Median: {op['median_time']*1000:.2f}ms")
            
            with col3:
                st.metric("Calls", op['count'])
            
            st.markdown("---")


def _render_frequent_operations_tab(freq_ops: list):
    """Render frequent operations tab."""
    st.markdown("#### 📈 Operações Mais Frequentes")
    
    if not freq_ops:
        st.info("Nenhuma operação registrada ainda.")
        return
    
    st.markdown("""
    Estas são as operações mais chamadas no sistema.
    Operações frequentes devem ser bem otimizadas.
    """)
    
    for i, op in enumerate(freq_ops, 1):
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**{i}. {op['name']}**")
                st.caption(f"Count: {op['count']}")
            
            with col2:
                st.caption(f"Avg: {op['avg_time']*1000:.2f}ms")
                st.caption(f"Total: {op['total_time']:.2f}s")
            
            with col3:
                efficiency = "✅" if op['avg_time'] < 0.1 else "⚠️" if op['avg_time'] < 0.5 else "❌"
                st.markdown(f"### {efficiency}")
            
            st.markdown("---")


def _render_cache_tab(cache_stats: Dict[str, Any]):
    """Render cache statistics tab."""
    st.markdown("#### 💾 Estatísticas do Cache")
    
    query_cache_stats = cache_stats.get('query_cache', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Itens no Cache",
            query_cache_stats.get('size', 0),
            help="Número de queries em cache"
        )
    
    with col2:
        st.metric(
            "Hits",
            query_cache_stats.get('hits', 0),
            help="Consultas atendidas pelo cache"
        )
    
    with col3:
        st.metric(
            "Misses",
            query_cache_stats.get('misses', 0),
            help="Consultas não encontradas no cache"
        )
    
    with col4:
        hit_rate = query_cache_stats.get('hit_rate', 0)
        st.metric(
            "Taxa de Acerto",
            f"{hit_rate:.1f}%",
            help="Porcentagem de consultas atendidas pelo cache",
            delta=f"{hit_rate - 50:.1f}%" if hit_rate > 50 else None
        )
    
    st.markdown("---")
    
    with st.expander("ℹ️ Sobre o Cache"):
        st.markdown("""
        O cache do sistema armazena resultados de queries para melhorar performance.
        
        **Benefícios:**
        - Reduz tempo de carregamento
        - Menos consultas ao banco de dados
        - Respostas mais rápidas para dados frequentes
        
        **Quando limpar:**
        - Dados desatualizados
        - Mudanças de configuração
        - Problemas de consistência
        """)
        
        if st.button("🗑️ Limpar Todos os Caches", type="secondary"):
            from utils.db_cache import clear_all_caches
            clear_all_caches()
            st.success("✓ Todos os caches foram limpos")
            st.rerun()


def render_metrics_export():
    """Render metrics export button."""
    st.markdown("### 📥 Exportar Métricas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Exportar JSON", use_container_width=True):
            metrics = get_metrics_for_export()
            st.json(metrics)
            st.info("Métricas exportadas em formato JSON")
    
    with col2:
        if st.button("🔄 Limpar Métricas", use_container_width=True, type="secondary"):
            from utils.performance import get_performance_metrics
            metrics = get_performance_metrics()
            metrics.clear()
            st.success("✓ Métricas limpas")
            st.rerun()


def render_real_time_monitoring():
    """Render real-time performance monitoring."""
    st.markdown("#### ⏱️ Monitoramento em Tempo Real")
    
    st.markdown("""
    Monitore a performance do sistema em tempo real.
    As métricas são atualizadas conforme você usa a aplicação.
    """)
    
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False)
    
    if auto_refresh:
        import time
        placeholder = st.empty()
        
        with placeholder.container():
            render_performance_dashboard()
        
        time.sleep(5)
        st.rerun()