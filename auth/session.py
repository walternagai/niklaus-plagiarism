"""
Session management utilities for Streamlit.
"""

import streamlit as st
from typing import Optional
from datetime import datetime, timedelta

from auth.models import User
from auth.repository import UserRepository
from auth.database import get_session
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages user sessions in Streamlit."""
    
    SESSION_KEY = 'user'
    SESSION_EXPIRY_KEY = 'session_expires'
    REDIRECT_KEY = 'redirect_after_login'
    
    @staticmethod
    def login(user: User) -> None:
        """Create user session."""
        st.session_state[SessionManager.SESSION_KEY] = user
        st.session_state[SessionManager.SESSION_EXPIRY_KEY] = (
            datetime.utcnow() + timedelta(hours=24)
        )
        
        db = get_session()
        user_repo = UserRepository(db)
        user_repo.update_last_login(user.id)
        db.close()
        
        logger.info(f"User {user.email} logged in")
    
    @staticmethod
    def logout() -> None:
        """Logout current user and clear session."""
        if SessionManager.SESSION_KEY in st.session_state:
            user = st.session_state[SessionManager.SESSION_KEY]
            logger.info(f"User {user.email if user else 'unknown'} logging out")
        
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.clear()
    
    @staticmethod
    def get_current_user() -> Optional[User]:
        """Get currently logged in user."""
        user = st.session_state.get(SessionManager.SESSION_KEY)
        
        if not user:
            return None
        
        expiry = st.session_state.get(SessionManager.SESSION_EXPIRY_KEY)
        if expiry and datetime.utcnow() > expiry:
            SessionManager.logout()
            return None
        
        return user
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated."""
        return SessionManager.get_current_user() is not None
    
    @staticmethod
    def is_admin() -> bool:
        """Check if current user is admin."""
        user = SessionManager.get_current_user()
        return user is not None and user.is_admin
    
    @staticmethod
    def set_redirect(page: str) -> None:
        """Set redirect target after login."""
        st.session_state[SessionManager.REDIRECT_KEY] = page
    
    @staticmethod
    def get_redirect() -> Optional[str]:
        """Get redirect target after login."""
        return st.session_state.get(SessionManager.REDIRECT_KEY)
    
    @staticmethod
    def clear_redirect() -> None:
        """Clear redirect target."""
        if SessionManager.REDIRECT_KEY in st.session_state:
            del st.session_state[SessionManager.REDIRECT_KEY]
    
    @staticmethod
    def refresh_user() -> Optional[User]:
        """Refresh user data from database."""
        current_user = SessionManager.get_current_user()
        if not current_user:
            return None
        
        db = get_session()
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(current_user.id)
        db.close()
        
        if user:
            st.session_state[SessionManager.SESSION_KEY] = user
        
        return user


def init_session_state() -> None:
    """Initialize Streamlit session state with defaults."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if 'page' not in st.session_state:
        st.session_state.page = 'upload'
    
    if 'last_analysis' not in st.session_state:
        st.session_state.last_analysis = None
    
    if 'settings' not in st.session_state:
        st.session_state.settings = {}