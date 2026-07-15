"""
User profile page for Niklaus.
"""

import streamlit as st
from auth.decorators import require_auth
from auth.session import SessionManager
from auth.database import get_session
from auth.repository import UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)


@require_auth
def render_profile_page():
    """Render user profile page."""
    
    user = st.session_state.user
    user_id = user.get('id') if isinstance(user, dict) else user.id
    user_email = user.get('email') if isinstance(user, dict) else user.email
    user_name = user.get('name') if isinstance(user, dict) else user.name
    is_admin = user.get('is_admin', False) if isinstance(user, dict) else getattr(user, 'is_admin', False)
    
    st.title("👤 Perfil")
    st.markdown(f"**{user_email}**")
    
    st.markdown("---")
    
    # User info from database
    db = get_session()
    user_repo = UserRepository(db)
    user_obj = user_repo.find_by_id(user_id)
    db.close()
    
    if user_obj:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Informações")
            st.write(f"**Nome:** {user_obj.name}")
            st.write(f"**Email:** {user_obj.email}")
            st.write(f"**Papel:** {'👑 Administrador' if user_obj.role == 'admin' else '👤 Usuário'}")
            st.write(f"**Cadastro:** {user_obj.created_at.strftime('%d/%m/%Y') if user_obj.created_at else 'N/A'}")
            st.write(f"**Último login:** {user_obj.last_login_at.strftime('%d/%m/%Y %H:%M') if user_obj.last_login_at else 'N/A'}")
        
        with col2:
            st.markdown("### Estatísticas")
            st.write(f"**Submissões:** {user_obj.submissions_count or 0}")
            st.write(f"**Arquivos analisados:** {user_obj.total_analyses or 0}")
            st.write(f"**Pares suspeitos:** {user_obj.total_suspicious_pairs or 0}")
    
    st.markdown("---")
    
    # Settings
    st.markdown("### ⚙️ Configurações")
    
    with st.form("settings_form"):
        language = st.selectbox("Linguagem padrão", ["Python", "Java", "C", "C++", "JavaScript"])
        notifications = st.checkbox("Receber notificações por email", value=True)
        
        if st.form_submit_button("Salvar Configurações", type="primary"):
            db = get_session()
            user_repo = UserRepository(db)
            
            settings = {
                'language': language,
                'notifications': notifications
            }
            
            user_repo.update_settings(user_id, settings)
            db.close()
            
            st.success("Configurações salvas!")
            st.rerun()
    
    st.markdown("---")
    
    # Actions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpar Cache", use_container_width=True):
            from auth.repository import CacheRepository
            
            db = get_session()
            cache_repo = CacheRepository(db)
            removed = cache_repo.clear_user_cache(user_id)
            db.close()
            
            st.success(f"{removed} arquivos de cache removidos!")
    
    with col2:
        if st.button("🚪 Sair", use_container_width=True):
            SessionManager.logout()
            st.success("Você saiu da sua conta.")
            st.rerun()


if __name__ == "__main__":
    render_profile_page()