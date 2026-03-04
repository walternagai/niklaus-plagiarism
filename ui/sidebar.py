"""
Sidebar UI component for Niklaus plagiarism detector.
"""

import streamlit as st
from typing import Dict, Any
from utils.config import config


def render_sidebar() -> Dict[str, Any]:
    """
    Render sidebar with configuration options.
    
    Returns:
        Dictionary with user settings
    """
    with st.sidebar:
        st.markdown("## :gear: Configurações")
        
        # Theme selector
        theme = _render_theme_selector()
        
        st.markdown("---")
        
        # API configuration
        api_key, model = _render_api_config()
        
        # Language selection
        language = _render_language_selector()
        
        # Analysis configuration
        threshold, preset = _render_analysis_config()
        
        # Performance configuration
        max_workers, use_cache, enable_ai = _render_performance_config()
        
        # Instructions
        _render_instructions()
        
        # Footer
        st.markdown("---")
        st.markdown(":computer: [GitHub](https://www.github.com/walternagai/niklaus-plagiarism)")
    
    return {
        'api_key': api_key,
        'model': model,
        'language': language,
        'threshold': threshold,
        'theme': theme,
        'max_workers': max_workers,
        'use_cache': use_cache,
        'enable_ai': enable_ai,
        'preset': preset
    }


def _render_theme_selector() -> str:
    """Render theme selector."""
    theme = st.selectbox("Tema Visual", config.THEME_OPTIONS)
    
    if theme == "Escuro":
        st.markdown("""
        <style>
        .stApp { background-color: #1e1e1e; color: #f0f0f0; }
        .stMarkdown, .stText { color: #f0f0f0; }
        </style>
        """, unsafe_allow_html=True)
    
    return theme


def _render_api_config() -> tuple:
    """Render API configuration section."""
    try:
        api_key = st.secrets["maritaca"]["MARITACA_API_KEY"]
        model = st.secrets["maritaca"].get("MARITACA_MODEL", config.MARITACA_MODEL)
        st.success("✅ API configurada")
    except KeyError:
        st.error("Configure MARITACA_API_KEY no arquivo .streamlit/secrets.toml")
        with st.expander("📝 Como configurar"):
            st.code("""
[maritaca]
MARITACA_API_KEY = "sua-chave-api-aqui"
MARITACA_MODEL = "sabiazinho-4"
            """, language="toml")
        st.stop()
    
    return api_key, model


def _render_language_selector() -> str:
    """Render language selector."""
    st.markdown("### Linguagem")
    
    language = st.selectbox(
        "Escolha a linguagem de programação",
        options=list(config.LANGUAGE_EXTENSIONS.keys()),
        index=0,
        help="Selecione a linguagem dos arquivos"
    )
    
    return language


def _render_analysis_config() -> tuple:
    """Render analysis configuration section."""
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
    
    default_threshold = presets.get(preset, st.session_state.get('threshold', config.DEFAULT_THRESHOLD))
    
    threshold = st.slider(
        "Limite de Similaridade",
        min_value=0.0,
        max_value=1.0,
        value=default_threshold,
        step=0.01,
        help="Similaridade mínima para considerar plágio"
    )
    
    return threshold, preset


def _render_performance_config() -> tuple:
    """Render performance configuration section."""
    st.markdown("### Performance")
    
    max_workers = st.slider(
        "Workers Paralelos",
        min_value=1,
        max_value=8,
        value=config.PARALLEL_WORKERS,
        help="Mais workers = análise mais rápida (use com cuidado)"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        use_cache = st.checkbox(
            "Usar cache",
            value=True,
            help="Armazena resultados para não reprocessar"
        )
    
    with col2:
        enable_ai = st.checkbox(
            "Análise com IA",
            value=True,
            help="Usa Maritaca para analisar plágio"
        )
    
    if use_cache:
        _render_cache_stats()
    
    return max_workers, use_cache, enable_ai


def _render_cache_stats():
    """Render cache statistics."""
    from core.persistence import AnalysisCache
    
    try:
        cache = AnalysisCache()
        stats = cache.get_cache_stats()
        
        with st.expander("📊 Cache Stats"):
            st.metric("Arquivos", stats['file_count'])
            st.metric("Tamanho", f"{stats['total_size_mb']:.2f} MB")
            
            if st.button("🗑️ Limpar Cache"):
                removed = cache.clear_all_cache()
                st.success(f"Removidos {removed} arquivos")
                st.rerun()
    except Exception:
        pass


def _render_instructions():
    """Render instructions section."""
    st.markdown("---")
    st.markdown("### 📖 Instruções")
    st.markdown("1. Escolha a linguagem")
    st.markdown("2. Ajuste o limite")
    st.markdown("3. Faça upload do ZIP")
    st.markdown("4. Clique em 'Analisar'")