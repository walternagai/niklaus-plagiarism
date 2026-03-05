"""
Main modular application for Niklaus plagiarism detector.
This version uses the modular UI architecture with authentication.
"""

import streamlit as st
from typing import Dict, Any, List
import shutil
import math
import secrets

from ui.sidebar import render_sidebar
from ui.tabs.upload import render_upload_tab
from ui.tabs.results import render_results_tab
from ui.tabs.statistics import render_statistics_tab
from ui.tabs.advanced import render_advanced_tab
from ui.tabs.graph import render_graph_tab
from ui.tabs.history import render_history_tab

from core.pipeline import AnalysisPipeline
from utils.logger import get_logger
from auth import SessionManager, OAuthHandler, OAuthConfig
from auth.database import get_session, session_scope
from auth.repository import UserRepository, SubmissionRepository

logger = get_logger(__name__)


def _to_json_safe(value: Any) -> Any:
    """Convert nested objects to JSON-safe primitives for DB storage."""
    if isinstance(value, dict):
        safe_dict: Dict[str, Any] = {}
        for k, v in value.items():
            safe_dict[str(k)] = _to_json_safe(v)
        return safe_dict

    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]

    # numpy scalars/arrays
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return [_to_json_safe(v) for v in value.tolist()]
        if isinstance(value, np.generic):
            return _to_json_safe(value.item())
    except Exception:
        pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, (str, int, bool)) or value is None:
        return value

    # Fallback for any custom object
    return str(value)


