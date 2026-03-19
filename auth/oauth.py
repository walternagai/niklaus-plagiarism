"""
OAuth handlers for Google, GitHub, and Microsoft authentication.
"""

import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, UTC

from auth.models import User
from auth.database import get_session
from auth.config import OAuthConfig, encrypt_token, decrypt_token
from auth.repository import UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Return current UTC datetime without tzinfo for DB compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class OAuthHandler:
    """Handles OAuth authentication for multiple providers."""
    
    def __init__(self, provider: str):
        self.provider = provider.lower()
        self.config = OAuthConfig()
        
        self.providers = {
            'google': {
                'client_id': self.config.google_client_id,
                'client_secret': self.config.google_client_secret,
                'redirect_uri': self.config.google_redirect_uri,
            },
            'github': {
                'client_id': self.config.github_client_id,
                'client_secret': self.config.github_client_secret,
                'redirect_uri': self.config.github_redirect_uri,
            },
            'microsoft': {
                'client_id': self.config.microsoft_client_id,
                'client_secret': self.config.microsoft_client_secret,
                'redirect_uri': self.config.microsoft_redirect_uri,
            }
        }
        
        if self.provider not in self.providers:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def get_authorization_url(self, state: str = None) -> str:
        """Build the OAuth provider authorization URL.

        If *state* is not provided a random one is generated.  The caller is
        responsible for persisting the state value (e.g. in st.session_state)
        before redirecting — this method no longer writes to session state as
        a side effect.
        """
        if not state:
            state = secrets.token_urlsafe(32)

        client_id = self.providers[self.provider]['client_id']
        redirect_uri = self.providers[self.provider]['redirect_uri']
        
        # Remove /oauth/callback/ suffix if present - Streamlit handles callbacks in main app
        if '/oauth/callback/' in redirect_uri:
            redirect_uri = redirect_uri.split('/oauth/callback/')[0]
        
        if self.provider == 'google':
            return f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile&state={state}"
        elif self.provider == 'github':
            return f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=user:email&state={state}"
        elif self.provider == 'microsoft':
            return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid email profile&state={state}"
        
        return ""
    
    
    def _exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        import requests
        
        provider_config = self.providers[self.provider]
        
        if self.provider == 'google':
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': provider_config['client_id'],
                'client_secret': provider_config['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': provider_config['redirect_uri'],
            }
        elif self.provider == 'github':
            token_url = "https://github.com/login/oauth/access_token"
            data = {
                'client_id': provider_config['client_id'],
                'client_secret': provider_config['client_secret'],
                'code': code,
                'redirect_uri': provider_config['redirect_uri'],
            }
        elif self.provider == 'microsoft':
            token_url = f"https://login.microsoftonline.com/{self.config.microsoft_tenant_id}/oauth2/v2.0/token"
            data = {
                'client_id': provider_config['client_id'],
                'client_secret': provider_config['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': provider_config['redirect_uri'],
            }
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        headers = {'Accept': 'application/json'}
        
        response = requests.post(token_url, data=data, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to exchange code for token: {response.text}")
        
        return response.json()
    
    def _get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile from OAuth provider."""
        import requests
        
        if self.provider == 'google':
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(userinfo_url, headers=headers)
        elif self.provider == 'github':
            userinfo_url = "https://api.github.com/user"
            headers = {'Authorization': f'token {access_token}'}
            response = requests.get(userinfo_url, headers=headers)
        elif self.provider == 'microsoft':
            userinfo_url = "https://graph.microsoft.com/v1.0/me"
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(userinfo_url, headers=headers)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        if response.status_code != 200:
            logger.error(f"Failed to get user profile: {response.status_code} - {response.text}")
            raise Exception(f"Failed to get user profile: {response.text}")
        
        profile = response.json()
        
        if self.provider == 'github':
            if not profile.get('email'):
                email_response = requests.get('https://api.github.com/user/emails', headers=headers)
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next((e for e in emails if e.get('primary')), None)
                    if primary_email:
                        profile['email'] = primary_email.get('email')
        
        return profile
    
    def _normalize_profile(self, profile: Dict[str, Any], access_token: str = None) -> Dict[str, Any]:
        """Normalize profile data across providers."""
        if self.provider == 'google':
            return {
                'email': profile.get('email'),
                'name': profile.get('name'),
                'oauth_id': profile.get('id'),
                'avatar_url': profile.get('picture'),
                'locale': profile.get('locale'),
            }
        elif self.provider == 'github':
            return {
                'email': profile.get('email'),
                'name': profile.get('name') or profile.get('login'),
                'oauth_id': str(profile.get('id')),
                'avatar_url': profile.get('avatar_url'),
                'locale': None,
            }
        elif self.provider == 'microsoft':
            return {
                'email': profile.get('mail') or profile.get('userPrincipalName'),
                'name': profile.get('displayName'),
                'oauth_id': profile.get('id'),
                'avatar_url': None,
                'locale': None,
            }
        return {}

    @staticmethod
    def create_state(provider: str) -> str:
        """Create signed OAuth state that includes provider and nonce."""
        provider_normalized = str(provider).lower().strip()
        nonce = secrets.token_urlsafe(24)
        payload = f"{provider_normalized}:{nonce}"
        signature = OAuthHandler._sign_state_payload(payload)
        return f"{payload}:{signature}"

    @staticmethod
    def extract_provider_from_state(state: str) -> Optional[str]:
        """Extract provider from signed state payload."""
        if not state or ':' not in str(state):
            return None

        provider = str(state).split(':', 1)[0].strip().lower()
        if provider in {'google', 'github', 'microsoft'}:
            return provider
        return None

    @staticmethod
    def verify_state_signature(state: str) -> bool:
        """Verify HMAC signature for state payload."""
        parts = str(state).split(':') if state else []
        if len(parts) != 3:
            return False

        provider, nonce, received_sig = parts
        if provider not in {'google', 'github', 'microsoft'} or not nonce or not received_sig:
            return False

        payload = f"{provider}:{nonce}"
        expected_sig = OAuthHandler._sign_state_payload(payload)
        return hmac.compare_digest(received_sig, expected_sig)

    @staticmethod
    def _sign_state_payload(payload: str) -> str:
        """Sign OAuth state payload using NIKLAUS_SECRET_KEY (from config).

        Falls back to a derived key from OAuth secrets if the explicit key is
        not set — but that is considered insecure and logged as a warning.
        """
        config = OAuthConfig()
        # Use the dedicated application secret key (NIKLAUS_SECRET_KEY)
        secret_seed = config.secret_key
        digest = hmac.new(secret_seed.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return digest[:24]

    @staticmethod
    def validate_state(received_state: str, expected_state: str) -> bool:
        """Validate OAuth state using constant-time comparison."""
        if not received_state or not expected_state:
            return False
        return hmac.compare_digest(str(received_state), str(expected_state))
    
    def handle_callback(self, code: str, state: str, expected_state: Optional[str] = None) -> Optional[User]:
        """Handle OAuth callback after authorization."""
        try:
            if expected_state is not None and not self.validate_state(state, expected_state):
                logger.warning("OAuth state validation failed")
                return None

            token_data = self._exchange_code_for_token(code)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')

            if not access_token:
                logger.error("No access token in response")
                return None

            profile = self._get_user_profile(access_token)
            normalized = self._normalize_profile(profile, access_token)

            if not normalized.get('email'):
                logger.error("No email in user profile")
                return None

            user = OAuthHandler.create_user_from_oauth(
                email=normalized['email'],
                name=normalized.get('name', normalized['email'].split('@')[0]),
                provider=self.provider,
                oauth_id=normalized.get('oauth_id'),
                avatar_url=normalized.get('avatar_url'),
                access_token=access_token,
                refresh_token=refresh_token,
            )

            logger.info(f"OAuth login successful for {normalized['email']} via {self.provider}")
            return user

        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return None
    
    @staticmethod
    def create_user_from_oauth(
        email: str,
        name: str,
        provider: str,
        oauth_id: str = None,
        avatar_url: str = None,
        access_token: str = None,
        refresh_token: str = None,
    ) -> User:
        """Create or update a user from OAuth profile data.

        Access and refresh tokens are encrypted at rest using Fernet before
        being persisted to the database.
        """
        # Encrypt tokens before storing
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token)

        db = get_session()
        try:
            user_repo = UserRepository(db)

            user = user_repo.find_by_email(email)

            if user:
                user.name = name
                user.avatar_url = avatar_url
                user.oauth_provider = provider
                user.oauth_id = oauth_id
                user.oauth_access_token = encrypted_access
                user.oauth_refresh_token = encrypted_refresh
                user.last_login_at = utcnow()
                user.is_active = True
                db.commit()
                db.refresh(user)
                logger.info(f"Updated existing user: {email}")
            else:
                role = 'admin' if OAuthConfig().is_admin(email) else 'user'
                user = user_repo.create(
                    email=email,
                    name=name,
                    role=role,
                    oauth_provider=provider,
                    oauth_id=oauth_id,
                    avatar_url=avatar_url,
                    oauth_access_token=encrypted_access,
                    oauth_refresh_token=encrypted_refresh,
                    is_active=True,
                    is_verified=True,
                )
                logger.info(f"Created new user: {email} (role: {role})")

            return user
        finally:
            db.close()
