"""
Refactored Streamlit application using modular architecture.
This is a backward-compatible version that integrates all new modules.
"""

import io
import os
import time
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Import new modular architecture
from core.pipeline import AnalysisPipeline, LegacyAdapter
from core.persistence import AnalysisCache, SessionManager
from core.file_handler import FileHandler
from utils.config import config
from utils.logger import get_logger
from utils.exceptions import NiklausError, FileValidationError

# Import visualization helpers (from original app.py)
# We'll keep these functions for now and migrate later

logger = get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Niklaus - Detecção de Plágio",
        page_icon=":mag:",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'cancel': False,
        'last_analysis': None,
        'advanced_analysis': None,
        'cluster_data': None,
        'cache_stats': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar() -> Dict[str, Any]:
    """Render sidebar and return user settings."""
    
    with st.sidebar:
        st.markdown("## :gear: Configurações")
        
        # Theme selector
        theme = st.selectbox("Tema Visual", config.THEME_OPTIONS)
        _apply_theme(theme)
        
        st.markdown("---")
        
        # API Key validation
        try:
            api_key = st.secrets["maritaca"]["MARITACA_API_KEY"]
            model = st.secrets["maritaca"].get("MARITACA_MODEL", config.MARITACA_MODEL)
        except KeyError:
            st.error("Configure MARITACA_API_KEY no arquivo .streamlit/secrets.toml")
            st.info(_get_secrets_template())
            st.stop()
        
        st.markdown("### Linguagem")
        language = st.selectbox(
            "Escolha a linguagem de programação",
            options=list(config.LANGUAGE_EXTENSIONS.keys()),
            index=0,
            help="Selecione a linguagem dos arquivos"
        )
        
        st.markdown("### Análise")
        preset = st.selectbox(
            "Preset de análise",
            ["Personalizado", "Conservador (80%)", "Moderado (70%)", "Agressivo (50%)"]
        )
        
        presets = {
            "Conservador (80%)": 0.8,
            "Moderado (70%)": 0.7,
            "Agressivo (50%)": 0.5
        }
        
        default_limit = presets.get(preset, st.session_state.get('limit', config.DEFAULT_THRESHOLD))
        
        limit = st.slider(
            "Limite de Similaridade",
            min_value=0.0,
            max_value=1.0,
            value=default_limit,
            step=0.01,
            help="Selecione o limite de similaridade para considerar plágio"
        )
        
        st.markdown("### Performance")
        max_workers = st.slider(
            "Workers Paralelos",
            min_value=1,
            max_value=8,
            value=config.PARALLEL_WORKERS,
            help="Mais workers = análise mais rápida (use com cuidado)"
        )
        
        use_cache = st.checkbox("Usar cache", value=True, help="Armazena resultados para não reprocessar")
        enable_ai = st.checkbox("Análise com IA", value=True, help="Usa Maritaca para analisar plágio")
        
        st.markdown("---")
        st.markdown("### 📖 Instruções")
        st.markdown("1. Escolha a linguagem")
        st.markdown("2. Ajuste o limite")
        st.markdown("3. Faça upload do ZIP")
        st.markdown("4. Clique em 'Analisar'")
        
        st.markdown("---")
        st.markdown(":computer: [GitHub](https://www.github.com/walternagai/niklaus-plagiarism)")
    
    return {
        'api_key': api_key,
        'model': model,
        'language': language,
        'threshold': limit,
        'theme': theme,
        'max_workers': max_workers,
        'use_cache': use_cache,
        'enable_ai': enable_ai
    }


