"""
Admin panel for Niklaus.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from auth.decorators import require_admin
from auth.database import get_session
from auth.repository import UserRepository, SubmissionRepository
from utils.logger import get_logger

logger = get_logger(__name__)


@require_admin
def render_admin_page():
    """Render admin panel."""
    
    user = st.session_state.user
    
    st.title("👑 Painel Administrativo")
    st.markdown(f"**{user.email}**")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Usuários", "Submissões", "Sistema"])
    
    with tab1:
        _render_users_tab()
    
    with tab2:
        _render_submissions_tab()
    
    with tab3:
        _render_system_tab()


def _render_users_tab():
    """Render users management tab."""
    st.markdown("### 👥 Usuários")
    
    db = get_session()
    user_repo = UserRepository(db)
    
    users = user_repo.get_all_active(limit=1000)
    
    if not users:
        st.info("Nenhum usuário cadastrado.")
        db.close()
        return
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Usuários", len(users))
    
    with col2:
        admins = sum(1 for u in users if u.is_admin)
        st.metric("Administradores", admins)
    
    with col3:
        regular = sum(1 for u in users if not u.is_admin)
        st.metric("Usuários", regular)
    
    st.markdown("---")
    
    # Users table
    data = []
    for u in users:
        data.append({
            'ID': u.id,
            'Email': u.email,
            'Nome': u.name,
            'Papel': '👑 Admin' if u.is_admin else '👤 User',
            'Submissões': u.submissions_count or 0,
            'Cadastro': u.created_at.strftime('%d/%m/%Y') if u.created_at else '-',
            'Último Login': u.last_login_at.strftime('%d/%m %H:%M') if u.last_login_at else '-'
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    db.close()


def _render_submissions_tab():
    """Render submissions management tab."""
    st.markdown("### 📊 Submissões")
    
    db = get_session()
    submission_repo = SubmissionRepository(db)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = submission_repo.count_by_status('completed')
        st.metric("Concluídas", total)
    
    with col2:
        pending = submission_repo.count_by_status('pending')
        st.metric("Pendentes", pending)
    
    with col3:
        failed = submission_repo.count_by_status('failed')
        st.metric("Falharam", failed)
    
    with col4:
        total_all = total + pending + failed
        st.metric("Total", total_all)
    
    st.markdown("---")
    
    # Recent submissions
    st.markdown("### Últimas Submissões")
    
    recent = submission_repo.get_recent_logs(limit=50)
    
    if not recent:
        st.info("Nenhuma submissão encontrada.")
        db.close()
        return
    
    data = []
    for s in recent:
        data.append({
            'ID': s.id,
            'Email': s.user.email if s.user else '-',
            'Arquivo': s.filename,
            'Linguagem': s.language,
            'Status': s.status,
            'Pares': s.suspicious_pairs_count or 0,
            'Data': s.created_at.strftime('%d/%m/%Y %H:%M')
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    db.close()


def _render_system_tab():
    """Render system information tab."""
    st.markdown("### ⚙️ Sistema")
    
    from auth.database import get_db_manager
    
    db_manager = get_db_manager()
    
    st.markdown("#### Banco de Dados")
    st.write(f"**URL:** `{db_manager.database_url}`")
    
    st.markdown("#### Cache")
    
    if st.button("Limpar Cache Expirado", use_container_width=True):
        from auth.repository import CacheRepository
        
        db = get_session()
        cache_repo = CacheRepository(db)
        removed = cache_repo.delete_expired()
        db.close()
        
        st.success(f"{removed} entradas de cache removidas!")
    
    st.markdown("#### Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Criar Usuário Admin", use_container_width=True):
            st.switch_page("pages/create_admin.py")
    
    with col2:
        if st.button("Ver Logs", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")

if __name__ == "__main__":
    render_admin_page()