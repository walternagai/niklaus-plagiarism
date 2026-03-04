"""
Charts components for Niklaus UI.
"""

import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from typing import List, Dict, Any, Optional
import os


def create_similarity_heatmap(files: List[str], similarity_matrix: np.ndarray) -> go.Figure:
    """
    Create interactive similarity heatmap.
    
    Args:
        files: List of filenames
        similarity_matrix: NxN similarity matrix
    
    Returns:
        Plotly Figure object
    """
    fig = px.imshow(
        similarity_matrix,
        x=files,
        y=files,
        color_continuous_scale="RdYlGn_r",
        labels=dict(x="Arquivo", y="Arquivo", color="Similaridade"),
        title="Matriz de Similaridade entre Arquivos",
        aspect="auto"
    )
    
    fig.update_layout(
        xaxis_tickangle=-45,
        width=800,
        height=800
    )
    
    fig.update_traces(
        hovertemplate="Similaridade: %{z:.2%}<extra></extra>"
    )
    
    return fig


def create_similarity_graph(
    similarity_matrix: np.ndarray,
    files: List[str],
    min_similarity: float = 0.5,
    cluster_data: Dict = None
) -> Optional[go.Figure]:
    """
    Create interactive similarity network graph.
    
    Args:
        similarity_matrix: NxN similarity matrix
        files: List of filenames
        min_similarity: Minimum similarity for edges
        cluster_data: Cluster information for node colors
    
    Returns:
        Plotly Figure object or None if no edges
    """
    import networkx as nx
    
    n = len(files)
    mat = np.array(similarity_matrix)
    
    G = nx.Graph()
    
    # Add nodes
    for i, f in enumerate(files):
        G.add_node(i, label=f)
    
    # Add edges
    for i in range(n):
        for j in range(i + 1, n):
            if mat[i, j] >= min_similarity:
                G.add_edge(i, j, weight=mat[i, j])
    
    if G.number_of_nodes() == 0:
        return None
    
    # Layout
    if G.number_of_edges() > 0:
        pos = nx.spring_layout(G, weight='weight', seed=42, k=1.5)
    else:
        pos = nx.circular_layout(G)
    
    # Node colors based on clusters
    node_colors = _get_node_colors(n, cluster_data, files)
    
    # Edge traces
    edge_traces = []
    for i, j, data in G.edges(data=True):
        x0, y0 = pos[i]
        x1, y1 = pos[j]
        sim = data['weight']
        opacity = 0.3 + 0.7 * (sim - min_similarity) / max(1 - min_similarity, 0.01)
        width = 1 + 5 * (sim - min_similarity) / max(1 - min_similarity, 0.01)
        
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=width, color=f'rgba(150,150,150,{opacity:.2f})'),
            hovertemplate=f'{files[i]} ↔ {files[j]}: {sim:.1%}<extra></extra>',
            showlegend=False
        ))
    
    # Node trace
    node_x = [pos[i][0] for i in range(n)]
    node_y = [pos[i][1] for i in range(n)]
    
    # Node sizes based on degree
    degrees = dict(G.degree())
    node_sizes = [20 + degrees.get(i, 0) * 5 for i in range(n)]
    
    # Hover text
    hover_texts = _build_hover_texts(G, mat, files, n)
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=[os.path.splitext(f)[0] for f in files],
        textposition='top center',
        textfont=dict(size=10),
        hovertext=hover_texts,
        hoverinfo='text',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white'),
            opacity=0.9
        ),
        showlegend=False
    )
    
    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title=dict(
            text=f"Grafo de Similaridade (limiar ≥ {min_similarity:.0%})",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        hovermode='closest',
        margin=dict(l=20, r=20, t=60, b=20),
        height=600,
        plot_bgcolor='rgba(250,250,250,0.8)',
    )
    
    return fig


def _get_node_colors(n: int, cluster_data: Dict, files: List[str]) -> List[str]:
    """Get node colors based on clusters."""
    node_colors = ['#636EFA'] * n
    
    if cluster_data and 'clusters' in cluster_data:
        palette = [
            '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
            '#19D3F3', '#FF6692', '#B6E880', '#FF97FF',
            '#FECB52', '#636EFA'
        ]
        
        for cid, info in cluster_data['clusters'].items():
            color = palette[(int(cid) - 1) % len(palette)]
            for fname in info['files']:
                if fname in files:
                    node_colors[files.index(fname)] = color
    
    return node_colors


def _build_hover_texts(G, mat, files: List[str], n: int) -> List[str]:
    """Build hover texts for nodes."""
    hover_texts = []
    
    for i, fname in enumerate(files):
        neighbors = list(G.neighbors(i))
        if neighbors:
            sims = [mat[i, j] for j in neighbors]
            hover_texts.append(
                f"<b>{fname}</b><br>"
                f"Conexões: {len(neighbors)}<br>"
                f"Sim. média: {np.mean(sims):.1%}<br>"
                f"Sim. máx: {np.max(sims):.1%}"
            )
        else:
            hover_texts.append(f"<b>{fname}</b><br>Sem conexões acima do limiar")
    
    return hover_texts


def create_metrics_radar_chart(
    metrics1: Dict[str, Any],
    metrics2: Dict[str, Any],
    file1: str,
    file2: str
) -> go.Figure:
    """
    Create radar chart comparing metrics between two files.
    
    Args:
        metrics1: Metrics for first file
        metrics2: Metrics for second file
        file1: First filename
        file2: Second filename
    
    Returns:
        Plotly Figure object
    """
    categories = ['LOC', 'Complexidade', 'Funções', 'Aninhamento', 'Manutenibilidade']
    
    # Normalize values
    max_loc = max(metrics1['loc'], metrics2['loc'], 1)
    max_cc = max(metrics1['cyclomatic'], metrics2['cyclomatic'], 1)
    max_func = max(metrics1['functions'], metrics2['functions'], 1)
    max_nest = max(metrics1['nesting'], metrics2['nesting'], 1)
    
    values1 = [
        metrics1['loc'] / max_loc,
        metrics1['cyclomatic'] / max_cc,
        metrics1['functions'] / max_func,
        metrics1['nesting'] / max_nest,
        metrics1['maintainability'] / 100
    ]
    
    values2 = [
        metrics2['loc'] / max_loc,
        metrics2['cyclomatic'] / max_cc,
        metrics2['functions'] / max_func,
        metrics2['nesting'] / max_nest,
        metrics2['maintainability'] / 100
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values1,
        theta=categories,
        fill='toself',
        name=file1,
        line_color='blue'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=values2,
        theta=categories,
        fill='toself',
        name=file2,
        line_color='red'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title="Comparação de Métricas"
    )
    
    return fig


def create_distribution_histogram(similarities: List[float]) -> go.Figure:
    """
    Create histogram of similarity distribution.
    
    Args:
        similarities: List of similarity values
    
    Returns:
        Plotly Figure object
    """
    import pandas as pd
    
    df = pd.DataFrame({'Similaridade': similarities})
    df['Faixa'] = pd.cut(
        df['Similaridade'],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
    )
    
    fig = px.bar(
        df['Faixa'].value_counts().sort_index(),
        title="Distribuição de Pares por Faixa de Similaridade",
        labels={'index': 'Faixa', 'value': 'Quantidade'},
        color='value',
        color_continuous_scale='Viridis'
    )
    
    return fig