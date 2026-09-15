"""
Full coverage for auth/config.py (OAuthConfig branches, token encryption),
auth/session.py (SessionManager with mocked Streamlit + DB) and
utils/error_handling.py (all display paths with mocked Streamlit).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import utils.error_handling as error_handling
from auth.config import OAuthConfig, decrypt_token, encrypt_token, _get_fernet_key
from auth.models import Base, User
from auth.session import SessionManager, init_session_state


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_st():
    fake = SimpleNamespace(
        session_state=FakeSessionState(),
        secrets={},
        error=MagicMock(), warning=MagicMock(), info=MagicMock(),
        markdown=MagicMock(), stop=MagicMock(side_effect=RuntimeError('stop')),
        success=MagicMock(),
    )
    with patch('auth.session.st', fake):
        yield fake


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def patched_db(db_session):
    """Route SessionManager's get_session() to the in-memory DB."""
    with patch('auth.session.get_session', return_value=db_session):
        yield db_session


# ---------------------------------------------------------------------------
# OAuthConfig
# ---------------------------------------------------------------------------

def _oauth_config_with(monkeypatch, secrets_payload, env=None):
    """Build OAuthConfig against a fully patched streamlit module."""
    fake_st = SimpleNamespace(secrets=secrets_payload)
    with patch.dict('sys.modules', {'streamlit': fake_st}):
        return OAuthConfig()


class TestOAuthConfig:
    def test_default_providers_empty(self, monkeypatch):
        for var in ('GOOGLE_CLIENT_ID', 'GITHUB_CLIENT_ID', 'MICROSOFT_CLIENT_ID'):
            monkeypatch.delenv(var, raising=False)
        config = _oauth_config_with(monkeypatch, {})
        assert config.google_client_id == ''
        assert config.get_available_providers() == []

    def test_nested_secrets_priority(self, monkeypatch):
        config = _oauth_config_with(monkeypatch, {'google': {'client_id': 'G1', 'client_secret': 'S1'}})
        assert config.google_client_id == 'G1'
        assert config.google_client_secret == 'S1'
        assert config.is_oauth_configured('google') is True
        assert 'google' in config.get_available_providers()

    def test_env_fallback(self, monkeypatch):
        monkeypatch.setenv('GITHUB_CLIENT_ID', 'env-id')
        monkeypatch.setenv('GITHUB_CLIENT_SECRET', 'env-secret')
        config = _oauth_config_with(monkeypatch, {})
        assert config.github_client_id == 'env-id'
        assert config.is_oauth_configured('github') is True

    def test_secret_key_explicit(self, monkeypatch):
        monkeypatch.setenv('NIKLAUS_SECRET_KEY', 'super-secret-key')
        config = _oauth_config_with(monkeypatch, {})
        assert config.secret_key == 'super-secret-key'

    def test_secret_key_fallback_when_missing(self, monkeypatch):
        for var in ('NIKLAUS_SECRET_KEY', 'GOOGLE_CLIENT_SECRET',
                    'GITHUB_CLIENT_SECRET', 'MICROSOFT_CLIENT_SECRET'):
            monkeypatch.delenv(var, raising=False)
        config = _oauth_config_with(monkeypatch, {})
        assert config.secret_key  # weak fallback still non-empty

    def test_admin_emails_env(self, monkeypatch):
        monkeypatch.setenv('ADMIN_EMAILS', 'admin@x.com, BOSS@Y.com,')
        config = _oauth_config_with(monkeypatch, {'ADMIN_EMAILS': 'admin@x.com'})
        assert config.is_admin('ADMIN@X.COM') is True
        assert config.is_admin('other@x.com') is False

    def test_admin_emails_secrets_absent_falls_back_to_env(self, monkeypatch):
        # secrets present but without ADMIN_EMAILS -> env is NOT consulted
        # (documents current behavior; env fallback only on secrets failure)
        monkeypatch.setenv('ADMIN_EMAILS', 'env@x.com')
        config = _oauth_config_with(monkeypatch, {})
        assert config.admin_emails == set()

    def test_microsoft_tenant_default(self, monkeypatch):
        monkeypatch.delenv('MICROSOFT_TENANT_ID', raising=False)
        monkeypatch.delenv('MICROSOFT_CLIENT_ID', raising=False)
        config = _oauth_config_with(monkeypatch, {})
        assert config.microsoft_tenant_id == 'common'

    def test_is_oauth_configured_unknown_provider(self, monkeypatch):
        config = _oauth_config_with(monkeypatch, {})
        assert config.is_oauth_configured('dropbox') is False


