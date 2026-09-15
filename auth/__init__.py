"""
Authentication module for Niklaus plagiarism detector.
"""

from auth.config import OAuthConfig
from auth.database import DatabaseManager, get_db, get_db_manager, get_session, init_db
from auth.decorators import guest_required, require_admin, require_auth
from auth.models import AnalysisCache, AuditLog, Base, Submission, User
from auth.oauth import OAuthHandler
from auth.repository import AuditRepository, CacheRepository, SubmissionRepository, UserRepository
from auth.session import SessionManager

__all__ = [
    # Models
    'User',
    'Submission', 
    'AnalysisCache',
    'AuditLog',
    'Base',
    
    # Database
    'DatabaseManager',
    'get_db_manager',
    'get_db',
    'get_session',
    'init_db',
    
    # OAuth
    'OAuthHandler',
    'OAuthConfig',
    
    # Repository
    'UserRepository',
    'SubmissionRepository',
    'CacheRepository',
    'AuditRepository',
    
    # Decorators
    'require_auth',
    'require_admin',
    'guest_required',
    
    # Session
    'SessionManager',
]