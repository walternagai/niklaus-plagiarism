"""
Graph tab for Niklaus UI.
"""

import streamlit as st
import numpy as np
from typing import Dict, Any
from ui.components.charts import create_similarity_graph
from ui.components.tables import display_cluster_table


def render_graph_tab(results: Dict[str, Any]) -> None:
    """
    Display similarity graph tab.
    
    Args:
        results: Analysis results
    """
    st.markdown("### :spider_web: Grafo de Similaridade")
    st.markdown(
        "Cada **nó** representa um arquivo. "
        "As **arestas** conectam pares com similaridade acima do limiar, "
        "com espessura proporcional à similaridade."
    )
    
    if not results.get('similarity_matrix') or not results.get('files'):
        st.info("Execute uma análise ou carregue uma submissão com dados suficientes para visualizar o grafo de similaridade.")
        return
    
    # Threshold slider for graph
    graph_threshold = st.slider(
        "Limiar do grafo",
        min_value=0.0,
        max_value=1.0,
        value=float(results['threshold']),
        step=0.05,
        key="graph_threshold",
        help="Apenas pares com similaridade acima deste valor aparecem no grafo"
    )
    
    # Rebuild cluster data with chosen threshold
    from core.analyzer import PlagiarismAnalyzer
    
    analyzer = PlagiarismAnalyzer(results['language'])
    sim_mat_np = np.array(results['similarity_matrix'])
    
    try:
        display_cluster_data = analyzer.cluster_detector.analyze_clusters(
            sim_mat_np, results['files'], min_similarity=graph_threshold
        )
    except Exception as e:
        st.error(f"Erro ao gerar grafo: {str(e)}")
        return
    
    # Create graph
    try:
        graph_fig = create_similarity_graph(
            results['similarity_matrix'],
            results['files'],
            min_similarity=graph_threshold,
            cluster_data=display_cluster_data
        )
        
        if graph_fig:
            st.plotly_chart(graph_fig, use_container_width=True)
        else:
            st.info("Nenhuma conexão acima do limiar definido. Reduza o limiar para visualizar o grafo.")
    except Exception as e:
        st.error(f"Erro ao criar visualização: {str(e)}")
        return
    
    # Cluster statistics
    st.markdown("---")
    st.markdown("#### Resumo dos Clusters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de clusters", display_cluster_data['num_clusters'])
    
    with col2:
        st.metric("Maior cluster", f"{display_cluster_data['largest_cluster']} arquivos")
    
    with col3:
        st.metric("Arestas no grafo", display_cluster_data['graph_edges'])
    
    with col4:
        density_pct = display_cluster_data['graph_density'] * 100
        st.metric("Densidade do grafo", f"{density_pct:.1f}%")
    
    # Cluster details
    display_cluster_table(display_cluster_data)
    
    # Community detection results
    if display_cluster_data.get('communities') and len(display_cluster_data['communities']) > 0:
        st.markdown("---")
        st.markdown("#### Comunidades Detectadas (Modularidade)")
        st.caption("Detecção de comunidades por otimização de modularidade (algoritmo greedy).")
        
        communities = display_cluster_data['communities']
        non_trivial = [c for c in communities if len(c) > 1]
        
        if non_trivial:
            for i, comm in enumerate(non_trivial, 1):
                member_names = [results['files'][idx] for idx in comm if idx < len(results['files'])]
                st.markdown(f"**Comunidade {i}** ({len(comm)} membros): " + ", ".join(f"`{f}`" for f in member_names))
        else:
            st.info("Nenhuma comunidade com mais de 1 membro detectada.")