def main():
    """Main application entry point."""
    
    st.set_page_config(
        page_title="Niklaus - Detecção de Plágio",
        page_icon=":mag:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    _init_session_state()
    session_manager = SessionManager()
    oauth_config = OAuthConfig()
    
    # Clear OAuth query parameters if user is already authenticated or if there's no code
    if session_manager.is_authenticated():
        try:
            # If already logged in and there are OAuth params, clear them
            if 'code' in st.query_params or 'state' in st.query_params:
                st.query_params.clear()
        except Exception as e:
            logger.debug(f"Failed to clear query params: {e}")
    
    if not session_manager.is_authenticated():
        _render_auth_page(session_manager, oauth_config)
        return
    
    user = session_manager.get_current_user()
    
    if not user:
        session_manager.logout()
        st.rerun()
        return
    
    db = get_session()
    user_repo = UserRepository(db)
    
    try:
        current_user = user_repo.find_by_id(user['id'])
        
        if not current_user or not bool(current_user.is_active):
            session_manager.logout()
            st.error("Usuário inativo ou não encontrado")
            st.rerun()
            return
        
        _render_authenticated_app(session_manager, current_user)
        
    finally:
        db.close()


def _render_auth_page(session_manager: SessionManager, oauth_config: OAuthConfig):
    """Render login page for unauthenticated users."""
    
    st.title("🔐 Niklaus - Detecção de Plágio")
    
    st.markdown("""
    ### Bem-vindo ao Niklaus
    
    Sistema de detecção de plágio avançado com análise de IA.
    
    Faça login para continuar:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if oauth_config.google_client_id:
            if st.button("🔗 Login com Google", use_container_width=True):
                _start_oauth_login('google', "Google")
    
    with col2:
        if oauth_config.github_client_id:
            if st.button("🐙 Login com GitHub", use_container_width=True):
                _start_oauth_login('github', "GitHub")
    
    with col3:
        if oauth_config.microsoft_client_id:
            if st.button("🪟 Login com Microsoft", use_container_width=True):
                _start_oauth_login('microsoft', "Microsoft")
    
    _handle_oauth_callback(session_manager)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        🔒 Seus dados estão seguros e são privados
    </div>
    """, unsafe_allow_html=True)


def _handle_oauth_callback(session_manager: SessionManager):
    """Handle OAuth callback from providers."""
    params = st.query_params
    
    # Don't process OAuth callback if already authenticated
    if session_manager.is_authenticated():
        try:
            st.query_params.clear()
        except Exception as e:
            logger.debug(f"Failed to clear query params: {e}")
        return
    
    # Handle OAuth error response
    if 'error' in params:
        error = params.get('error', [None])[0] if isinstance(params.get('error'), list) else params.get('error')
        error_desc = params.get('error_description', ['Erro desconhecido'])[0]
        st.error(f"❌ Erro de autenticação: {error_desc}")
        st.markdown("[Voltar para login](/)")
        logger.error(f"OAuth error: {error} - {error_desc}")
        # Clear params to avoid infinite error loop
        _clear_oauth_session_state()
        st.query_params.clear()
        return
    
    # Handle successful OAuth callback
    if 'code' in params and 'state' in params:
        code_list = params.get('code', [])
        state_list = params.get('state', [])
        
        code = code_list[0] if isinstance(code_list, list) and code_list else code_list
        state = state_list[0] if isinstance(state_list, list) and state_list else state_list
        
        # Provider and state must be present in session from login initiation
        provider = st.session_state.get('oauth_provider')
        expected_state = st.session_state.get('oauth_state')
        
        if provider and code and state and expected_state:
            try:
                st.info("⏳ Processando login... Aguarde.")

                if not OAuthHandler.validate_state(str(state), str(expected_state)):
                    logger.warning("OAuth callback rejected due to state mismatch")
                    st.error("❌ Sessão de login inválida ou expirada. Tente novamente.")
                    _clear_oauth_session_state()
                    st.query_params.clear()
                    return
                
                handler = OAuthHandler(provider)
                user_obj = handler.handle_callback(str(code), str(state), expected_state=str(expected_state))
                
                if user_obj:
                    # Convert SQLAlchemy object to dict for session
                    user_dict = {
                        'id': user_obj.id,
                        'email': user_obj.email,
                        'name': user_obj.name,
                        'role': user_obj.role,
                        'is_admin': user_obj.role == 'admin'
                    }
                    
                    session_manager.login(user_dict)
                    st.success(f"✅ Bem-vindo, {user_obj.name}!")
                    st.balloons()
                    logger.info(f"User {user_obj.email} logged in via {provider}")
                    
                    # Clean up session
                    _clear_oauth_session_state()
                    
                    # Clear query params
                    st.query_params.clear()
                    
                    # Show success message briefly before redirect
                    st.info("Redirecionando...")
                    
                    # Rerun to show authenticated app
                    st.rerun()
                else:
                    st.error("❌ Falha ao autenticar usuário")
                    st.markdown("[Tentar novamente](/)")
                    logger.error(f"Failed to create user from OAuth callback for {provider}")
                    # Clear invalid OAuth params
                    _clear_oauth_session_state()
                    st.query_params.clear()
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"OAuth callback exception: {error_msg}", exc_info=True)
                
                # Clear OAuth params on error
                _clear_oauth_session_state()
                st.query_params.clear()
                
                # User-friendly error messages
                if 'invalid_grant' in error_msg or 'Bad Request' in error_msg:
                    st.error("❌ Código de autorização expirado ou já usado")
                    st.warning("💡 Por favor, faça login novamente")
                elif 'access_denied' in error_msg:
                    st.error("❌ Acesso negado pelo provedor")
                else:
                    st.error(f"❌ Erro durante autenticação: {error_msg[:100]}")
                
                st.markdown("[Voltar para login](/)")
        else:
            st.error("❌ Parâmetros de autenticação inválidos")
            st.error(f"Provider: {provider or 'não encontrado'}, Code: {'✓' if code else '✗'}, State: {'✓' if state else '✗'}")
            st.markdown("[Voltar para login](/)")
            # Clear invalid OAuth params
            _clear_oauth_session_state()
            st.query_params.clear()


def _start_oauth_login(provider: str, provider_label: str) -> None:
    """Start OAuth login flow with explicit provider and state."""
    handler = OAuthHandler(provider)
    state = secrets.token_urlsafe(32)

    st.session_state['oauth_provider'] = provider
    st.session_state['oauth_state'] = state
    st.session_state['login_initiated'] = True

    auth_url = handler.get_authorization_url(state=state)
    st.markdown(f"""
    <meta http-equiv="refresh" content="0; url={auth_url}" />
    """, unsafe_allow_html=True)
    st.info(f"Redirecionando para {provider_label}...")


