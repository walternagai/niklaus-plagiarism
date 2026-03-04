"""
Authentication decorators for Streamlit.
"""

from functools import wraps
import streamlit as st
from typing import Callable
from utils.logger import get_logger

logger = get_logger(__name__)


def require_auth(func: Callable) -> Callable:
    """Decorator that requires authentication."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state or st.session_state.user is None:
            st.warning("⚠️ Você precisa estar logado para acessar esta página.")
            if st.button("🔑 Fazer Login", use_container_width=True):
                st.session_state.redirect_to = st.session_state.get('current_page', 'upload')
                st.switch_page("pages/login.py")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def require_admin(func: Callable) -> Callable:
    """Decorator that requires admin role."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state or st.session_state.user is None:
            st.warning("⚠️ Você precisa estar logado para acessar esta página.")
            st.stop()
        
        user = st.session_state.user
        
        if not user.is_admin:
            st.error("⛔ Acesso restrito a administradores.")
            logger.warning(f"User {user.email} attempted to access admin page")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def guest_required(func: Callable) -> Callable:
    """Decorator for pages that should only be visible to non-authenticated users."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' in st.session_state and st.session_state.user is not None:
            st.info(f"ℹ️ Você já está logado como {st.session_state.user.name}")
            if st.button("Ir para o Dashboard"):
                st.switch_page("pages/dashboard.py")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper