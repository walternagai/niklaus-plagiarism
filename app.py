"""
Main modular application for Niklaus plagiarism detector.
This version uses the modular UI architecture with authentication.
"""

import streamlit as st
from typing import Dict, Any, List
import shutil

from ui.sidebar import render_sidebar
from ui.tabs.upload import render_upload_tab
from ui.tabs.results import render_results_tab
from ui.tabs.statistics import render_statistics_tab
from ui.tabs.advanced import render_advanced_tab
from ui.tabs.graph import render_graph_tab

from core.pipeline import AnalysisPipeline
from utils.logger import get_logger
from auth import SessionManager, OAuthHandler, OAuthConfig
from auth.database import get_session
from auth.repository import UserRepository, SubmissionRepository

logger = get_logger(__name__)


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
        except:
            pass
    
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
                handler = OAuthHandler('google')
                auth_url = handler.get_authorization_url()
                st.session_state['oauth_provider'] = 'google'
                st.session_state['oauth_state'] = auth_url.split('state=')[1].split('&')[0] if 'state=' in auth_url else ''
                st.markdown(f"""
                <meta http-equiv="refresh" content="0; url={auth_url}" />
                """, unsafe_allow_html=True)
                st.info("Redirecionando para o Google...")
    
    with col2:
        if oauth_config.github_client_id:
            if st.button("🐙 Login com GitHub", use_container_width=True):
                handler = OAuthHandler('github')
                auth_url = handler.get_authorization_url()
                st.session_state['oauth_provider'] = 'github'
                st.session_state['oauth_state'] = auth_url.split('state=')[1].split('&')[0] if 'state=' in auth_url else ''
                st.markdown(f"""
                <meta http-equiv="refresh" content="0; url={auth_url}" />
                """, unsafe_allow_html=True)
                st.info("Redirecionando para o GitHub...")
    
    with col3:
        if oauth_config.microsoft_client_id:
            if st.button("🪟 Login com Microsoft", use_container_width=True):
                handler = OAuthHandler('microsoft')
                auth_url = handler.get_authorization_url()
                st.session_state['oauth_provider'] = 'microsoft'
                st.session_state['oauth_state'] = auth_url.split('state=')[1].split('&')[0] if 'state=' in auth_url else ''
                st.markdown(f"""
                <meta http-equiv="refresh" content="0; url={auth_url}" />
                """, unsafe_allow_html=True)
                st.info("Redirecionando para a Microsoft...")
    
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
        except:
            pass
        return
    
    # Handle OAuth error response
    if 'error' in params:
        error = params.get('error', [None])[0] if isinstance(params.get('error'), list) else params.get('error')
        error_desc = params.get('error_description', ['Erro desconhecido'])[0]
        st.error(f"❌ Erro de autenticação: {error_desc}")
        st.markdown("[Voltar para login](/)")
        logger.error(f"OAuth error: {error} - {error_desc}")
        # Clear params to avoid infinite error loop
        st.query_params.clear()
        return
    
    # Handle successful OAuth callback
    if 'code' in params and 'state' in params:
        code_list = params.get('code', [])
        state_list = params.get('state', [])
        
        code = code_list[0] if isinstance(code_list, list) and code_list else code_list
        state = state_list[0] if isinstance(state_list, list) and state_list else state_list
        
        # Try to get provider from session, or infer from state parameter
        provider = st.session_state.get('oauth_provider')
        
        # If provider not in session, check if we can recover it
        if not provider:
            # Try to determine provider from available configuration
            oauth_config = OAuthConfig()
            if oauth_config.google_client_id and oauth_config.google_client_secret:
                provider = 'google'
                st.session_state['oauth_provider'] = 'google'
                logger.info("Recovered provider 'google' from config")
            elif oauth_config.github_client_id and oauth_config.github_client_secret:
                provider = 'github'
                st.session_state['oauth_provider'] = 'github'
                logger.info("Recovered provider 'github' from config")
            elif oauth_config.microsoft_client_id and oauth_config.microsoft_client_secret:
                provider = 'microsoft'
                st.session_state['oauth_provider'] = 'microsoft'
                logger.info("Recovered provider 'microsoft' from config")
        
        if provider and code and state:
            try:
                st.info("⏳ Processando login... Aguarde.")
                
                handler = OAuthHandler(provider)
                user_obj = handler.handle_callback(str(code), str(state))
                
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
                    for key in ['oauth_state', 'oauth_provider', 'login_initiated']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
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
                    st.query_params.clear()
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"OAuth callback exception: {error_msg}", exc_info=True)
                
                # Clear OAuth params on error
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
            st.query_params.clear()


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
            except:
                pass
            
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
            _render_history_tab(current_user.id)
    
    else:
        if not should_analyze:
            for i, tab in enumerate([tab2, tab3, tab4, tab5], start=2):
                with tab:
                    st.info("Nenhum resultado disponível. Execute uma análise primeiro.")
            
            with tab6:
                _render_history_tab(current_user.id)