def _clear_oauth_session_state() -> None:
    """Clear transient OAuth keys from session state."""
    for key in ['oauth_state', 'oauth_provider', 'login_initiated']:
        if key in st.session_state:
            del st.session_state[key]


def _render_authenticated_app(session_manager: SessionManager, current_user):
    """Render the main app for authenticated users."""
    
    # Breadcrumb navigation
    st.markdown("""
    <style>
    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        font-size: 14px;
        color: #666;
    }
    .breadcrumb-separator {
        color: #999;
    }
    .breadcrumb-item {
        text-decoration: none;
        color: #1f77b4;
    }
    .breadcrumb-item:hover {
        text-decoration: underline;
    }
    .breadcrumb-current {
        color: #333;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Build breadcrumb based on current state
    breadcrumb_items = ["🏠 Niklaus"]
    
    if st.session_state.get('last_analysis'):
        breadcrumb_items.append("📊 Resultados")
    
    # Render breadcrumb
    breadcrumb_html = '<div class="breadcrumb">'
    for i, item in enumerate(breadcrumb_items):
        if i > 0:
            breadcrumb_html += '<span class="breadcrumb-separator">›</span>'
        
        if i == len(breadcrumb_items) - 1:
            breadcrumb_html += f'<span class="breadcrumb-current">{item}</span>'
        else:
            breadcrumb_html += f'<span class="breadcrumb-item">{item}</span>'
    
    breadcrumb_html += '</div>'
    st.markdown(breadcrumb_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.sidebar:
        st.markdown(f"### 👤 {current_user.name}")
        st.markdown(f"*{current_user.email}*")
        if current_user.role == 'admin':
            st.markdown("🛡️ **Administrador**")
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear OAuth parameters before logout
            try:
                st.query_params.clear()
            except Exception as e:
                logger.debug(f"Failed to clear query params before logout: {e}")
            
            # Clear session
            session_manager.logout()
            st.rerun()
        
        st.divider()
    
    settings = render_sidebar()
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        ":file_folder: Upload & Análise",
        ":bar_chart: Resultados",
        ":chart_with_upwards_trend: Estatísticas",
        ":microscope: Análise Avançada",
        ":spider_web: Grafo de Similaridade",
        "📋 Histórico"
    ])
    
    # Initialize cancel flag
    if 'cancel_analysis' not in st.session_state:
        st.session_state['cancel_analysis'] = False
    
    with tab1:
        files, contents, extract_path, should_analyze = render_upload_tab(settings)
        
        if should_analyze and files and contents:
            # Cancel button
            cancel_placeholder = st.empty()
            with cancel_placeholder.container():
                st.warning("⏳ Análise em andamento...")
                if st.button("❌ Cancelar Análise", type="secondary", use_container_width=True):
                    st.session_state['cancel_analysis'] = True
                    st.warning("⚠️ Cancelando análise...")
            
            results = _run_analysis(files, contents, settings, current_user.id)
            
            # Clear cancel button after analysis
            cancel_placeholder.empty()
            
            st.session_state['last_analysis'] = results
            st.session_state['settings'] = settings
            
            if extract_path:
                shutil.rmtree(extract_path, ignore_errors=True)
            
            st.toast("✅ Análise concluída com sucesso!")
            st.rerun()
    
    # Check for loaded analysis (from history or new analysis)
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
        
        with tab6:
            render_history_tab(current_user.id)
    
    else:
        # No analysis data available
        with tab2:
            st.info("📊 Nenhum resultado disponível. Execute uma análise ou carregue uma do histórico.")
        
        with tab3:
            st.info("📈 Nenhum estatística disponível. Execute uma análise ou carregue uma do histórico.")
        
        with tab4:
            st.info("🔬 Nenhuma análise avançada disponível. Execute uma análise ou carregue uma do histórico.")
        
        with tab5:
            st.info("🕸️ Nenhum grafo disponível. Execute uma análise ou carregue uma do histórico.")
        
        with tab6:
            render_history_tab(current_user.id)


def _init_session_state():
    """Initialize session state variables."""
    defaults = {
        'cancel': False,
        'last_analysis': None,
        'advanced_analysis': None,
        'cluster_data': None,
        'settings': {},
        'oauth_provider': None,
        'user_id': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_analysis(files: List[str], contents: List[str], settings: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """
    Run analysis using AnalysisPipeline and save to database.
    
    Args:
        files: List of filenames
        contents: List of file contents
        settings: User settings
        user_id: Current user ID
    
    Returns:
        Analysis results
    """
    logger.info(f"User {user_id} starting analysis of {len(files)} files")
    
    pipeline = AnalysisPipeline(
        language=settings['language'],
        api_key=settings['api_key'] if settings['enable_ai'] else None,
        model=settings['model'],
        max_workers=settings['max_workers'],
        use_cache=settings['use_cache']
    )
    
    progress_bar = st.progress(0, text="Iniciando análise...")
    
    def progress_callback(stage: str, current: int, total: int):
        if total > 0:
            pct = current / total
            progress_bar.progress(pct, text=f"{stage}: {current}/{total}")
    
    try:
        results = pipeline.run_full_analysis(
            files=files,
            contents=contents,
            threshold=settings['threshold'],
            enable_ai=settings['enable_ai'],
            progress_callback=progress_callback
        )
        
        progress_bar.progress(100, text="Análise concluída!")
        
        _save_submission(results, user_id, len(files), settings)
        
        logger.info(f"Analysis completed in {results['analysis_time']:.2f}s")
        
        return results
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        st.error(f"Erro na análise: {str(e)}")
        st.stop()


def _save_submission(results: Dict[str, Any], user_id: int, total_files: int, settings: Dict[str, Any]):
    """Save submission to database."""
    try:
        with session_scope() as db:
            submission_repo = SubmissionRepository(db)

            files_list = results.get('files', [])
            filename = ', '.join(files_list[:3]) if files_list else 'analysis'
            if len(files_list) > 3:
                filename += f' and {len(files_list) - 3} more'

            threshold = float(settings.get('threshold', results.get('threshold', 0.7)) or 0.7)
            suspicious_pairs = [
                pair for pair in results.get('pairwise_results', [])
                if float(pair.get('similarity', 0) or 0) >= threshold
            ]

            analysis_payload = _to_json_safe({
                # Schema v2: store enough to render Results/Stats/Advanced/Graph
                'schema_version': 2,
                'files': results.get('files', files_list),
                'language': results.get('language', settings.get('language', 'unknown')),
                'threshold': threshold,
                'suspicious_pairs': results.get('suspicious_pairs', []),
                'pairwise_results': results.get('pairwise_results', []),
                'similarity_matrix': results.get('similarity_matrix'),
                'cluster_data': results.get('cluster_data'),
                'metrics': results.get('metrics'),
                'ast_similarities': results.get('ast_similarities'),
                'patterns': results.get('patterns'),
                'ai_analyses': results.get('ai_analyses'),
                'average_similarity': results.get('average_similarity', 0.0),
                'max_similarity': results.get('max_similarity', 0.0),
                'analysis_time': results.get('analysis_time', 0.0),
            })

            submission = submission_repo.create(
                user_id=user_id,
                filename=filename[:255],
                language=settings.get('language', 'unknown'),
                threshold=threshold,
                max_workers=settings.get('max_workers', 4),
                enable_ai=settings.get('enable_ai', False),
                use_cache=settings.get('use_cache', True),
                files_count=total_files,
                suspicious_pairs_count=len(suspicious_pairs),
                average_similarity=results.get('average_similarity', 0.0),
                max_similarity=results.get('max_similarity', 0.0),
                analysis_time_seconds=results.get('analysis_time', 0.0),
                status='completed',
                analysis_data=analysis_payload
            )

            logger.info(f"Submission {submission.id} saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save submission: {e}")


if __name__ == "__main__":
    main()
