"""
OAuth callback page - handles OAuth provider redirects.
"""

import streamlit as st
from auth.oauth import OAuthHandler
from auth.session import SessionManager
from auth.decorators import guest_required
from utils.logger import get_logger

logger = get_logger(__name__)


@guest_required
def handle_oauth_callback():
    """Handle OAuth callback from providers."""
    
    params = st.query_params
    
    code = params.get('code')
    state = params.get('state')
    error = params.get('error')
    error_description = params.get('error_description', 'Unknown error')
    
    provider = st.session_state.get('oauth_provider')
    
    if error:
        st.error(f"Erro de autenticação: {error_description}")
        logger.error(f"OAuth error: {error} - {error_description}")
        st.markdown("Voltar para o [login](/login)")
        return
    
    if not code or not provider:
        st.error("Parâmetros de autenticação inválidos")
        st.markdown("Voltar para o [login](/login)")
        return
    
    saved_state = st.session_state.get('oauth_state')
    if saved_state and state != saved_state:
        st.error("Erro de segurança: State inválido")
        logger.error(f"OAuth state mismatch for {provider}")
        st.markdown("Voltar para o [login](/login)")
        return
    
    try:
        handler = OAuthHandler(provider)
        user = handler.handle_callback(code, state)
        
        if user:
            SessionManager.login(user)
            st.success(f"Bem-vindo, {user.name}!")
            logger.info(f"User {user.email} logged in via {provider}")
            
            for key in ['oauth_state', 'oauth_provider', 'login_initiated']:
                if key in st.session_state:
                    del st.session_state[key]
            
            redirect_to = SessionManager.get_redirect() or "/"
            SessionManager.clear_redirect()
            
            st.switch_page(redirect_to)
        else:
            st.error("Falha ao autenticar usuário")
            logger.error(f"Failed to create user from OAuth callback for {provider}")
            st.markdown("Voltar para o [login](/login)")
            
    except Exception as e:
        st.error(f"Erro durante autenticação: {str(e)}")
        logger.error(f"OAuth callback exception: {str(e)}", exc_info=True)
        st.markdown("Voltar para o [login](/login)")


def main():
    """Main entry point for OAuth callback page."""
    st.title("⏳ Processando login...")
    
    handle_oauth_callback()


if __name__ == "__main__":
    main()