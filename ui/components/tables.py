"""
Table components for Niklaus UI.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Tuple


def display_similarity_table(
    suspicious_pairs: List[Tuple[str, str, float]],
    threshold: float
) -> pd.DataFrame:
    """
    Display suspicious pairs in a formatted table.
    
    Args:
        suspicious_pairs: List of (file1, file2, similarity) tuples
        threshold: Similarity threshold
    
    Returns:
        Filtered DataFrame
    """
    if not suspicious_pairs:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df_data = []
    for file1, file2, sim in suspicious_pairs:
        df_data.append({
            'Arquivo 1': file1,
            'Arquivo 2': file2,
            'Similaridade': sim
        })
    
    df = pd.DataFrame(df_data)
    
    # Filter slider
    min_filter = st.slider(
        "Filtrar por similaridade mínima",
        min_value=0.0,
        max_value=float(df['Similaridade'].max()),
        value=threshold,
        step=0.01
    )
    
    filtered_df = df[df['Similaridade'] >= min_filter]
    
    # Display with progress bars
    st.dataframe(
        filtered_df.style.format({"Similaridade": "{:.2%}"}),
        use_container_width=True,
        column_config={
            "Similaridade": st.column_config.ProgressColumn(
                "Similaridade",
                format="%.2f%%",
                min_value=0,
                max_value=1,
            )
        }
    )
    
    return filtered_df


def display_metrics_table(metrics: List[Dict[str, Any]]) -> None:
    """
    Display code metrics in a formatted table.
    
    Args:
        metrics: List of metric dictionaries
    """
    if not metrics:
        st.warning("Métricas não disponíveis.")
        return
    
    df = pd.DataFrame(metrics)
    
    # Format columns
    if 'maintainability' in df.columns:
        df['maintainability'] = df['maintainability'].round(1)
    
    st.dataframe(df, use_container_width=True)


def display_ast_table(ast_similarities: List[Tuple]) -> None:
    """
    Display AST similarities in a formatted table.
    
    Args:
        ast_similarities: List of (file1, file2, similarity) tuples
    """
    if not ast_similarities:
        return
    
    df_data = []
    for item in ast_similarities:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            df_data.append({
                'Arquivo 1': item[0],
                'Arquivo 2': item[1],
                'Similaridade Estrutural': item[2]
            })
    
    if not df_data:
        return
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('Similaridade Estrutural', ascending=False)
    
    st.dataframe(
        df.style.format({"Similaridade Estrutural": "{:.2%}"}),
        use_container_width=True
    )


def display_cluster_table(cluster_data: Dict[str, Any]) -> None:
    """
    Display cluster information in a formatted table.
    
    Args:
        cluster_data: Cluster data dictionary
    """
    if not cluster_data or not cluster_data.get('clusters'):
        st.info("Nenhum cluster detectado.")
        return
    
    st.markdown("#### Detalhes por Cluster")
    
    # Show only clusters with more than 1 file
    suspicious_clusters = {
        cid: info for cid, info in cluster_data['clusters'].items()
        if info['size'] > 1
    }
    
    if not suspicious_clusters:
        st.success("Nenhum cluster suspeito detectado.")
        return
    
    for cid, info in sorted(suspicious_clusters.items(), key=lambda x: x[1]['size'], reverse=True):
        avg_sim = info['stats']['avg_similarity']
        max_sim = info['stats']['max_similarity']
        
        # Color badge by severity
        if avg_sim >= 0.9:
            badge = "🔴"
            label = "Suspeita Alta"
        elif avg_sim >= 0.7:
            badge = "🟠"
            label = "Suspeita Moderada"
        else:
            badge = "🟡"
            label = "Suspeita Baixa"
        
        with st.expander(f"{badge} Cluster {cid} — {info['size']} arquivos | {label} | Sim. média: {avg_sim:.1%}"):
            # Central files
            if info.get('central_files'):
                st.markdown("**Arquivos mais centrais** (possíveis originais):")
                for fname, centrality in info['central_files']:
                    st.markdown(f"- `{fname}` — centralidade: {centrality:.1%}")
            
            st.markdown("**Todos os arquivos no cluster:**")
            for fname in info['files']:
                st.markdown(f"- `{fname}`")
            
            st.markdown(f"""
            **Estatísticas do cluster:**
            - Similaridade média: `{avg_sim:.1%}`
            - Similaridade máxima: `{max_sim:.1%}`
            - Similaridade mínima: `{info['stats']['min_similarity']:.1%}`
            """)


def display_comparison_table(
    metrics1: Dict[str, Any],
    metrics2: Dict[str, Any],
    file1: str,
    file2: str
) -> None:
    """
    Display side-by-side metrics comparison.
    
    Args:
        metrics1: Metrics for first file
        metrics2: Metrics for second file
        file1: First filename
        file2: Second filename
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{file1}**")
        st.metric("Linhas de Código", metrics1['loc'])
        st.metric("Complexidade Ciclomática", metrics1['cyclomatic'])
        st.metric("Funções/Métodos", metrics1['functions'])
        st.metric("Profundidade Aninhamento", metrics1['nesting'])
        st.metric("Índice Manutenibilidade", f"{metrics1['maintainability']:.1f}")
    
    with col2:
        st.markdown(f"**{file2}**")
        st.metric("Linhas de Código", metrics2['loc'])
        st.metric("Complexidade Ciclomática", metrics2['cyclomatic'])
        st.metric("Funções/Métodos", metrics2['functions'])
        st.metric("Profundidade Aninhamento", metrics2['nesting'])
        st.metric("Índice Manutenibilidade", f"{metrics2['maintainability']:.1f}")