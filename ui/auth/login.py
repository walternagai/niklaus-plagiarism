"""
Authentication UI components for Niklaus.
"""

import streamlit as st
from auth.oauth import OAuthHandler, OAuthConfig
from auth.session import SessionManager
from auth.decorators import guest_required
from utils.logger import get_logger

logger = get_logger(__name__)


@guest_required
def render_login_page():
    """Render login page with OAuth providers."""
    
    st.title("🔐 Login - Niklaus")
    st.markdown("### Detecte plágio em código-fonte")
    st.markdown("---")
    
    st.markdown("#### Faça login para continuar")
    st.markdown("Escolha uma das opções abaixo:")
    
    config = OAuthConfig()
    
    col1, col2, col3 = st.columns(3)
    
    # Google
    with col1:
        if config.is_oauth_configured('google'):
            if st.button("🔵 Continuar com Google", use_container_width=True, type="primary"):
                _initiate_oauth('google')
        else:
            st.button("🔵 Google (não configurado)", use_container_width=True, disabled=True)
    
    # GitHub
    with col2:
        if config.is_oauth_configured('github'):
            if st.button("⚫ Continuar com GitHub", use_container_width=True, type="primary"):
                _initiate_oauth('github')
        else:
            st.button("⚫ GitHub (não configurado)", use_container_width=True, disabled=True)
    
    # Microsoft
    with col3:
        if config.is_oauth_configured('microsoft'):
            if st.button("🔷 Continuar com Microsoft", use_container_width=True, type="primary"):
                _initiate_oauth('microsoft')
        else:
            st.button("🔷 Microsoft (não configurado)", use_container_width=True, disabled=True)
    
    st.markdown("---")
    
    st.info("""
    🔒 **Sua privacidade é importante**
    
    - Seus dados são armazenados de forma segura
    - Apenas informações básicas do perfil são obtidas
    - Suas análises são privadas por padrão
    """)
    
    # Admin info
    if config.admin_emails:
        st.caption(f"👑 Administradores: {', '.join(config.admin_emails)}")
    
    # Manual login (development only)
    if st.checkbox("Login manual (desenvolvimento)"):
        _manual_login_form()


def _initiate_oauth(provider: str):
    """Initiate OAuth login flow."""
    try:
        handler = OAuthHandler(provider)
        import secrets as sec
        state = sec.token_urlsafe(32)
        
        st.session_state['oauth_state'] = state
        st.session_state['oauth_provider'] = provider
        st.session_state['login_initiated'] = True
        
        auth_url = handler.get_authorization_url(state=state)
        
        st.markdown(f"**Clique no link abaixo para autenticar:**")
        st.markdown(f"[Login com {provider.title()}]({auth_url})")
        
        logger.info(f"OAuth login initiated for {provider}")
        
    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}")
        st.error(f"Erro ao iniciar login: {str(e)}")


def _manual_login_form():
    """Manual login form for development."""
    st.markdown("### Login Manual (Desenvolvimento)")
    
    email = st.text_input("Email")
    name = st.text_input("Nome")
    
    if st.button("Entrar", type="primary"):
        if not email or not name:
            st.error("Email e nome são obrigatórios")
            return
        
        try:
            from auth.oauth import OAuthHandler
            
            user = OAuthHandler.create_user_from_oauth(
                email=email,
                name=name,
                provider='manual'
            )
            
            SessionManager.login(user)
            st.success(f"Bem-vindo, {user.name}!")
            st.rerun()
            
        except Exception as e:
            logger.error(f"Manual login error: {e}")
            st.error(f"Erro no login: {str(e)}")


if __name__ == "__main__":
    render_login_page()