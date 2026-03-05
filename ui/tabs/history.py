"""
History tab for managing and viewing submission history.
"""

import streamlit as st
from typing import List, Dict, Any
from datetime import datetime as dt

from auth.database import get_session
from auth.repository import SubmissionRepository
from utils.logger import get_logger

logger = get_logger(__name__)


def render_history_tab(user_id: int):
    """
    Render submission history tab with pagination, filters, and actions.
    
    Args:
        user_id: Current user ID
    """
    st.subheader("📋 Histórico de Submissões")
    
    # Initialize loaded submission
    if 'loaded_submission_id' not in st.session_state:
        st.session_state['loaded_submission_id'] = None
    
    # Show loaded submission status
    if st.session_state.get('loaded_submission_id') and st.session_state.get('last_analysis'):
        st.success(f"📂 Submissão #{st.session_state['loaded_submission_id']} carregada - Veja as abas Resultados, Estatísticas, Análise Avançada e Grafo")
    
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    try:
        _render_actions_section(user_id, submission_repo)
        _render_filters_section()
        _render_submissions_list(user_id, submission_repo)
    finally:
        db.close()


def _render_actions_section(user_id: int, submission_repo: SubmissionRepository):
    """Render actions section with clear history buttons."""
    st.markdown("#### 🔧 Ações")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Limpar Todas as Submissões", use_container_width=True, type="secondary"):
            st.session_state['show_clear_all_dialog'] = True
    
    with col2:
        if st.button("📊 Ver Estatísticas do Histórico", use_container_width=True):
            st.session_state['show_history_stats'] = True
    
    with col3:
        if st.session_state.get('loaded_submission_id'):
            if st.button("✖️ Fechar Submissão Carregada", use_container_width=True):
                # Clear all analysis-related session state
                if 'last_analysis' in st.session_state:
                    del st.session_state['last_analysis']
                if 'loaded_submission_id' in st.session_state:
                    del st.session_state['loaded_submission_id']
                if 'advanced_analysis' in st.session_state:
                    del st.session_state['advanced_analysis']
                if 'cluster_data' in st.session_state:
                    del st.session_state['cluster_data']
                
                st.toast("✓ Submissão fechada")
                st.rerun()
    
    # Show clear all dialog
    if st.session_state.get('show_clear_all_dialog', False):
        _show_clear_all_confirmation(user_id, submission_repo)
    
    # Show history stats
    if st.session_state.get('show_history_stats', False):
        _show_history_stats(user_id, submission_repo)
    
    st.markdown("---")


def _show_clear_all_confirmation(user_id: int, submission_repo: SubmissionRepository):
    """Show confirmation dialog for clearing all submissions."""
    st.warning("⚠️ **Atenção:** Esta ação irá excluir TODAS as suas submissões.")
    st.warning("Esta ação não pode ser desfeita!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Sim, excluir todas", key="btn_confirm_clear_all", type="primary"):
            _clear_all_submissions(user_id, submission_repo)
    
    with col2:
        if st.button("❌ Cancelar", key="btn_cancel_clear_all"):
            st.session_state['show_clear_all_dialog'] = False


def _clear_all_submissions(user_id: int, submission_repo: SubmissionRepository):
    """Clear all submissions for a user."""
    try:
        # Ensure dialogs are closed even if we rerun
        st.session_state['show_clear_all_dialog'] = False
        st.session_state['show_history_stats'] = False

        # Get all submissions
        submissions = submission_repo.find_by_user(user_id, limit=10000, offset=0)
        count = len(submissions)
        
        # Delete each submission
        for sub in submissions:
            submission_repo.delete(sub.id)
        
        st.success(f"✓ {count} submissões excluídas com sucesso!")
        st.toast(f"✓ {count} submissões removidas")
        
        # Clear loaded submission
        st.session_state['loaded_submission_id'] = None
        st.session_state['last_analysis'] = None

        # Clear any per-submission delete confirmation flags
        keys_to_clear = [k for k in st.session_state.keys() if str(k).startswith('show_delete_confirm_')]
        for k in keys_to_clear:
            try:
                del st.session_state[k]
            except Exception:
                pass
        
        # Clear caches
        from utils.db_cache import get_submission_cache
        cache = get_submission_cache()
        cache.invalidate_user(user_id)
        
        logger.info(f"User {user_id} cleared {count} submissions")
        st.rerun()
        
    except Exception as e:
        logger.error(f"Error clearing submissions for user {user_id}: {e}")
        st.error(f"❌ Erro ao excluir submissões: {str(e)}")


