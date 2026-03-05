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
    
    just_completed = bool(st.session_state.pop('analysis_just_completed', False))
    if just_completed:
        st.success("✅ Análise concluída. Você pode ver os detalhes nas abas de resultados.")

    # Check if there's a previous analysis
    has_previous_analysis = bool(st.session_state.get('last_analysis'))
    
    if has_previous_analysis and not just_completed:
        st.info("ℹ️ Há uma análise carregada. Você pode visualizar os resultados ou iniciar outra análise.")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📁 Limpar e Nova Análise", type="primary", use_container_width=True):
                # Clear previous analysis
                for key in ['last_analysis', 'advanced_analysis', 'cluster_data']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("✅ Preparado para nova análise! Faça upload dos arquivos abaixo.")
                st.rerun()
        
        with col2:
            if st.button("📊 Ver Resultados", type="secondary", use_container_width=True):
                st.info("Navegue para a aba 'Resultados' para ver os detalhes da análise carregada.")
        
        st.markdown("---")
    
    # File upload
    zip_file = st.file_uploader(
        "Carregar arquivo ZIP",
        type="zip",
        help=f"ZIP com arquivos (máx: {config.MAX_ZIP_SIZE_MB}MB)",
        key="zip_uploader"
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
            
            # Check minimum files
            if len(files) < 2:
                st.error("❌ Mínimo de arquivos insuficiente")
                st.warning("💡 **Solução:** O ZIP deve conter pelo menos 2 arquivos para análise de plágio.")
                return None, None, None, False
            
            return files, contents, extract_path, True
            
        except FileValidationError as e:
            st.error(f"❌ Erro de validação: {str(e)}")
            st.warning("💡 **Solução:** Verifique se o arquivo ZIP contém apenas código-fonte válido.")
            
            # File-specific suggestions
            if "tamanho" in str(e).lower():
                st.info(f"📚 Limite máximo: {config.MAX_ZIP_SIZE_MB}MB por arquivo ZIP")
            elif "formato" in str(e).lower():
                st.info("📚 Formatos aceitos: .py, .java, .cpp, .c, .js, .ts, .go, .rs, .kt")
            
            st.stop()
            
        except Exception as e:
            error_msg = str(e)
            
            st.error(f"❌ Erro ao extrair arquivo")
            
            # Specific error messages
            if "corrompido" in error_msg.lower() or "corrupted" in error_msg.lower():
                st.warning("💡 **Solução:** O arquivo ZIP está corrompido. Tente:")
                st.markdown("- Baixar o arquivo novamente")
                st.markdown("- Usar outro navegador")
                st.markdown("- Verificar a integridade do arquivo")
            
            elif "espaço" in error_msg.lower() or "space" in error_msg.lower():
                st.warning("💡 **Solução:** Espaço em disco insuficiente.")
                st.markdown("- Libere espaço em disco")
                st.markdown("- Limpe arquivos temporários")
            
            elif "permissão" in error_msg.lower() or "permission" in error_msg.lower():
                st.warning("💡 **Solução:** Sem permissão para escrever no diretório temporário.")
                st.markdown("- Execute o aplicativo com permissões adequadas")
            
            else:
                st.warning("💡 **Solução:** Tente novamente ou use outro arquivo ZIP.")
            
            with st.expander("🔍 Ver detalhes técnicos"):
                st.code(error_msg, language="text")
            
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