def _apply_theme(theme: str):
    """Apply visual theme."""
    if theme == "Escuro":
        st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #f0f0f0; }
        .stMarkdown, .stText { color: #f0f0f0; }
        </style>
        """, unsafe_allow_html=True)


def _get_secrets_template() -> str:
    """Return secrets.toml template."""
    return """
Crie o arquivo `.streamlit/secrets.toml`:

[maritaca]
MARITACA_API_KEY = "sua-chave-api-aqui"
MARITACA_MODEL = "sabiazinho-4"
"""


# ============================================================================
# FILE UPLOAD
# ============================================================================

def handle_file_upload(zip_file, language: str) -> Tuple[List[str], List[str], str]:
    """
    Handle file upload and extraction.
    
    Returns:
        Tuple of (files, contents, extract_path)
    """
    handler = FileHandler()
    
    try:
        files, contents, extract_path = handler.extract_zip(zip_file, language)
        logger.info(f"Extracted {len(files)} files from {zip_file.name}")
        return files, contents, extract_path
    except FileValidationError as e:
        st.error(f"Erro de validação: {str(e)}")
        st.stop()
    except Exception as e:
        logger.error(f"Failed to extract ZIP: {e}")
        st.error(f"Erro ao extrair arquivo: {str(e)}")
        st.stop()


# ============================================================================
# ANALYSIS EXECUTION
# ============================================================================

def run_analysis(
    files: List[str],
    contents: List[str],
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run complete plagiarism analysis using new pipeline.
    
    Args:
        files: List of filenames
        contents: List of file contents
        settings: User settings from sidebar
    
    Returns:
        Analysis results
    """
    logger.info(f"Starting analysis of {len(files)} files with {settings['max_workers']} workers")
    
    # Create pipeline
    pipeline = AnalysisPipeline(
        language=settings['language'],
        api_key=settings['api_key'] if settings['enable_ai'] else None,
        model=settings['model'],
        max_workers=settings['max_workers'],
        use_cache=settings['use_cache']
    )
    
    # Progress bar
    progress_bar = st.progress(0, text="Iniciando análise...")
    status_text = st.empty()
    
    def progress_callback(stage: str, current: int, total: int):
        """Update progress bar."""
        if total > 0:
            pct = current / total
            progress_bar.progress(pct, text=f"{stage}: {current}/{total}")
    
    try:
        # Run analysis
        results = pipeline.run_full_analysis(
            files=files,
            contents=contents,
            threshold=settings['threshold'],
            enable_ai=settings['enable_ai'],
            progress_callback=progress_callback
        )
        
        progress_bar.progress(100, text="Análise concluída!")
        
        logger.info(f"Analysis completed in {results['analysis_time']:.2f}s")
        
        return results
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        st.error(f"Erro na análise: {str(e)}")
        st.stop()


# ============================================================================
# RESULTS DISPLAY
# ============================================================================

def display_results(results: Dict[str, Any], settings: Dict[str, Any]):
    """Display analysis results in tabs."""
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":bar_chart: Resultados",
        ":chart_with_upwards_trend: Estatísticas",
        ":microscope: Análise Avançada",
        ":spider_web: Grafo de Similaridade",
        ":information_source: Info"
    ])
    
    with tab1:
        display_results_tab(results, settings)
    
    with tab2:
        display_statistics_tab(results)
    
    with tab3:
        display_advanced_tab(results)
    
    with tab4:
        display_graph_tab(results)
    
    with tab5:
        display_info_tab(results, settings)