def _show_history_stats(user_id: int, submission_repo: SubmissionRepository):
    """Show statistics about submission history."""
    try:
        submissions = submission_repo.find_by_user(user_id, limit=10000, offset=0)
        
        if not submissions:
            st.info("Nenhuma submissão encontrada")
            if st.button("Fechar", key="close_stats_empty"):
                st.session_state['show_history_stats'] = False
                st.rerun()
            return
        
        total = len(submissions)
        completed = len([s for s in submissions if getattr(s, 'status', '') == 'completed'])
        processing = len([s for s in submissions if getattr(s, 'status', '') == 'processing'])
        errors = len([s for s in submissions if getattr(s, 'status', '') == 'error'])
        
        total_files = sum(getattr(s, 'files_count', 0) or 0 for s in submissions)
        total_pairs = sum(getattr(s, 'suspicious_pairs_count', 0) or 0 for s in submissions)
        
        avg_sims = [getattr(s, 'average_similarity', 0) or 0 for s in submissions if getattr(s, 'average_similarity', None)]
        overall_avg_sim = sum(avg_sims) / len(avg_sims) if avg_sims else 0
        
        max_sims = [getattr(s, 'max_similarity', 0) or 0 for s in submissions if getattr(s, 'max_similarity', None)]
        overall_max_sim = max(max_sims) if max_sims else 0
        
        st.markdown("#### 📊 Estatísticas do Histórico")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Submissões", total)
            st.metric("Concluídas", completed)
        
        with col2:
            st.metric("Processando", processing)
            st.metric("Com Erro", errors)
        
        with col3:
            st.metric("Total de Arquivos", total_files)
            st.metric("Pares Suspeitos", total_pairs)
        
        with col4:
            st.metric("Similaridade Média Geral", f"{overall_avg_sim:.1%}")
            st.metric("Similaridade Máxima Geral", f"{overall_max_sim:.1%}")
        
        st.markdown("---")
        
        if st.button("Fechar Estatísticas", key="close_stats"):
            st.session_state['show_history_stats'] = False
            st.rerun()
        
    except Exception as e:
        logger.error(f"Error showing history stats: {e}")
        st.error(f"Erro ao carregar estatísticas: {str(e)}")
        if st.button("Fechar", key="close_stats_error"):
            st.session_state['show_history_stats'] = False
            st.rerun()


def _render_filters_section():
    """Render filters section."""
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


def _render_submissions_list(user_id: int, submission_repo: SubmissionRepository):
    """Render list of submissions with actions."""
    try:
        # Get all submissions (we'll filter in Python for now)
        all_submissions = submission_repo.find_by_user(user_id, limit=1000, offset=0)
        
        # Apply filters
        filtered_submissions = []
        
        for sub in all_submissions:
            # Date filter
            if st.session_state['history_filter_date_start']:
                start_date = dt.combine(st.session_state['history_filter_date_start'], dt.min.time())
                if sub.created_at < start_date:
                    continue
            
            if st.session_state['history_filter_date_end']:
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
        current_page = st.session_state['history_page']
        page_size = 50
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
            _render_submission_card(sub, user_id, submission_repo)
                
    except Exception as e:
        logger.error(f"Error rendering submissions list: {e}")
        st.error(f"Erro ao carregar histórico: {str(e)}")


