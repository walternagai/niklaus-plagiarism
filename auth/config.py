"""
OAuth configuration manager for Niklaus.
"""

import os
from typing import Set
from utils.logger import get_logger

logger = get_logger(__name__)


class OAuthConfig:
    """OAuth configuration manager."""
    
    def __init__(self):
        """Load OAuth configuration from secrets."""
        try:
            import streamlit as st
            secrets = st.secrets
        except:
            secrets = {}
        
        # Google - supports both flat and nested config
        if 'google' in secrets:
            google = secrets['google']
            self.google_client_id = google.get('client_id', '')
            self.google_client_secret = google.get('client_secret', '')
            self.google_redirect_uri = google.get('redirect_uri', 'http://localhost:8501/oauth/callback/google')
        else:
            self.google_client_id = secrets.get('GOOGLE_CLIENT_ID', os.getenv('GOOGLE_CLIENT_ID', ''))
            self.google_client_secret = secrets.get('GOOGLE_CLIENT_SECRET', os.getenv('GOOGLE_CLIENT_SECRET', ''))
            self.google_redirect_uri = secrets.get('GOOGLE_REDIRECT_URI', os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8501/oauth/callback/google'))
        
        # GitHub - supports both flat and nested config
        if 'github' in secrets:
            github = secrets['github']
            self.github_client_id = github.get('client_id', '')
            self.github_client_secret = github.get('client_secret', '')
            self.github_redirect_uri = github.get('redirect_uri', 'http://localhost:8501/oauth/callback/github')
        else:
            self.github_client_id = secrets.get('GITHUB_CLIENT_ID', os.getenv('GITHUB_CLIENT_ID', ''))
            self.github_client_secret = secrets.get('GITHUB_CLIENT_SECRET', os.getenv('GITHUB_CLIENT_SECRET', ''))
            self.github_redirect_uri = secrets.get('GITHUB_REDIRECT_URI', os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8501/oauth/callback/github'))
        
        # Microsoft - supports both flat and nested config
        if 'microsoft' in secrets:
            microsoft = secrets['microsoft']
            self.microsoft_client_id = microsoft.get('client_id', '')
            self.microsoft_client_secret = microsoft.get('client_secret', '')
            self.microsoft_redirect_uri = microsoft.get('redirect_uri', 'http://localhost:8501/oauth/callback/microsoft')
            self.microsoft_tenant_id = microsoft.get('tenant_id', 'common')
        else:
            self.microsoft_client_id = secrets.get('MICROSOFT_CLIENT_ID', os.getenv('MICROSOFT_CLIENT_ID', ''))
            self.microsoft_client_secret = secrets.get('MICROSOFT_CLIENT_SECRET', os.getenv('MICROSOFT_CLIENT_SECRET', ''))
            self.microsoft_redirect_uri = secrets.get('MICROSOFT_REDIRECT_URI', os.getenv('MICROSOFT_REDIRECT_URI', 'http://localhost:8501/oauth/callback/microsoft'))
            self.microsoft_tenant_id = secrets.get('MICROSOFT_TENANT_ID', os.getenv('MICROSOFT_TENANT_ID', 'common'))
        
        # Admin users
        self.admin_emails = self._load_admin_emails()
    
    def _load_admin_emails(self) -> Set[str]:
        """Load admin emails from config."""
        try:
            import streamlit as st
            admin_list = st.secrets.get('ADMIN_EMAILS', '')
        except:
            admin_list = os.getenv('ADMIN_EMAILS', '')
        
        return set(email.strip().lower() for email in admin_list.split(',') if email.strip())
    
    def is_admin(self, email: str) -> bool:
        """Check if email is in admin list."""
        return email.lower() in self.admin_emails
    
    def is_oauth_configured(self, provider: str) -> bool:
        """Check if OAuth provider is configured."""
        if provider == 'google':
            return bool(self.google_client_id and self.google_client_secret)
        elif provider == 'github':
            return bool(self.github_client_id and self.github_client_secret)
        elif provider == 'microsoft':
            return bool(self.microsoft_client_id and self.microsoft_client_secret)
        return False
    
    def get_available_providers(self) -> list:
        """Get list of configured OAuth providers."""
        providers = []
        if self.is_oauth_configured('google'):
            providers.append('google')
        if self.is_oauth_configured('github'):
            providers.append('github')
        if self.is_oauth_configured('microsoft'):
            providers.append('microsoft')
        return providers