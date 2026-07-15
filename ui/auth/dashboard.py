"""
User dashboard for Niklaus.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from auth.decorators import require_auth
from auth.session import SessionManager
from auth.database import get_session
from auth.repository import SubmissionRepository
from utils.logger import get_logger

logger = get_logger(__name__)


@require_auth
def render_dashboard():
    """Render user dashboard."""
    
    user = st.session_state.user
    
    st.title(f"👤 Dashboard - {user.name}")
    st.markdown(f"**{user.email}** | {'👑 Admin' if user.is_admin else '👤 Usuário'}")
    
    st.markdown("---")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Submissões", user.submissions_count or 0)
    
    with col2:
        st.metric("Arquivos Analisados", user.total_analyses or 0)
    
    with col3:
        st.metric("Pares Suspeitos", user.total_suspicious_pairs or 0)
    
    with col4:
        st.metric("Último Login", 
                   user.last_login_at.strftime('%d/%m %H:%M') if user.last_login_at else "N/A")
    
    st.markdown("---")
    
    # Recent submissions
    st.markdown("### 📊 Últimas Submissões")
    
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    submissions = submission_repo.find_by_user(user.id, limit=10)
    
    if not submissions:
        st.info("Você ainda não fez nenhuma submissão.")
        if st.button("➕ Nova Análise", use_container_width=True, type="primary"):
            st.switch_page("pages/upload.py")
    else:
        _render_submissions_table(submissions)
    
    db.close()
    
    # Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Nova Análise", use_container_width=True, type="primary"):
            st.switch_page("pages/upload.py")
    
    with col2:
        if st.button("📜 Ver Histórico", use_container_width=True):
            st.switch_page("pages/history.py")
    
    with col3:
        if st.button("📁 Meus Arquivos", use_container_width=True):
            st.info("Em desenvolvimento")
            # st.switch_page("pages/files.py")


def _render_submissions_table(submissions):
    """Render submissions table."""
    
    data = []
    for s in submissions:
        data.append({
            'Data': s.created_at.strftime('%d/%m/%Y %H:%M'),
            'Arquivo': s.filename,
            'Linguagem': s.language,
            'Limiar': f"{s.threshold:.0%}",
            'Pares': s.suspicious_pairs_count or 0,
            'Tempo': f"{s.analysis_time_seconds:.1f}s" if s.analysis_time_seconds else "-",
            'Status': '✅' if s.status == 'completed' else '⚠️'
        })
    
    df = pd.DataFrame(data)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # View details
    submission_id = st.selectbox(
        "Ver detalhes da análise",
        options=[s.id for s in submissions],
        format_func=lambda x: next(
            (f"{s.filename} ({s.created_at.strftime('%d/%m')})" 
             for s in submissions if s.id == x), ""
        )
    )
    
    if st.button("🔍 Ver Detalhes", use_container_width=True):
        db = get_session()
        submission_repo = SubmissionRepository(db)
        submission = submission_repo.find_by_id(submission_id)
        
        if submission and submission.has_analysis_data():
            st.session_state['last_analysis'] = submission.analysis_data
            st.switch_page("pages/results.py")
        else:
            st.warning("Análise não disponível para esta submissão.")
        
        db.close()