def _render_submission_card(submission, user_id: int, submission_repo: SubmissionRepository):
    """Render a single submission card with actions."""
    files_count = getattr(submission, 'files_count', 0) or 0
    suspicious_count = getattr(submission, 'suspicious_pairs_count', 0) or 0
    avg_sim = getattr(submission, 'average_similarity', 0.0) or 0.0
    max_sim = getattr(submission, 'max_similarity', 0.0) or 0.0
    time_seconds = getattr(submission, 'analysis_time_seconds', 0.0) or 0.0
    threshold = getattr(submission, 'threshold', 0.7) or 0.7
    filename = getattr(submission, 'filename', 'N/A')
    language = getattr(submission, 'language', 'N/A')
    status = getattr(submission, 'status', 'unknown')
    sub_id = getattr(submission, 'id', 0)
    
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
        st.markdown(f"### {status_icon} {submission.created_at.strftime('%d/%m/%Y %H:%M')}")
    
    with col_status:
        if status == 'completed':
            st.success("✓ Concluída")
        else:
            st.warning("⏳ Processando")
    
    # Metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Arquivos", value=files_count, delta=None)
    
    with col2:
        st.metric("⚠️ Suspeitos", value=suspicious_count, delta_color="inverse")
    
    with col3:
        st.metric("📈 Similaridade", value=f"{avg_sim:.1%}" if avg_sim else "N/A", delta=None)
    
    with col4:
        st.metric("📉 Máxima", value=f"{max_sim:.1%}" if max_sim else "N/A", delta=None)
    
    with col5:
        st.metric("⏱️ Tempo", value=f"{time_seconds:.2f}s" if time_seconds else "N/A", delta=None)
    
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
    
    # Actions
    col_actions = st.columns([1, 1, 1])
    
    with col_actions[0]:
        if st.button(f"📂 Carregar Resultados", key=f"load_{sub_id}", use_container_width=True):
            _load_submission_results(submission)
    
    with col_actions[1]:
        if st.button(f"📊 Ver Detalhes", key=f"details_{sub_id}", use_container_width=True):
            _show_submission_details(submission)
    
    with col_actions[2]:
        if st.button(f"🗑️ Excluir", key=f"delete_{sub_id}", use_container_width=True, type="secondary"):
            st.session_state[f'show_delete_confirm_{sub_id}'] = True
    
    # Delete confirmation
    if st.session_state.get(f'show_delete_confirm_{sub_id}', False):
        st.warning(f"⚠️ Confirmar exclusão da submissão {sub_id}?")
        col_confirm = st.columns(2)
        
        with col_confirm[0]:
            if st.button("✅ Sim, excluir", key=f"confirm_del_{sub_id}", type="primary"):
                _delete_submission(sub_id, user_id, submission_repo)
                st.session_state[f'show_delete_confirm_{sub_id}'] = False
                st.rerun()
        
        with col_confirm[1]:
            if st.button("❌ Cancelar", key=f"cancel_del_{sub_id}"):
                st.session_state[f'show_delete_confirm_{sub_id}'] = False
                st.rerun()
    
    # Details expander
    with st.expander("📄 Detalhes", expanded=False):
        st.markdown(f"**ID:** {sub_id}")
        st.markdown(f"**Linguagem:** {language}")
        st.markdown(f"**Threshold:** {int(threshold * 100)}%")
        st.markdown(f"**Arquivos analisados:** {filename}")
        
        analysis_data = getattr(submission, 'analysis_data', None)
        if analysis_data:
            st.markdown("**Dados da análise:**")
            st.json(analysis_data)
    
    st.markdown("---")