def _render_history_tab(user_id: int):
    """Render submission history tab with pagination and filters."""
    st.subheader("📋 Histórico de Submissões")
    
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    # Initialize filter state
    if 'history_filter_date_start' not in st.session_state:
        st.session_state['history_filter_date_start'] = None
    if 'history_filter_date_end' not in st.session_state:
        st.session_state['history_filter_date_end'] = None
    if 'history_filter_status' not in st.session_state:
        st.session_state['history_filter_status'] = 'Todos'
    if 'history_filter_min_similarity' not in st.session_state:
        st.session_state['history_filter_min_similarity'] = 0.0
    if 'history_filter_max_similarity' not in st.session_state:
        st.session_state['history_filter_max_similarity'] = 1.0
    if 'history_page' not in st.session_state:
        st.session_state['history_page'] = 1
    
    # Filters section
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📅 Período**")
            filter_date_start = st.date_input(
                "Data inicial",
                value=None,
                key="history_filter_date_start_input",
                help="Filtrar submissões a partir desta data"
            )
            filter_date_end = st.date_input(
                "Data final",
                value=None,
                key="history_filter_date_end_input",
                help="Filtrar submissões até esta data"
            )
        
        with col2:
            st.markdown("**📊 Status**")
            filter_status = st.selectbox(
                "Filtrar por status",
                options=["Todos", "Concluída", "Processando", "Erro"],
                key="history_filter_status_input",
                help="Filtrar por status da submissão"
            )
            
            st.markdown("**📈 Similaridade**")
            min_sim = st.slider(
                "Similaridade mínima (%)",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
                key="history_filter_min_sim_input",
                help="Filtrar por similaridade média mínima"
            ) / 100.0
            
            max_sim = st.slider(
                "Similaridade máxima (%)",
                min_value=0,
                max_value=100,
                value=100,
                step=5,
                key="history_filter_max_sim_input",
                help="Filtrar por similaridade média máxima"
            ) / 100.0
        
        with col3:
            st.markdown("**🔧 Ações**")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("✅ Aplicar Filtros", use_container_width=True, type="primary"):
                    st.session_state['history_filter_date_start'] = filter_date_start
                    st.session_state['history_filter_date_end'] = filter_date_end
                    st.session_state['history_filter_status'] = filter_status
                    st.session_state['history_filter_min_similarity'] = min_sim
                    st.session_state['history_filter_max_similarity'] = max_sim
                    st.session_state['history_page'] = 1  # Reset to first page
                    st.toast("✅ Filtros aplicados!")
                    st.rerun()
            
            with col_btn2:
                if st.button("🔄 Limpar Filtros", use_container_width=True):
                    st.session_state['history_filter_date_start'] = None
                    st.session_state['history_filter_date_end'] = None
                    st.session_state['history_filter_status'] = 'Todos'
                    st.session_state['history_filter_min_similarity'] = 0.0
                    st.session_state['history_filter_max_similarity'] = 1.0
                    st.session_state['history_page'] = 1
                    st.toast("🔄 Filtros removidos!")
                    st.rerun()
    
    try:
        # Get all submissions (we'll filter in Python for now)
        all_submissions = submission_repo.find_by_user(user_id, limit=1000, offset=0)
        
        # Apply filters
        filtered_submissions = []
        
        for sub in all_submissions:
            # Date filter
            if st.session_state['history_filter_date_start']:
                from datetime import datetime as dt
                start_date = dt.combine(st.session_state['history_filter_date_start'], dt.min.time())
                if sub.created_at < start_date:
                    continue
            
            if st.session_state['history_filter_date_end']:
                from datetime import datetime as dt
                end_date = dt.combine(st.session_state['history_filter_date_end'], dt.max.time())
                if sub.created_at > end_date:
                    continue
            
            # Status filter
            status_filter = st.session_state['history_filter_status']
            sub_status = getattr(sub, 'status', 'unknown')
            if status_filter != "Todos":
                if status_filter == "Concluída" and sub_status != 'completed':
                    continue
                elif status_filter == "Processando" and sub_status != 'processing':
                    continue
                elif status_filter == "Erro" and sub_status != 'error':
                    continue
            
            # Similarity filter
            avg_sim = getattr(sub, 'average_similarity', 0.0) or 0.0
            min_sim_filter = st.session_state['history_filter_min_similarity']
            max_sim_filter = st.session_state['history_filter_max_similarity']
            
            if avg_sim < min_sim_filter or avg_sim > max_sim_filter:
                continue
            
            filtered_submissions.append(sub)
        
        total_submissions = len(filtered_submissions)
        
        if not filtered_submissions:
            st.info("Nenhuma submissão encontrada com os filtros aplicados.")
            st.markdown("Ajuste os filtros ou faça uma nova análise.")
            return
        
        # Pagination
        page_size = 50
        current_page = st.session_state['history_page']
        total_pages = (total_submissions + page_size - 1) // page_size
        
        # Calculate page boundaries
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        page_submissions = filtered_submissions[start_idx:end_idx]
        
        # Show count
        filters_applied = (
            st.session_state['history_filter_date_start'] is not None or
            st.session_state['history_filter_status'] != 'Todos' or
            st.session_state['history_filter_min_similarity'] > 0.0 or
            st.session_state['history_filter_max_similarity'] < 1.0
        )
        
        if filters_applied:
            st.markdown(f"**{total_submissions} submissões encontradas (filtradas)**")
        else:
            st.markdown(f"**{total_submissions} submissões encontradas**")
        
        # Pagination controls
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("⬅️ Anterior", disabled=(current_page == 1), use_container_width=True):
                    st.session_state['history_page'] = current_page - 1
                    st.rerun()
            
            with col2:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'>Página {current_page} de {total_pages}</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Próxima ➡️", disabled=(current_page == total_pages), use_container_width=True):
                    st.session_state['history_page'] = current_page + 1
                    st.rerun()
        
        st.markdown("---")
        
        # Display submissions
        for sub in page_submissions:
            files_count = getattr(sub, 'files_count', 0) or 0
            suspicious_count = getattr(sub, 'suspicious_pairs_count', 0) or 0
            avg_sim = getattr(sub, 'average_similarity', 0.0) or 0.0
            max_sim = getattr(sub, 'max_similarity', 0.0) or 0.0
            time_seconds = getattr(sub, 'analysis_time_seconds', 0.0) or 0.0
            threshold = getattr(sub, 'threshold', 0.7) or 0.7
            filename = getattr(sub, 'filename', 'N/A')
            language = getattr(sub, 'language', 'N/A')
            status = getattr(sub, 'status', 'unknown')
            sub_id = getattr(sub, 'id', 0)
            
            # Status indicators
            if suspicious_count > 0:
                status_icon = "🔴"
            elif avg_sim > 0.4:
                status_icon = "🟡"
            else:
                status_icon = "🟢"
            
            # Header with date and status
            col_header, col_status = st.columns([3, 1])
            
            with col_header:
                st.markdown(f"### {status_icon} {sub.created_at.strftime('%d/%m/%Y %H:%M')}")
            
            with col_status:
                if status == 'completed':
                    st.success("✓ Concluída")
                else:
                    st.warning("⏳ Processando")
            
            # Metrics in columns
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "📊 Arquivos",
                    value=files_count,
                    delta=None
                )
            
            with col2:
                st.metric(
                    "⚠️ Suspeitos",
                    value=suspicious_count,
                    delta_color="inverse"
                )
            
            with col3:
                st.metric(
                    "📈 Similaridade",
                    value=f"{avg_sim:.1%}" if avg_sim else "N/A",
                    delta=None
                )
            
            with col4:
                st.metric(
                    "📉 Máxima",
                    value=f"{max_sim:.1%}" if max_sim else "N/A",
                    delta=None
                )
            
            with col5:
                st.metric(
                    "⏱️ Tempo",
                    value=f"{time_seconds:.2f}s" if time_seconds else "N/A",
                    delta=None
                )
            
            # Warning about high similarity
            if suspicious_count > 0:
                avg_percent = avg_sim * 100
                threshold_int = int(threshold * 100) if threshold else 70
                st.warning(
                    f"⚠️ **Atenção:** {suspicious_count} par(es) com similaridade ≥ "
                    f"{threshold_int}% detectado(s). Similaridade média: {avg_percent:.1f}%"
                )
            elif avg_sim > 0.4:
                st.info(f"ℹ️ Similaridade geral baixa ({avg_sim:.1%}), mas recomendamos revisão.")
            
            # Details
            with st.expander("📄 Detalhes", expanded=False):
                st.markdown(f"**ID:** {sub_id}")
                st.markdown(f"**Linguagem:** {language}")
                st.markdown(f"**Threshold:** {int(threshold * 100)}%")
                st.markdown(f"**Arquivos analisados:** {filename}")
                
                analysis_data = getattr(sub, 'analysis_data', None)
                if analysis_data:
                    st.markdown("**Dados da análise:**")
                    st.json(analysis_data)
            
            st.markdown("---")
                
    finally:
        db.close()


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
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    try:
        files_list = results.get('files', [])
        filename = ', '.join(files_list[:3]) if files_list else 'analysis'
        if len(files_list) > 3:
            filename += f' and {len(files_list) - 3} more'
        
        suspicious_pairs = [
            pair for pair in results.get('pairwise_results', [])
            if pair.get('similarity', 0) > settings.get('threshold', 0.7)
        ]
        
        submission = submission_repo.create(
            user_id=user_id,
            filename=filename[:255],
            language=settings.get('language', 'unknown'),
            threshold=settings.get('threshold', 0.7),
            max_workers=settings.get('max_workers', 4),
            enable_ai=settings.get('enable_ai', False),
            use_cache=settings.get('use_cache', True),
            files_count=total_files,
            suspicious_pairs_count=len(suspicious_pairs),
            average_similarity=results.get('average_similarity', 0.0),
            max_similarity=results.get('max_similarity', 0.0),
            analysis_time_seconds=results.get('analysis_time', 0.0),
            status='completed',
            analysis_data={
                'pairwise_results': results.get('pairwise_results', []),
                'files': files_list,
                'avg_similarity': results.get('average_similarity', 0.0),
                'max_similarity': results.get('max_similarity', 0.0),
            }
        )
        
        logger.info(f"Submission {submission.id} saved for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to save submission: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()