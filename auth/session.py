"""
Session management utilities for Streamlit.
"""

import streamlit as st
from typing import Optional, Union, Dict, Any
from datetime import datetime, timedelta, UTC

from auth.models import User
from auth.repository import UserRepository
from auth.database import get_session
from utils.logger import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Return current UTC datetime without tzinfo for session checks."""
    return datetime.now(UTC).replace(tzinfo=None)


class SessionManager:
    """Manages user sessions in Streamlit."""
    
    SESSION_KEY = 'user'
    SESSION_EXPIRY_KEY = 'session_expires'
    REDIRECT_KEY = 'redirect_after_login'
    
    @staticmethod
    def login(user: Union[User, Dict[str, Any]]) -> None:
        """Create user session."""
        if isinstance(user, dict):
            user_dict = user
        else:
            user_dict = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'is_admin': user.role == 'admin'
            }
        
        st.session_state[SessionManager.SESSION_KEY] = user_dict
        st.session_state[SessionManager.SESSION_EXPIRY_KEY] = (
            utcnow() + timedelta(hours=24)
        )
        
        db = get_session()
        user_repo = UserRepository(db)
        user_repo.update_last_login(user_dict['id'])
        db.close()
        
        logger.info(f"User {user_dict['email']} logged in")
    
    @staticmethod
    def logout() -> None:
        """Logout current user and clear session."""
        if SessionManager.SESSION_KEY in st.session_state:
            user = st.session_state[SessionManager.SESSION_KEY]
            email = user.get('email', 'unknown') if isinstance(user, dict) else 'unknown'
            logger.info(f"User {email} logging out")
        
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.clear()
    
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get currently logged in user."""
        user = st.session_state.get(SessionManager.SESSION_KEY)
        
        if not user:
            return None
        
        expiry = st.session_state.get(SessionManager.SESSION_EXPIRY_KEY)
        if expiry and utcnow() > expiry:
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
        return user is not None and user.get('is_admin', False)
    
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
    def refresh_user() -> Optional[Dict[str, Any]]:
        """Refresh user data from database."""
        current_user = SessionManager.get_current_user()
        if not current_user:
            return None
        
        db = get_session()
        user_repo = UserRepository(db)
        user = user_repo.find_by_id(current_user['id'])
        db.close()
        
        if user:
            user_dict = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'is_admin': user.role == 'admin'
            }
            st.session_state[SessionManager.SESSION_KEY] = user_dict
            return user_dict
        
        return None


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
