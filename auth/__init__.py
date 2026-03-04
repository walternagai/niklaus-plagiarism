"""
Authentication module for Niklaus plagiarism detector.
"""

from auth.models import User, Submission, AnalysisCache, AuditLog, Base
from auth.database import DatabaseManager, get_db_manager, get_db, init_db
from auth.oauth import OAuthHandler, OAuthConfig
from auth.repository import UserRepository, SubmissionRepository, CacheRepository, AuditRepository
from auth.decorators import require_auth, require_admin, login_required
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
    'login_required',
    
    # Session
    'SessionManager',
]