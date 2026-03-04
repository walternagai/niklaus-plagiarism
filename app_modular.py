"""
Main modular application for Niklaus plagiarism detector.
This version uses the modular UI architecture.
"""

import streamlit as st
from typing import Dict, Any, List
import shutil

# Import modular components
from ui.sidebar import render_sidebar
from ui.tabs.upload import render_upload_tab
from ui.tabs.results import render_results_tab
from ui.tabs.statistics import render_statistics_tab
from ui.tabs.advanced import render_advanced_tab
from ui.tabs.graph import render_graph_tab

# Import core modules
from core.pipeline import AnalysisPipeline
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="Niklaus - Detecção de Plágio",
        page_icon=":mag:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    _init_session_state()
    
    # Render sidebar and get settings
    settings = render_sidebar()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":file_folder: Upload & Análise",
        ":bar_chart: Resultados",
        ":chart_with_upwards_trend: Estatísticas",
        ":microscope: Análise Avançada",
        ":spider_web: Grafo de Similaridade"
    ])
    
    # Tab 1: Upload
    with tab1:
        files, contents, extract_path, should_analyze = render_upload_tab(settings)
        
        if should_analyze and files and contents:
            # Run analysis
            results = _run_analysis(files, contents, settings)
            
            # Store in session
            st.session_state['last_analysis'] = results
            st.session_state['settings'] = settings
            
            # Cleanup
            if extract_path:
                shutil.rmtree(extract_path, ignore_errors=True)
            
            st.toast("✅ Análise concluída com sucesso!")
            st.rerun()
    
    # Render other tabs if analysis is available
    if st.session_state.get('last_analysis'):
        results = st.session_state['last_analysis']
        settings = st.session_state.get('settings', {})
        
        with tab2:
            render_results_tab(results, settings)
        
        with tab3:
            render_statistics_tab(results)
        
        with tab4:
            render_advanced_tab(results)
        
        with tab5:
            render_graph_tab(results)
    
    else:
        # Show info in other tabs if no analysis
        if not should_analyze:
            with tab2:
                st.info("Nenhum resultado disponível. Execute uma análise primeiro.")
            with tab3:
                st.info("Nenhuma estatística disponível. Execute uma análise primeiro.")
            with tab4:
                st.info("Nenhuma análise avançada disponível. Execute uma análise primeiro.")
            with tab5:
                st.info("Nenhum grafo disponível. Execute uma análise primeiro.")


def _init_session_state():
    """Initialize session state variables."""
    defaults = {
        'cancel': False,
        'last_analysis': None,
        'advanced_analysis': None,
        'cluster_data': None,
        'settings': {}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_analysis(files: List[str], contents: List[str], settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run analysis using AnalysisPipeline.
    
    Args:
        files: List of filenames
        contents: List of file contents
        settings: User settings
    
    Returns:
        Analysis results
    """
    logger.info(f"Starting analysis of {len(files)} files")
    
    # Create pipeline
    pipeline = AnalysisPipeline(
        language=settings['language'],
        api_key=settings['api_key'] if settings['enable_ai'] else None,
        model=settings['model'],
        max_workers=settings['max_workers'],
        use_cache=settings['use_cache']
    )
    
    # Progress tracking
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


if __name__ == "__main__":
    main()