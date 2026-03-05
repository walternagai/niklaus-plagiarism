"""
Advanced analysis tab for Niklaus UI.
"""

import streamlit as st
from typing import Dict, Any
from ui.components.tables import display_metrics_table, display_ast_table, display_comparison_table
from ui.components.charts import create_metrics_radar_chart


def render_advanced_tab(results: Dict[str, Any]) -> None:
    """
    Display advanced analysis tab.
    
    Args:
        results: Analysis results
    """
    st.markdown("### :microscope: Análise Avançada de Código")
    st.markdown("**Análise estrutural (AST), métricas de complexidade e detecção de padrões de plágio**")
    
    if not results.get('metrics'):
        st.warning(
            "Métricas não disponíveis para esta submissão. "
            "Algumas submissões antigas foram salvas em modo compacto (sem AST/métricas). "
            "Execute uma nova análise para visualizar a Análise Avançada."
        )
        return
    
    # AST Similarities
    st.markdown("#### Similaridade Estrutural (AST)")
    st.info("A similaridade estrutural compara a árvore sintática do código, identificando similaridades mesmo com variáveis renomeadas ou código reorganizado.")
    
    if results.get('ast_similarities'):
        display_ast_table(results['ast_similarities'])
        
        # Show stats
        import numpy as np
        ast_sims = [s[2] for s in results['ast_similarities'] if isinstance(s, (list, tuple)) and len(s) == 3]
        
        if ast_sims:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Similaridade Estrutural Média", f"{np.mean(ast_sims):.1%}")
            with col2:
                st.metric("Similaridade Estrutural Máxima", f"{np.max(ast_sims):.1%}")
    
    # Metrics
    st.markdown("---")
    st.markdown("#### Métricas de Complexidade")
    
    display_metrics_table(results['metrics'])
    
    # Comparative metrics
    if results.get('suspicious_pairs'):
        st.markdown("---")
        st.markdown("#### Análise de Métricas Comparativas")
        
        # Select files to compare
        file_pairs = [(row[0], row[1]) for row in results['suspicious_pairs'][:20]]
        
        if file_pairs:
            selected_pair_idx = st.selectbox(
                "Selecione par de arquivos para análise detalhada",
                range(len(file_pairs)),
                format_func=lambda x: f"{file_pairs[x][0]} vs {file_pairs[x][1]}"
            )
            
            if selected_pair_idx is not None:
                file1, file2 = file_pairs[selected_pair_idx]
                
                # Get metrics for both files
                m1 = next((m for m in results['metrics'] if m.get('file') == file1), None)
                m2 = next((m for m in results['metrics'] if m.get('file') == file2), None)
                
                if m1 and m2:
                    # Display comparison table
                    display_comparison_table(m1, m2, file1, file2)
                    
                    # Radar chart
                    try:
                        radar_fig = create_metrics_radar_chart(m1, m2, file1, file2)
                        st.plotly_chart(radar_fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Não foi possível gerar gráfico radar: {str(e)}")
    
    # Patterns
    if results.get('patterns'):
        st.markdown("---")
        st.markdown("#### Padrões de Plágio Detectados")
        
        for key, pattern in results['patterns'].items():
            with st.expander(f":mag: {key}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Tipo Detectado", pattern.get('plagiarism_type', 'N/A').replace('_', ' '))
                with col2:
                    st.metric("Confiança", f"{pattern.get('confidence', 0):.1%}")
                
                st.info(f"**Explicação:** {pattern.get('explanation', 'N/A')}")
                
                # Show pattern details without nested expander
                if pattern.get('patterns_detected'):
                    st.markdown("**Detalhes dos Padrões:**")
                    st.json(pattern.get('patterns_detected', {}))