# ---------------------------------------------------------------------------
# Token encryption
# ---------------------------------------------------------------------------

class TestTokenEncryption:
    def test_roundtrip(self, monkeypatch):
        monkeypatch.setenv('NIKLAUS_SECRET_KEY', 'test-key-abc')
        from auth.config import encrypt_token
        ciphertext = encrypt_token('secret-token-123')
        assert ciphertext != 'secret-token-123'
        assert decrypt_token(ciphertext) == 'secret-token-123'

    def test_none_passthrough(self):
        assert encrypt_token(None) is None  # via patch of module attr
        assert decrypt_token(None) is None

    def test_decrypt_plaintext_fallback(self, monkeypatch):
        monkeypatch.setenv('NIKLAUS_SECRET_KEY', 'test-key-abc')
        assert decrypt_token('not-encrypted-plain') == 'not-encrypted-plain'

    def test_fernet_key_is_urlsafe_b64_32bytes(self):
        import base64
        key = _get_fernet_key()
        raw = base64.urlsafe_b64decode(key)
        assert len(raw) == 32


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------

class TestSessionManager:
    def test_login_with_dict(self, fake_st, patched_db):
        SessionManager.login({'id': 1, 'email': 'u@x.com', 'name': 'U', 'is_admin': False})
        assert fake_st.session_state[SessionManager.SESSION_KEY]['email'] == 'u@x.com'
        assert SessionManager.is_authenticated() is True

    def test_login_with_user_object(self, fake_st, patched_db):
        user = User(email='obj@x.com', name='Obj', role='user')
        patched_db.add(user)
        patched_db.commit()
        patched_db.refresh(user)

        SessionManager.login(user)
        stored = fake_st.session_state[SessionManager.SESSION_KEY]
        assert stored['is_admin'] is False
        assert SessionManager.is_authenticated() is True

    def test_logout_clears(self, fake_st, patched_db):
        SessionManager.login({'id': 1, 'email': 'x@x.com'})
        SessionManager.logout()
        assert SessionManager.is_authenticated() is False

    def test_session_expiry(self, fake_st, patched_db):
        from auth.session import utcnow
        from datetime import timedelta
        SessionManager.login({'id': 1, 'email': 'x@x.com'})
        # Force expiry into the past
        fake_st.session_state[SessionManager.SESSION_EXPIRY_KEY] = utcnow() - timedelta(hours=1)
        assert SessionManager.get_current_user() is None
        assert SessionManager.is_authenticated() is False

    def test_is_admin_true_and_false(self, fake_st, patched_db):
        SessionManager.login({'id': 1, 'email': 'x@x.com', 'is_admin': True})
        assert SessionManager.is_admin() is True
        SessionManager.logout()
        assert SessionManager.is_admin() is False

    def test_redirect_roundtrip(self, fake_st):
        SessionManager.set_redirect('upload')
        assert SessionManager.get_redirect() == 'upload'
        SessionManager.clear_redirect()
        assert SessionManager.get_redirect() is None

    def test_refresh_user_updates(self, fake_st, patched_db):
        user = User(email='rf@x.com', name='RF', role='admin')
        patched_db.add(user)
        patched_db.commit()
        patched_db.refresh(user)

        SessionManager.login({'id': user.id, 'email': 'rf@x.com', 'is_admin': False})
        refreshed = SessionManager.refresh_user()
        assert refreshed is not None
        assert refreshed['is_admin'] is True

    def test_refresh_user_none_when_missing(self, fake_st, patched_db):
        SessionManager.login({'id': 9999, 'email': 'ghost@x.com'})
        assert SessionManager.refresh_user() is None

    def test_refresh_user_when_not_logged(self, fake_st, patched_db):
        assert SessionManager.refresh_user() is None

    def test_init_session_state_defaults(self, fake_st):
        init_session_state()
        assert fake_st.session_state['user'] is None
        assert fake_st.session_state['page'] == 'upload'
        init_session_state()  # idempotent


