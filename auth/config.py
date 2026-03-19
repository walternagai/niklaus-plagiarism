"""
OAuth configuration manager for Niklaus.
"""

import base64
import hashlib
import os
from typing import Optional, Set
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Token encryption helpers (Fernet / AES-128-CBC)
# ---------------------------------------------------------------------------

def _get_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from NIKLAUS_SECRET_KEY env / Streamlit secret.

    The raw value is SHA-256-hashed so any length of secret works, then
    URL-safe base64-encoded (Fernet requires exactly 32 raw bytes encoded as
    url-safe base64).
    """
    try:
        import streamlit as st
        raw = st.secrets.get("NIKLAUS_SECRET_KEY", "")
    except Exception:
        raw = ""

    if not raw:
        raw = os.getenv("NIKLAUS_SECRET_KEY", "")

    if not raw:
        logger.warning(
            "NIKLAUS_SECRET_KEY is not set. OAuth tokens will use a weak "
            "derivation key. Set NIKLAUS_SECRET_KEY in your secrets/env."
        )
        # Fallback: derive from module path so it is at least stable per installation
        raw = __file__

    key_bytes = hashlib.sha256(str(raw).encode()).digest()  # always 32 bytes
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_token(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt *plaintext* token with Fernet. Returns base64 ciphertext string."""
    if not plaintext:
        return plaintext
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_fernet_key())
        return f.encrypt(plaintext.encode()).decode()
    except Exception as exc:
        logger.error(f"Token encryption failed: {exc}")
        return plaintext  # Fallback: store unencrypted rather than lose the token


def decrypt_token(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt Fernet *ciphertext* token. Returns plaintext string."""
    if not ciphertext:
        return ciphertext
    try:
        from cryptography.fernet import Fernet, InvalidToken
        f = Fernet(_get_fernet_key())
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Token may be stored in plaintext (before encryption was introduced)
        return ciphertext


class OAuthConfig:
    """OAuth configuration manager."""
    
    def __init__(self):
        """Load OAuth configuration from secrets."""
        try:
            import streamlit as st
            secrets = st.secrets
        except Exception as e:
            logger.debug(f"OAuthConfig: unable to load Streamlit secrets: {e}")
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
        
        # Application secret key (used for HMAC signing of OAuth state)
        self.secret_key: str = self._load_secret_key()

        # Admin users
        self.admin_emails = self._load_admin_emails()
    
    def _load_secret_key(self) -> str:
        """Load NIKLAUS_SECRET_KEY from Streamlit secrets or environment."""
        try:
            import streamlit as st
            value = st.secrets.get("NIKLAUS_SECRET_KEY", "")
        except Exception:
            value = ""

        if not value:
            value = os.getenv("NIKLAUS_SECRET_KEY", "")

        if not value:
            logger.warning(
                "NIKLAUS_SECRET_KEY is not configured. OAuth state signing will "
                "use a weak fallback key. Set NIKLAUS_SECRET_KEY for security."
            )
            # Derive a semi-stable fallback from available OAuth secrets so
            # existing deployments don't break, but it is weaker than an
            # explicit key.
            value = "|".join([
                self.google_client_secret or "",
                self.github_client_secret or "",
                self.microsoft_client_secret or "",
            ]) or "niklaus-insecure-fallback"

        return value

    def _load_admin_emails(self) -> Set[str]:
        """Load admin emails from config."""
        try:
            import streamlit as st
            admin_list = st.secrets.get('ADMIN_EMAILS', '')
        except Exception as e:
            logger.debug(f"OAuthConfig: unable to load ADMIN_EMAILS from secrets: {e}")
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