def display_results_tab(results: Dict[str, Any], settings: Dict[str, Any]):
    """Display main results tab."""
    
    st.markdown("### :bar_chart: Resultados da Análise")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Arquivos Analisados", len(results['files']))
    with col2:
        st.metric("Pares Suspeitos", len(results['suspicious_pairs']))
    with col3:
        if results['suspicious_pairs']:
            max_sim = max(s[2] for s in results['suspicious_pairs'])
            st.metric("Maior Similaridade", f"{max_sim:.1%}")
    with col4:
        st.metric("Tempo de Análise", f"{results['analysis_time']:.2f}s")
    
    st.markdown("---")
    
    # Suspicious pairs table
    if results['suspicious_pairs']:
        st.markdown("### Pares com Similaridade Suspeita")
        
        # Convert to DataFrame
        df_data = []
        for file1, file2, sim in results['suspicious_pairs']:
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
            value=settings['threshold'],
            step=0.01
        )
        
        filtered_df = df[df['Similaridade'] >= min_filter]
        
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
        
        # AI Analysis (if available)
        if results.get('ai_analyses'):
            st.markdown("### :notebook: Análises com IA")
            
            for file1, file2, sim in results['suspicious_pairs']:
                key = f"{file1}_{file2}"
                if key in results['ai_analyses']:
                    with st.expander(f":mag_right: {file1} ↔ {file2} - {sim:.1%}"):
                        st.write(results['ai_analyses'][key])
        
        # Export
        st.markdown("---")
        st.markdown("### :inbox_tray: Exportar Resultados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "📥 Baixar CSV",
                data=csv,
                file_name=f"similaridade_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            report = {
                "timestamp": datetime.now().isoformat(),
                "language": results['language'],
                "threshold": results['threshold'],
                "files": results['files'],
                "suspicious_pairs": [
                    {"file1": f1, "file2": f2, "similarity": float(s)}
                    for f1, f2, s in results['suspicious_pairs']
                ]
            }
            st.download_button(
                "📥 Baixar JSON",
                data=json.dumps(report, indent=2, ensure_ascii=False),
                file_name=f"relatorio_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            if st.button("📥 Baixar PDF", use_container_width=True):
                st.info("PDF export será implementado na próxima fase")
    
    else:
        st.success("✅ Não foram encontrados trechos de código plagiados abaixo do limite definido.")


def display_statistics_tab(results: Dict[str, Any]):
    """Display statistics tab."""
    
    st.markdown("### :chart_with_upwards_trend: Estatísticas e Visualizações")
    
    if not results['suspicious_pairs']:
        st.info("Sem dados estatísticos disponíveis.")
        return
    
    # Metrics
    similarities = [s[2] for s in results['suspicious_pairs']]
    
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
    
    files = results['files']
    matrix = np.array(results['similarity_matrix'])
    
    fig = px.imshow(
        matrix,
        x=files,
        y=files,
        color_continuous_scale="RdYlGn_r",
        labels=dict(x="Arquivo", y="Arquivo", color="Similaridade"),
        title="Matriz de Similaridade entre Arquivos",
        aspect="auto"
    )
    fig.update_layout(xaxis_tickangle=-45, width=800, height=800)
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribution
    st.markdown("### :bar_chart: Distribuição de Similaridades")
    
    hist_df = pd.DataFrame({'Similaridade': similarities})
    hist_df['Faixa'] = pd.cut(
        hist_df['Similaridade'],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
    )
    
    hist_fig = px.bar(
        hist_df['Faixa'].value_counts().sort_index(),
        title="Distribuição de Pares por Faixa de Similaridade",
        labels={'index': 'Faixa', 'value': 'Quantidade'},
        color='value',
        color_continuous_scale='Viridis'
    )
    st.plotly_chart(hist_fig, use_container_width=True)


def display_advanced_tab(results: Dict[str, Any]):
    """Display advanced analysis tab."""
    
    st.markdown("### :microscope: Análise Avançada de Código")
    st.markdown("**Análise estrutural (AST), métricas de complexidade e detecção de padrões de plágio**")
    
    if not results.get('metrics'):
        st.warning("Métricas não disponíveis. Execute uma análise primeiro.")
        return
    
    # AST Similarities
    st.markdown("#### Similaridade Estrutural (AST)")
    st.info("A similaridade estrutural compara a árvore sintática do código, identificando similaridades mesmo com variáveis renomeadas ou código reorganizado.")
    
    if results.get('ast_similarities'):
        ast_df_data = []
        for item in results['ast_similarities']:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                ast_df_data.append({
                    'Arquivo 1': item[0],
                    'Arquivo 2': item[1],
                    'Similaridade Estrutural': item[2]
                })
        
        if ast_df_data:
            ast_df = pd.DataFrame(ast_df_data)
            ast_df = ast_df.sort_values('Similaridade Estrutural', ascending=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Similaridade Estrutural Média", f"{ast_df['Similaridade Estrutural'].mean():.1%}")
            with col2:
                st.metric("Similaridade Estrutural Máxima", f"{ast_df['Similaridade Estrutural'].max():.1%}")
            
            st.dataframe(
                ast_df.style.format({"Similaridade Estrutural": "{:.2%}"}),
                use_container_width=True
            )
    
    # Metrics
    st.markdown("---")
    st.markdown("#### Métricas de Complexidade")
    
    metrics_df = pd.DataFrame(results['metrics'])
    st.dataframe(metrics_df, use_container_width=True)
    
    # Patterns
    if results.get('patterns'):
        st.markdown("---")
        st.markdown("#### Padrões de Plágio Detectados")
        
        for key, pattern in results['patterns'].items():
            with st.expander(f":mag: {key}"):
                st.markdown(f"**Tipo:** {pattern.get('plagiarism_type', 'N/A')}")
                st.markdown(f"**Confiança:** {pattern.get('confidence', 0):.1%}")
                st.markdown(f"**Explicação:** {pattern.get('explanation', 'N/A')}")


def display_graph_tab(results: Dict[str, Any]):
    """Display similarity graph tab."""
    
    st.markdown("### :spider_web: Grafo de Similaridade")
    st.markdown(
        "Cada **nó** representa um arquivo. "
        "As **arestas** conectam pares com similaridade acima do limiar."
    )
    
    cluster_data = results.get('cluster_data')
    
    if cluster_data:
        # Summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de clusters", cluster_data['num_clusters'])
        with col2:
            st.metric("Maior cluster", f"{cluster_data['largest_cluster']} arquivos")
        with col3:
            st.metric("Arestas no grafo", cluster_data['graph_edges'])
        with col4:
            density_pct = cluster_data['graph_density'] * 100
            st.metric("Densidade do grafo", f"{density_pct:.1f}%")
        
        # Note about visualization
        st.info("Visualização interativa do grafo será implementada na próxima fase usando Plotly NetworkX.")
    else:
        st.info("Execute uma análise para visualizar o grafo de similaridade.")


def display_info_tab(results: Dict[str, Any], settings: Dict[str, Any]):
    """Display information tab."""
    
    st.markdown("### :information_source: Informações da Análise")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Configurações")
        st.markdown(f"- **Linguagem:** {results['language']}")
        st.markdown(f"- **Limite de Similaridade:** {results['threshold']:.0%}")
        st.markdown(f"- **Workers Paralelos:** {settings['max_workers']}")
        st.markdown(f"- **Cache:** {'Ativado' if settings['use_cache'] else 'Desativado'}")
        st.markdown(f"- **Análise com IA:** {'Ativada' if settings['enable_ai'] else 'Desativada'}")
    
    with col2:
        st.markdown("#### Estatísticas")
        st.markdown(f"- **Arquivos Analisados:** {len(results['files'])}")
        st.markdown(f"- **Comparações Realizadas:** {len(results['textual_similarities'])}")
        st.markdown(f"- **Pares Suspeitos:** {len(results['suspicious_pairs'])}")
        st.markdown(f"- **Tempo Total:** {results['analysis_time']:.2f}s")
    
    # Cache stats
    if settings['use_cache']:
        st.markdown("---")
        st.markdown("#### Estatísticas de Cache")
        
        cache = AnalysisCache()
        stats = cache.get_cache_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Arquivos de Cache", stats['file_count'])
        with col2:
            st.metric("Tamanho Total", f"{stats['total_size_mb']:.2f} MB")
        with col3:
            if stats.get('newest_cache'):
                st.metric("Cache Mais Recente", stats['newest_cache'][:19])


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    
    # Setup
    setup_page_config()
    init_session_state()
    
    # Render sidebar and get settings
    settings = render_sidebar()
    
    # Tabs
    tab1, tab2 = st.tabs([":file_folder: Upload & Análise", ":clipboard: Última Análise"])
    
    with tab1:
        st.title(":computer: Niklaus")
        st.markdown("### Assistente de Detecção de Plágio em Código")
        st.markdown("Niklaus compara arquivos de código-fonte e identifica similaridades usando análise estática e inteligência artificial.")
        
        st.markdown("---")
        
        # File upload
        zip_file = st.file_uploader(
            "Carregar arquivo ZIP",
            type="zip",
            help=f"ZIP com arquivos (máx: {config.MAX_ZIP_SIZE_MB}MB)"
        )
        
        if zip_file:
            st.info(f"Arquivo: {zip_file.name} ({zip_file.size / 1024 / 1024:.2f} MB)")
        
        # Performance estimate
        if zip_file:
            with st.expander(":chart_with_upwards_trend: Estimativa de Performance"):
                st.markdown("#### Estimativas baseadas no tamanho do arquivo")
                
                # Note: We don't know exact file count until extraction
                st.info("As estimativas serão mostradas após a extração dos arquivos.")
                
                # Show general estimates
                estimate_pipeline = AnalysisPipeline(
                    settings['language'],
                    max_workers=settings['max_workers']
                )
                
                for files in [10, 20, 50]:
                    stats = estimate_pipeline.get_performance_stats(files)
                    st.markdown(f"**{files} arquivos:** ~{stats['estimated_total_time']:.1f}s com {settings['max_workers']} workers")
        
        analyze_button = st.button(":mag: Analisar Arquivos", type="primary", use_container_width=True)
        
        if analyze_button and zip_file:
            # Extract files
            with st.spinner("Extraindo arquivos..."):
                files, contents, extract_path = handle_file_upload(zip_file, settings['language'])
                st.toast(f"✅ {len(files)} arquivos extraídos com sucesso!")
            
            # Performance estimate
            with st.expander("📊 Estimativa de Tempo"):
                pipeline = AnalysisPipeline(settings['language'], max_workers=settings['max_workers'])
                stats = pipeline.get_performance_stats(len(files))
                st.markdown(f"""
                - **Arquivos:** {stats['files']}
                - **Comparações:** {stats['comparisons']}
                - **Tempo Estimado:** {stats['estimated_total_time']:.1f}s
                - **Workers:** {stats['parallel_workers']} (speedup {stats['speedup_factor']}x)
                """)
            
            # Run analysis
            results = run_analysis(files, contents, settings)
            
            # Store in session
            st.session_state['last_analysis'] = results
            st.session_state['settings'] = settings
            
            # Cleanup
            try:
                shutil.rmtree(extract_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup {extract_path}: {e}")
            
            st.toast("✅ Análise concluída com sucesso!")
            st.rerun()
    
    with tab2:
        if st.session_state.get('last_analysis'):
            results = st.session_state['last_analysis']
            settings = st.session_state.get('settings', {})
            display_results(results, settings)
        else:
            st.info("Nenhuma análise disponível. Execute uma análise primeiro.")


if __name__ == "__main__":
    main()