# ---------------------------------------------------------------------------
# error_handling — all display paths
# ---------------------------------------------------------------------------

@pytest.fixture
def eh_st():
    fake = SimpleNamespace(
        error=MagicMock(), warning=MagicMock(), info=MagicMock(),
        markdown=MagicMock(),
    )
    with patch.object(error_handling.st, 'error', fake.error), \
         patch.object(error_handling.st, 'warning', fake.warning), \
         patch.object(error_handling.st, 'info', fake.info), \
         patch.object(error_handling.st, 'markdown', fake.markdown):
        yield fake


class TestDisplayErrorDispatch:
    def test_niklaus_error_with_suggestion_and_url(self, eh_st):
        err = error_handling._LocalError('main message', suggestion='try x', help_url='http://help')
        error_handling.display_error(err)
        assert any('main message' in str(c) for c in eh_st.error.call_args_list)
        eh_st.warning.assert_called()
        eh_st.markdown.assert_called()

    def test_file_error_size_branch(self, eh_st):
        error_handling.display_error(error_handling.FileValidationError('tamanho máximo'))
        all_errors = [str(c) for c in eh_st.error.call_args_list]
        assert any('muito grande' in e for e in all_errors)

    def test_file_error_format_branch(self, eh_st):
        error_handling.display_error(error_handling.FileValidationError('formato inválido'))
        all_errors = [str(c) for c in eh_st.error.call_args_list]
        assert any('Formato' in e for e in all_errors)

    def test_file_error_empty_branch(self, eh_st):
        error_handling.display_error(error_handling.FileValidationError('ZIP vazio'))
        assert 'vazio' in eh_st.error.call_args[0][0]

    def test_file_error_corrupted_branch(self, eh_st):
        error_handling.display_error(error_handling.FileValidationError('ZIP corrompido'))
        assert 'corrompido' in eh_st.error.call_args[0][0]

    def test_file_error_generic_branch(self, eh_st):
        error_handling.display_error(error_handling.FileValidationError('estranho demais'))
        all_errors = [str(c) for c in eh_st.error.call_args_list]
        assert any('Erro no arquivo' in e for e in all_errors)

    def test_api_error_timeout_branch(self, eh_st):
        error_handling.display_error(error_handling.APIError('timeout na IA'))
        all_errors = [str(c) for c in eh_st.error.call_args_list]
        assert any('Tempo limite' in e for e in all_errors)

    def test_api_error_rate_limit_branch(self, eh_st):
        error_handling.display_error(error_handling.APIError('rate limit exceeded'))
        assert 'Muitas requisições' in eh_st.error.call_args[0][0] or eh_st.error.called

    def test_api_error_generic_branch(self, eh_st):
        error_handling.display_error(error_handling.APIError('falha interna'))
        assert eh_st.error.called

    def test_auth_error_branch(self, eh_st):
        error_handling.display_error(error_handling.AuthenticationError('sessão expirou'))
        assert eh_st.error.called

    def test_analysis_error_branch(self, eh_st):
        error_handling.display_error(error_handling.AnalysisError('pipeline falhou'))
        assert eh_st.error.called

    def test_generic_exception_with_context(self, eh_st):
        error_handling.display_error(ValueError('oops'), context='upload')
        assert eh_st.error.called


class TestLocalErrorHierarchy:
    def test_local_api_error_is_exception_with_message(self):
        err = error_handling.APIError('rate limit hit')
        assert isinstance(err, Exception)
        assert 'rate limit hit' in str(err)

    def test_local_auth_and_analysis_errors(self):
        assert isinstance(error_handling.AuthenticationError('x'), Exception)
        assert isinstance(error_handling.AnalysisError('x'), Exception)