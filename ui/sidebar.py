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
        # Header
        _render_header()
        
        # Quick Presets
        _render_quick_presets()
        
        # API configuration
        api_key, model = _render_api_config()
        
        # Language selection
        language = _render_language_selector()
        
        # Analysis configuration
        threshold = _render_analysis_config()
        
        # Performance configuration
        max_workers, use_cache, enable_ai = _render_performance_config()
        
        # Instructions
        _render_instructions()
        
        # Footer
        _render_footer()
    
    return {
        'api_key': api_key,
        'model': model,
        'language': language,
        'threshold': threshold,
        'max_workers': max_workers,
        'use_cache': use_cache,
        'enable_ai': enable_ai,
    }


def _render_quick_presets():
    """Render quick preset buttons for common configurations."""
    st.markdown("### ⚡ Presets Rápidos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Rápido", use_container_width=True, help="Análise rápida com configurações básicas"):
            st.session_state['preset_mode'] = 'quick'
            st.session_state['threshold'] = 0.8
            st.session_state['max_workers'] = 2
            st.session_state['enable_ai'] = False
            st.session_state['use_cache'] = True
            st.toast("✅ Preset Rápido aplicado!")
            st.rerun()
    
    with col2:
        if st.button("🔍 Completo", use_container_width=True, help="Análise completa com IA"):
            st.session_state['preset_mode'] = 'full'
            st.session_state['threshold'] = 0.7
            st.session_state['max_workers'] = 4
            st.session_state['enable_ai'] = True
            st.session_state['use_cache'] = True
            st.toast("✅ Preset Completo aplicado!")
            st.rerun()
    
    with col3:
        if st.button("⚙️ Personalizado", use_container_width=True, help="Use configurações personalizadas"):
            st.session_state['preset_mode'] = 'custom'
            st.toast("ℹ️ Configure as opções abaixo")
    
    st.markdown("---")


def _render_header():
    """Render sidebar header with branding."""
    st.markdown(
        """
        <div style='text-align: center; padding: 10px 0;'>
            <h1 style='margin: 0; color: #1f77b4; font-size: 28px;'>🔍 Niklaus</h1>
            <p style='margin: 5px 0 0 0; font-size: 14px; color: #666;'>Detector de Plágio</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")


def _render_api_config() -> tuple:
    """Render API configuration section."""
    st.markdown("### 🔑 API")
    
    with st.container():
        try:
            api_key = st.secrets["maritaca"]["MARITACA_API_KEY"]
            model = st.secrets["maritaca"].get("MARITACA_MODEL", config.MARITACA_MODEL)
            
            st.success("✅ API configurada")
            st.caption(f"Modelo: `{model}`")
            
        except KeyError:
            st.error("❌ API não configurada")
            
            with st.expander("⚙️ Como configurar", expanded=True):
                st.markdown("""
                **1. Crie o arquivo `.streamlit/secrets.toml`:**
                """)
                st.code("""
[maritaca]
MARITACA_API_KEY = "sua-chave-api-aqui"
MARITACA_MODEL = "sabiazinho-4"
                """, language="toml")
                
                st.markdown("""
                **2. Obtenha sua chave em:**
                - [Maritaca AI](https://maritaca.ai)
                """)
                
            st.stop()
    
    return api_key, model


def _render_language_selector() -> str:
    """Render language selector."""
    st.markdown("### 💻 Linguagem")
    
    language = st.selectbox(
        "Selecione a linguagem",
        options=list(config.LANGUAGE_EXTENSIONS.keys()),
        index=0,
        help="Linguagem de programação dos arquivos"
    )
    
    ext = config.LANGUAGE_EXTENSIONS.get(language, 'py')
    st.caption(f"Extensão: `.{ext}`")
    
    return language


def _render_analysis_config() -> float:
    """Render analysis configuration section."""
    st.markdown("### 📊 Análise")

    default_threshold = st.session_state.get('threshold', config.DEFAULT_THRESHOLD)

    # Threshold preset shortcut buttons
    st.caption("Atalhos de sensibilidade:")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🔴 50%", use_container_width=True, help="Agressivo — detecta mais"):
            st.session_state['threshold'] = 0.5
    with col_b:
        if st.button("🟡 70%", use_container_width=True, help="Moderado — equilibrado"):
            st.session_state['threshold'] = 0.7
    with col_c:
        if st.button("🟢 80%", use_container_width=True, help="Conservador — alta confiança"):
            st.session_state['threshold'] = 0.8

    threshold = st.slider(
        "Similaridade mínima",
        min_value=0.0,
        max_value=1.0,
        value=default_threshold,
        step=0.01,
        key='threshold',
        help="Pares com similaridade ≥ este valor serão marcados",
    )

    if threshold < 0.4:
        st.warning("⚠️ Muito sensível - pode gerar muitos falsos positivos")
    elif threshold < 0.6:
        st.info("ℹ️ Alta sensibilidade - resultados detalhados")
    elif threshold < 0.8:
        st.success("✅ Sensibilidade moderada - equilibrado")
    else:
        st.success("✅ Conservador - alta confiança")

    return threshold


def _render_performance_config() -> tuple:
    """Render performance configuration section."""
    st.markdown("### ⚡ Performance")
    
    # Get preset values if available
    default_workers = st.session_state.get('max_workers', config.PARALLEL_WORKERS)
    default_cache = st.session_state.get('use_cache', True)
    default_ai = st.session_state.get('enable_ai', True)
    
    # Parallel workers
    max_workers = st.slider(
        "Workers paralelos",
        min_value=1,
        max_value=8,
        value=default_workers,
        help="Mais workers = análise mais rápida"
    )
    
    # Checkboxes for cache and AI
    col1, col2 = st.columns(2)
    
    with col1:
        use_cache = st.checkbox(
            "💾 Cache",
            value=default_cache,
            help="Reutiliza resultados anteriores"
        )
    
    with col2:
        enable_ai = st.checkbox(
            "🤖 IA",
            value=default_ai,
            help="Análise avançada com Maritaca"
        )
    
    # Cache stats
    if use_cache:
        _render_cache_stats()
    
    return max_workers, use_cache, enable_ai


def _render_cache_stats():
    """Render cache statistics."""
    from core.persistence import AnalysisCache
    
    try:
        cache = AnalysisCache()
        stats = cache.get_cache_stats()
        
        with st.expander("📈 Estatísticas do Cache", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Arquivos", stats['file_count'])
            
            with col2:
                st.metric("Tamanho", f"{stats['total_size_mb']:.2f} MB")
            
            if st.button("🗑️ Limpar Cache", use_container_width=True, type="secondary"):
                removed = cache.clear_all_cache()
                st.success(f"✓ {removed} arquivos removidos")
                st.rerun()
                
    except Exception:
        pass


def _render_instructions():
    """Render instructions section."""
    st.markdown("---")
    st.markdown("### 📖 Como usar")
    
    st.markdown("""
**Passos para usar:**

1️⃣ Configure a API
2️⃣ Selecione a linguagem  
3️⃣ Ajuste o threshold
4️⃣ Faça upload do ZIP
5️⃣ Clique em analisar
""")


def _render_footer():
    """Render sidebar footer."""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center;'>
            <small>
                <a href='https://www.github.com/walternagai/niklaus-plagiarism' target='_blank'>
                    💻 GitHub
                </a>
            </small>
        </div>
        """,
        unsafe_allow_html=True
    )