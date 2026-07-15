"""
Combined analytics and monitoring dashboard.
Consolidates all monitoring, alerts, and business metrics.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any

from utils.analytics import get_analytics, display_analytics_dashboard
from utils.alerts import get_alert_manager, display_alerts_ui
from utils.performance import get_performance_dashboard, display_performance_report
from utils.compression import get_compression_stats
from utils.db_cache import get_cache_stats


def render_monitoring_dashboard():
    """Render comprehensive monitoring dashboard."""
    
    st.markdown("# 📊 Dashboard de Monitoramento")
    
    st.markdown("""
    Dashboard consolidado com métricas de performance, alertas, analytics e sistema.
    """)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Analytics",
        "⚠️ Alertas",
        "⚡ Performance",
        "💾 Cache",
        "🗜️ Compressão"
    ])
    
    with tab1:
        _render_analytics_tab()
    
    with tab2:
        _render_alerts_tab()
    
    with tab3:
        _render_performance_tab()
    
    with tab4:
        _render_cache_tab()
    
    with tab5:
        _render_compression_tab()


def _render_analytics_tab():
    """Render analytics metrics."""
    st.markdown("### 📈 Métricas de Negócio")
    
    analytics = get_analytics()
    global_stats = analytics.get_global_stats(days=30)
    trending = analytics.get_trending_metrics(hours=24)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Análises (30d)",
            global_stats['total_analyses'],
            help="Total de análises nos últimos 30 dias"
        )
    
    with col2:
        st.metric(
            "Usuários Ativos",
            global_stats['unique_users'],
            help="Usuários únicos nos últimos 30 dias"
        )
    
    with col3:
        st.metric(
            "Arquivos Processados",
            global_stats['total_files'],
            delta=f"{global_stats['total_files'] // 30:d}/dia",
            help="Total de arquivos processados"
        )
    
    with col4:
        trend_emoji = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}
        st.metric(
            "Tendência (24h)",
            f"{trend_emoji.get(trending['trend'], '➡️')} {trending['trend'].title()}",
            help="Tendência de uso nas últimas 24 horas"
        )
    
    st.markdown("---")
    
    # Usage patterns
    usage_patterns = analytics.get_usage_patterns(days=7)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Distribuição por Linguagem")
        if usage_patterns['language_distribution']:
            for lang, count in sorted(usage_patterns['language_distribution'].items(),
                                      key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"- **{lang}**: {count} análises")
        else:
            st.info("Nenhum dado disponível")
    
    with col2:
        st.markdown("#### 🎯 Distribuição por Threshold")
        if usage_patterns['threshold_distribution']:
            for threshold, count in sorted(usage_patterns['threshold_distribution'].items()):
                st.write(f"- **{threshold}**: {count} análises")
        else:
            st.info("Nenhum dado disponível")
    
    st.markdown("---")
    
    # Peak usage
    if usage_patterns['peak_hour']:
        st.markdown("#### ⏰ Picos de Uso")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Horário**: {usage_patterns['peak_hour']}")
        
        with col2:
            st.write(f"**Uso máximo**: {usage_patterns['peak_usage']} análises/hora")
        
        with col3:
            st.write(f"**Média diária**: {usage_patterns['average_daily_usage']:.1f} análises/dia")
    
    # Export
    st.markdown("---")
    st.markdown("#### 📥 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Exportar JSON", use_container_width=True):
            data = analytics.export_metrics(format='json')
            st.download_button(
                label="Baixar JSON",
                data=data,
                file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("📄 Exportar CSV", use_container_width=True):
            data = analytics.export_metrics(format='csv')
            st.download_button(
                label="Baixar CSV",
                data=data,
                file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )


def _render_alerts_tab():
    """Render alerts dashboard."""
    st.markdown("### ⚠️ Alertas de Performance")
    
    alert_manager = get_alert_manager()
    stats = alert_manager.get_alert_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Alertas", stats['total_alerts'])
    
    with col2:
        st.metric("Alertas Ativos", stats['active_alerts'])
    
    with col3:
        st.metric("Confirmados", stats['acknowledged_alerts'])
    
    with col4:
        active_by_severity = stats['severity_breakdown']
        critical = active_by_severity.get('critical', 0)
        high = active_by_severity.get('high', 0)
        st.metric("Críticos/Altos", f"{critical}/{high}")
    
    st.markdown("---")
    
    display_alerts_ui()
    
    st.markdown("---")
    
    with st.expander("⚙️ Configurar Alertas"):
        st.markdown("#### Thresholds de Alerta")
        st.info("Configure os thresholds na sidebar em 'Configurações Avançadas'")
        
        thresholds = alert_manager._thresholds
        
        for metric, config in thresholds.items():
            st.markdown(f"**{metric}**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"⚠️ Warning: {config['warning']}")
            
            with col2:
                st.write(f"🚨 Critical: {config['critical']}")


def _render_performance_tab():
    """Render performance metrics."""
    st.markdown("### ⚡ Métricas de Performance")
    
    display_performance_report()
    
    st.markdown("---")
    
    dashboard_data = get_performance_dashboard()
    
    with st.expander("📈 Gráfico de Tendências"):
        st.markdown("#### Operações ao Longo do Tempo")
        
        all_metrics = dashboard_data['all_metrics']
        
        if all_metrics:
            import pandas as pd
            import plotly.graph_objects as go
            
            data = []
            for metric_name, stats in all_metrics.items():
                data.append({
                    'Operação': metric_name,
                    'Chamadas': stats['count'],
                    'Tempo Médio (ms)': stats['avg_time'] * 1000,
                    'Tempo Total (s)': stats['total_time']
                })
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Chamadas por Operação**")
                    st.bar_chart(df.set_index('Operação')['Chamadas'])
                
                with col2:
                    st.markdown("**Tempo Médio por Operação**")
                    st.bar_chart(df.set_index('Operação')['Tempo Médio (ms)'])
        else:
            st.info("Nenhum dado disponível")


def _render_cache_tab():
    """Render cache statistics."""
    st.markdown("### 💾 Estatísticas de Cache")
    
    cache_stats = get_cache_stats()
    query_cache_stats = cache_stats.get('query_cache', {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Itens no Cache", query_cache_stats.get('size', 0))
    
    with col2:
        st.metric("Hits", query_cache_stats.get('hits', 0))
    
    with col3:
        st.metric("Misses", query_cache_stats.get('misses', 0))
    
    with col4:
        hit_rate = query_cache_stats.get('hit_rate', 0)
        st.metric("Hit Rate", f"{hit_rate:.1f}%")
    
    with col5:
        st.metric("Total Queries", query_cache_stats.get('total_queries', 0))
    
    st.markdown("---")
    
    # Cache efficiency
    if query_cache_stats.get('total_queries', 0) > 0:
        st.markdown("#### 📊 Eficiência do Cache")
        
        import plotly.graph_objects as go
        
        labels = ['Hits', 'Misses']
        values = [
            query_cache_stats.get('hits', 0),
            query_cache_stats.get('misses', 0)
        ]
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Recommendations
        hit_rate = query_cache_stats.get('hit_rate', 0)
        
        st.markdown("#### 💡 Recomendações")
        
        if hit_rate < 30:
            st.error("⚠️ Hit rate muito baixo! Considere aumentar TTL ou revisar queries.")
        elif hit_rate < 50:
            st.warning("🔶 Hit rate abaixo do ideal. Verifique padrões de acesso.")
        elif hit_rate < 70:
            st.info("ℹ️ Hit rate razoável. Há espaço para otimização.")
        else:
            st.success("✅ Excelente hit rate! Cache funcionando bem.")
    
    st.markdown("---")
    
    # Cache management
    st.markdown("#### 🔧 Gerenciamento de Cache")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpar Cache de Queries", use_container_width=True, type="secondary"):
            from utils.db_cache import clear_all_caches
            clear_all_caches()
            st.success("✓ Cache de queries limpo")
            st.rerun()
    
    with col2:
        if st.button("🔄 Atualizar Estatísticas", use_container_width=True):
            st.rerun()


def _render_compression_tab():
    """Render compression statistics."""
    st.markdown("### 🗜️ Estatísticas de Compressão")
    
    compression_stats = get_compression_stats()
    total_savings = compression_stats.get_total_savings()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Bytes Originais", f"{total_savings['original_bytes']:,}")
    
    with col2:
        st.metric("Bytes Comprimidos", f"{total_savings['compressed_bytes']:,}")
    
    with col3:
        st.metric("Bytes Economizados", f"{total_savings['saved_bytes']:,}")
    
    with col4:
        st.metric("Economia", f"{total_savings['savings_percentage']:.1f}%")
    
    st.markdown("---")
    
    # Per operation stats
    all_stats = compression_stats.get_stats()
    
    if all_stats:
        st.markdown("#### 📊 Compressão por Operação")
        
        import pandas as pd
        
        data = []
        for operation, stats in all_stats.items():
            data.append({
                'Operação': operation,
                'Original (KB)': stats['total_original'] / 1024,
                'Comprimido (KB)': stats['total_compressed'] / 1024,
                'Ratio (%)': stats['ratio']
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Visual comparison
        if not df.empty:
            import plotly.graph_objects as go
            
            fig = go.Figure(data=[
                go.Bar(name='Original (KB)', x=df['Operação'], y=df['Original (KB)']),
                go.Bar(name='Comprimido (KB)', x=df['Operação'], y=df['Comprimido (KB)'])
            ])
            fig.update_layout(barmode='group', height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado de compressão disponível ainda")


def render_quick_stats():
    """Render quick stats for sidebar."""
    analytics = get_analytics()
    trending = analytics.get_trending_metrics(hours=24)
    
    st.markdown("### 📈 Stats Rápidas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Análises (24h)", trending['analyses_count'])
    
    with col2:
        st.metric("Tempo Médio", f"{trending['avg_processing_time']:.2f}s")
    
    # Alerts summary
    alert_manager = get_alert_manager()
    active_alerts = alert_manager.get_active_alerts()
    
    if active_alerts:
        critical_count = len([a for a in active_alerts if a.severity == 'critical'])
        high_count = len([a for a in active_alerts if a.severity == 'high'])
        
        if critical_count > 0:
            st.error(f"🚨 {critical_count} alerta(s) crítico(s)")
        elif high_count > 0:
            st.warning(f"⚠️ {high_count} alerta(s) alto(s)")
        else:
            st.info(f"ℹ️ {len(active_alerts)} alerta(s) ativo(s)")