def _load_submission_results(submission):
    """Load submission results into session state for viewing."""
    try:
        analysis_data = getattr(submission, 'analysis_data', None)
        
        if not analysis_data:
            st.error("❌ Esta submissão não possui dados de análise.")
            return
        
        normalized = _normalize_submission_analysis(submission, analysis_data)
        if not normalized:
            st.error("❌ Não foi possível normalizar os dados desta submissão.")
            return

        # Load into session state
        st.session_state['last_analysis'] = normalized
        st.session_state['loaded_submission_id'] = getattr(submission, 'id', None)
        
        # Also load settings from submission
        prev_settings = st.session_state.get('settings', {}) or {}
        settings = {
            'threshold': float(normalized.get('threshold', getattr(submission, 'threshold', 0.7) or 0.7)),
            'language': normalized.get('language', getattr(submission, 'language', 'Python') or 'Python'),
            'max_workers': int(prev_settings.get('max_workers', 4) or 4),
            'use_cache': bool(prev_settings.get('use_cache', True)),
            'enable_ai': bool(prev_settings.get('enable_ai', True)),
            'api_key': prev_settings.get('api_key'),
            'model': prev_settings.get('model'),
        }
        st.session_state['settings'] = settings
        
        # Clear any previous advanced analysis
        if 'advanced_analysis' in st.session_state:
            del st.session_state['advanced_analysis']
        if 'cluster_data' in st.session_state:
            del st.session_state['cluster_data']
        
        st.success(f"✅ Submissão #{getattr(submission, 'id', 0)} carregada!")
        st.toast("✅ Resultados carregados! Veja as abas: Resultados, Estatísticas, Análise Avançada e Grafo.")
        
        logger.info(f"Loaded submission {getattr(submission, 'id', 0)} for viewing")
        
        # Force rerun to update all tabs
        st.rerun()
        
    except Exception as e:
        logger.error(f"Error loading submission results: {e}")
        st.error(f"❌ Erro ao carregar resultados: {str(e)}")


def _normalize_submission_analysis(submission, analysis_data):
    """Normalize stored analysis_data into the schema expected by UI tabs."""
    import json

    if analysis_data is None:
        return None

    # SQLite JSON may come as str
    if isinstance(analysis_data, str):
        try:
            analysis_data = json.loads(analysis_data)
        except Exception:
            return None

    if not isinstance(analysis_data, dict):
        return None

    # Always prefer submission columns for these
    threshold = float(getattr(submission, 'threshold', analysis_data.get('threshold', 0.7)) or 0.7)
    language = getattr(submission, 'language', analysis_data.get('language', 'Python')) or 'Python'
    analysis_time = float(
        analysis_data.get('analysis_time', getattr(submission, 'analysis_time_seconds', 0.0) or 0.0)
        or 0.0
    )

    normalized = dict(analysis_data)
    normalized.setdefault('schema_version', 1)
    normalized['threshold'] = threshold
    normalized['language'] = language
    normalized['analysis_time'] = analysis_time

    # Legacy keys mapping
    if 'average_similarity' not in normalized:
        if 'avg_similarity' in normalized:
            normalized['average_similarity'] = normalized.get('avg_similarity')
        else:
            normalized['average_similarity'] = getattr(submission, 'average_similarity', 0.0) or 0.0

    if 'max_similarity' not in normalized:
        normalized['max_similarity'] = getattr(submission, 'max_similarity', 0.0) or 0.0

    # Ensure files list
    files = normalized.get('files')
    if not files and normalized.get('pairwise_results'):
        seen = set()
        ordered = []
        for r in normalized.get('pairwise_results', []):
            f1 = r.get('file1')
            f2 = r.get('file2')
            for f in (f1, f2):
                if f and f not in seen:
                    seen.add(f)
                    ordered.append(f)
        files = ordered
        normalized['files'] = files

    # Build suspicious_pairs if missing
    if not normalized.get('suspicious_pairs'):
        pr = normalized.get('pairwise_results') or []
        suspicious_pairs = []
        for r in pr:
            try:
                sim = float(r.get('similarity', 0) or 0)
            except Exception:
                sim = 0.0
            if bool(r.get('is_suspicious')) or sim >= threshold:
                f1 = r.get('file1')
                f2 = r.get('file2')
                if f1 and f2:
                    suspicious_pairs.append((f1, f2, sim))
        normalized['suspicious_pairs'] = suspicious_pairs

    # Build similarity_matrix if missing but pairwise_results available
    if not normalized.get('similarity_matrix') and normalized.get('pairwise_results') and normalized.get('files'):
        files = list(normalized.get('files') or [])
        idx = {f: i for i, f in enumerate(files)}
        n = len(files)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 1.0
        for r in normalized.get('pairwise_results', []):
            f1 = r.get('file1')
            f2 = r.get('file2')
            if f1 in idx and f2 in idx:
                i = idx[f1]
                j = idx[f2]
                try:
                    sim = float(r.get('similarity', 0) or 0)
                except Exception:
                    sim = 0.0
                matrix[i][j] = sim
                matrix[j][i] = sim
        normalized['similarity_matrix'] = matrix

    # If cluster_data is missing but matrix exists, set empty dict (graph tab will recompute)
    if normalized.get('similarity_matrix') and normalized.get('cluster_data') is None:
        normalized['cluster_data'] = {}

    return normalized


