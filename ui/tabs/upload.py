"""
Upload tab for Niklaus UI.
"""

import streamlit as st
import tempfile
import shutil
from typing import Dict, Any, Tuple, List
from core.file_handler import FileHandler
from utils.config import config
from utils.exceptions import FileValidationError


def render_upload_tab(settings: Dict[str, Any]) -> Tuple[List[str], List[str], str, bool]:
    """
    Render upload tab.
    
    Args:
        settings: User settings from sidebar
    
    Returns:
        Tuple of (files, contents, extract_path, should_analyze)
    """
    st.title(":computer: Niklaus")
    st.markdown("### Assistente de Detecção de Plágio em Código")
    st.markdown("Niklaus compara arquivos de código-fonte e identifica similaridades usando análise estática e processamento paralelo.")
    
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
        _display_performance_estimate(settings)
    
    # Analyze button
    analyze_button = st.button(":mag: Analisar Arquivos", type="primary", use_container_width=True)
    
    # Last analysis info
    if st.session_state.get('last_analysis'):
        _display_last_analysis_summary()
    
    if analyze_button and zip_file:
        # Extract files
        try:
            handler = FileHandler()
            files, contents, extract_path = handler.extract_zip(zip_file, settings['language'])
            st.toast(f"✅ {len(files)} arquivos extraídos com sucesso!")
            return files, contents, extract_path, True
        except FileValidationError as e:
            st.error(f"Erro de validação: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"Erro ao extrair arquivo: {str(e)}")
            st.stop()
    
    return None, None, None, False


def _display_performance_estimate(settings: Dict[str, Any]) -> None:
    """Display performance estimate based on ZIP size."""
    with st.expander(":chart_with_upwards_trend: Estimativa de Performance"):
        from core.pipeline import AnalysisPipeline
        
        st.markdown("#### Estimativas baseadas no número de arquivos")
        
        pipeline = AnalysisPipeline(settings['language'], max_workers=settings['max_workers'])
        
        for files in [10, 20, 50]:
            stats = pipeline.get_performance_stats(files)
            st.markdown(f"**{files} arquivos:** ~{stats['estimated_total_time']:.1f}s com {settings['max_workers']} workers")
        
        st.info("Estimativas reais serão mostradas após extração dos arquivos.")


def _display_last_analysis_summary() -> None:
    """Display last analysis summary."""
    st.markdown("---")
    st.markdown("#### :clock1: Última Análise")
    
    last_analysis = st.session_state['last_analysis']
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Arquivos", last_analysis.get('files_count', len(last_analysis.get('files', []))))
    with col2:
        st.metric("Pares Suspeitos", last_analysis.get('similarities_count', len(last_analysis.get('suspicious_pairs', []))))
    
    if st.button("Ver Resultados", key="view_last_analysis"):
        st.session_state['show_last_analysis'] = True
        st.rerun()