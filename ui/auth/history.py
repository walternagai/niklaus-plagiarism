"""
Submission history page for Niklaus.
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
def render_history_page():
    """Render submission history page."""
    
    user = st.session_state.user
    
    st.title("📜 Histórico de Submissões")
    st.markdown(f"**{user.email}**")
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        language_filter = st.selectbox(
            "Linguagem",
            options=["Todas", "Python", "Java", "C", "C++", "JavaScript", "Go", "Rust", "TypeScript", "Kotlin"]
        )
    
    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["Todos", "Concluído", "Pendente", "Falhou"]
        )
    
    with col3:
        limit = st.selectbox(
            "Quantidade",
            options=[10, 25, 50, 100],
            index=0
        )
    
    # Get submissions
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    status_map = {
        "Todos": None,
        "Concluído": "completed",
        "Pendente": "pending",
        "Falhou": "failed"
    }
    
    submissions = submission_repo.find_by_user(
        user.id,
        limit=limit,
        status=status_map.get(status_filter)
    )
    
    # Apply language filter
    if language_filter != "Todas":
        submissions = [s for s in submissions if s.language == language_filter]
    
    if not submissions:
        st.info("Nenhuma submissão encontrada com os filtros selecionados.")
        db.close()
        return
    
    # Statistics
    st.markdown("### 📊 Estatísticas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_files = sum(s.files_count or 0 for s in submissions)
        st.metric("Total de Arquivos", total_files)
    
    with col2:
        total_pairs = sum(s.suspicious_pairs_count or 0 for s in submissions)
        st.metric("Total de Pares Suspeitos", total_pairs)
    
    with col3:
        avg_time = sum(s.analysis_time_seconds or 0 for s in submissions) / len(submissions) if submissions else 0
        st.metric("Tempo Médio", f"{avg_time:.1f}s")
    
    st.markdown("---")
    
    # Submissions table
    st.markdown("### 📋 Submissões")
    
    data = []
    for s in submissions:
        data.append({
            'ID': s.id,
            'Data': s.created_at.strftime('%d/%m/%Y %H:%M'),
            'Arquivo': s.filename,
            'Linguagem': s.language,
            'Limiar': f"{s.threshold:.0%}",
            'Arquivos': s.files_count or 0,
            'Suspeitos': s.suspicious_pairs_count or 0,
            'Tempo': f"{s.analysis_time_seconds:.2f}s" if s.analysis_time_seconds else "-",
            'Status': s.status
        })
    
    df = pd.DataFrame(data)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Actions
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Exportar CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                "Baixar CSV",
                data=csv,
                file_name=f"historico_submissoes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()
    
    # View details
    st.markdown("---")
    st.markdown("### 🔍 Ver Detalhes")
    
    submission_id = st.selectbox(
        "Selecione uma submissão",
        options=[s.id for s in submissions],
        format_func=lambda x: next(
            (f"{s.filename} ({s.created_at.strftime('%d/%m/%Y')})" 
             for s in submissions if s.id == x), ""
        )
    )
    
    if st.button("Ver Análise Completa", type="primary", use_container_width=True):
        submission = submission_repo.find_by_id(submission_id)
        
        if submission and submission.has_analysis_data():
            st.session_state['last_analysis'] = submission.analysis_data
            st.switch_page("pages/results.py")
        else:
            st.warning("Análise não disponível.")
    
    db.close()