def _show_submission_details(submission):
    """Show detailed information about a submission."""
    st.markdown("#### 📊 Detalhes da Submissão")
    
    sub_id = getattr(submission, 'id', 0)
    files_count = getattr(submission, 'files_count', 0) or 0
    suspicious_count = getattr(submission, 'suspicious_pairs_count', 0) or 0
    avg_sim = getattr(submission, 'average_similarity', 0.0) or 0.0
    max_sim = getattr(submission, 'max_similarity', 0.0) or 0.0
    threshold = getattr(submission, 'threshold', 0.7) or 0.7
    language = getattr(submission, 'language', 'N/A')
    filename = getattr(submission, 'filename', 'N/A')
    created_at = getattr(submission, 'created_at', None)
    processed_at = getattr(submission, 'processed_at', None)
    time_seconds = getattr(submission, 'analysis_time_seconds', 0.0) or 0.0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Informações Gerais**")
        st.markdown(f"- **ID:** {sub_id}")
        st.markdown(f"- **Arquivo:** {filename}")
        st.markdown(f"- **Linguagem:** {language}")
        st.markdown(f"- **Threshold:** {int(threshold * 100)}%")
        st.markdown(f"- **Arquivos analisados:** {files_count}")
        
        if created_at:
            st.markdown(f"- **Criado em:** {created_at.strftime('%d/%m/%Y %H:%M:%S')}")
        
        if processed_at:
            st.markdown(f"- **Processado em:** {processed_at.strftime('%d/%m/%Y %H:%M:%S')}")
    
    with col2:
        st.markdown("**Resultados**")
        st.markdown(f"- **Pares suspeitos:** {suspicious_count}")
        st.markdown(f"- **Similaridade média:** {avg_sim:.2%}")
        st.markdown(f"- **Similaridade máxima:** {max_sim:.2%}")
        st.markdown(f"- **Tempo de análise:** {time_seconds:.2f}s")
        
        if avg_sim > 0.7:
            st.error("🔴 Alta similaridade detectada")
        elif avg_sim > 0.5:
            st.warning("🟡 Similaridade moderada")
        else:
            st.success("🟢 Similaridade baixa")


def _delete_submission(submission_id: int, user_id: int, submission_repo: SubmissionRepository):
    """Delete a single submission."""
    try:
        success = submission_repo.delete(submission_id)
        
        if success:
            st.success(f"✓ Submissão {submission_id} excluída!")
            st.toast("✓ Submissão removida")
            
            # Clear from session if loaded
            if st.session_state.get('loaded_submission_id') == submission_id:
                st.session_state['loaded_submission_id'] = None
                st.session_state['last_analysis'] = None
            
            # Invalidate cache
            from utils.db_cache import get_submission_cache
            cache = get_submission_cache()
            cache.invalidate_user(user_id)
            
            logger.info(f"User {user_id} deleted submission {submission_id}")
        else:
            st.error(f"❌ Submissão {submission_id} não encontrada")
        
    except Exception as e:
        logger.error(f"Error deleting submission {submission_id}: {e}")
        st.error(f"❌ Erro ao excluir submissão: {str(e)}")
