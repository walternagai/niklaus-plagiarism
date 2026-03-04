"""
Statistics tab for Niklaus UI.
"""

import streamlit as st
import numpy as np
from typing import Dict, Any
from ui.components.charts import (
    create_similarity_heatmap,
    create_distribution_histogram
)


def render_statistics_tab(results: Dict[str, Any]) -> None:
    """
    Display statistics tab.
    
    Args:
        results: Analysis results
    """
    st.markdown("### :chart_with_upwards_trend: Estatísticas e Visualizações")
    
    if not results.get('suspicious_pairs'):
        st.info(":white_check_mark: Sem dados estatísticos disponíveis.")
        return
    
    # Calculate statistics
    similarities = [s[2] for s in results['suspicious_pairs']]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Média de Similaridade", f"{np.mean(similarities):.1%}")
    
    with col2:
        st.metric("Mediana", f"{np.median(similarities):.1%}")
    
    with col3:
        st.metric("Desvio Padrão", f"{np.std(similarities):.2f}")
    
    with col4:
        st.metric("Acima de 70%", sum(1 for s in similarities if s > 0.7))
    
    st.markdown("---")
    
    # Heatmap
    st.markdown("### :fire: Mapa de Calor de Similaridade")
    
    if results.get('similarity_matrix'):
        matrix = np.array(results['similarity_matrix'])
        fig = create_similarity_heatmap(results['files'], matrix)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Distribution histogram
    st.markdown("### :bar_chart: Distribuição de Similaridades")
    
    fig = create_distribution_histogram(similarities)
    st.plotly_chart(fig, use_container_width=True)
    
    # Additional statistics
    st.markdown("---")
    st.markdown("### :clipboard: Resumo Estatístico")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Similaridades")
        st.write(f"- **Mínima:** {np.min(similarities):.1%}")
        st.write(f"- **Máxima:** {np.max(similarities):.1%}")
        st.write(f"- **Média:** {np.mean(similarities):.1%}")
        st.write(f"- **Mediana:** {np.median(similarities):.1%}")
        st.write(f"- **Desvio Padrão:** {np.std(similarities):.2f}")
    
    with col2:
        st.markdown("#### Distribuição por Faixa")
        
        faixas = {
            '0-20%': sum(1 for s in similarities if 0 <= s < 0.2),
            '20-40%': sum(1 for s in similarities if 0.2 <= s < 0.4),
            '40-60%': sum(1 for s in similarities if 0.4 <= s < 0.6),
            '60-80%': sum(1 for s in similarities if 0.6 <= s < 0.8),
            '80-100%': sum(1 for s in similarities if 0.8 <= s <= 1.0)
        }
        
        for faixa, count in faixas.items():
            st.write(f"- **{faixa}:** {count} pares")