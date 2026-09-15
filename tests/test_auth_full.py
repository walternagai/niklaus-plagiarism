"""
Deep auth tests: OAuth handler flow, database manager, session manager
and route decorators.

HTTP and Streamlit dependencies are mocked.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.database import DatabaseManager, get_db_manager
from auth.decorators import guest_required, require_admin
from auth.models import Base, User
from auth.oauth import OAuthHandler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class FakeStopException(Exception):
    """Streamlit's st.stop() raises to halt script execution."""


class FakeSessionState(dict):
    """Minimal st.session_state double supporting attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_st():
    """Patch streamlit inside auth.decorators with a controllable fake.

    ``stop`` raises (like the real Streamlit) so decorated functions
    actually halt before touching missing state.
    """
    fake = SimpleNamespace(
        session_state=FakeSessionState(),
        warning=MagicMock(),
        error=MagicMock(),
        info=MagicMock(),
        stop=MagicMock(side_effect=FakeStopException('stopped')),
        button=MagicMock(return_value=False),
        switch_page=MagicMock(),
    )
    with patch('auth.decorators.st', fake):
        yield fake


# ---------------------------------------------------------------------------
# OAuthHandler — state/signature (pure logic)
# ---------------------------------------------------------------------------

class TestOAuthState:
    def test_create_state_includes_provider(self):
        state = OAuthHandler.create_state('GitHub')
        assert state.startswith('github:')

    def test_extract_provider(self):
        assert OAuthHandler.extract_provider_from_state('github:abc:sig') == 'github'
        assert OAuthHandler.extract_provider_from_state('evil:abc:sig') is None
        assert OAuthHandler.extract_provider_from_state('') is None
        assert OAuthHandler.extract_provider_from_state('no-separator') is None

    def test_verify_signature_roundtrip_and_tamper(self):
        state = OAuthHandler.create_state('google')
        assert OAuthHandler.verify_state_signature(state) is True
        parts = state.split(':')
        tampered = f"google:{parts[1]}:{'0' * len(parts[2])}"
        assert OAuthHandler.verify_state_signature(tampered) is False
        assert OAuthHandler.verify_state_signature('google:nonce') is False
        assert OAuthHandler.verify_state_signature('') is False

    def test_validate_state(self):
        assert OAuthHandler.validate_state('abc', 'abc') is True
        assert OAuthHandler.validate_state('abc', 'xyz') is False
        assert OAuthHandler.validate_state('', 'abc') is False
        assert OAuthHandler.validate_state('abc', '') is False


# ---------------------------------------------------------------------------
# OAuthHandler — authorization URL
# ---------------------------------------------------------------------------

class TestOAuthURL:
    def test_google_url_contains_params(self):
        url = OAuthHandler('google').get_authorization_url(state='S1')
        assert 'accounts.google.com' in url
        assert 'client_id=' in url and 'state=S1' in url

    def test_github_url(self):
        url = OAuthHandler('github').get_authorization_url('S2')
        assert 'github.com/login/oauth/authorize' in url

    def test_microsoft_url(self):
        url = OAuthHandler('microsoft').get_authorization_url('S3')
        assert 'login.microsoftonline.com' in url

    def test_callback_suffix_stripped(self):
        handler = OAuthHandler('google')
        handler.providers['google']['redirect_uri'] = 'http://x/oauth/callback/google'
        url = handler.get_authorization_url('S')
        assert '/oauth/callback/' not in url

    def test_random_state_when_missing(self):
        handler = OAuthHandler('google')
        url1 = handler.get_authorization_url()
        url2 = handler.get_authorization_url()
        assert url1 != url2  # random state each call


# ---------------------------------------------------------------------------
# OAuthHandler — token exchange and profile (mocked HTTP)
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture
def oauth_handler():
    return OAuthHandler('github')


class TestOAuthExchange:
    def test_exchange_success(self, oauth_handler, monkeypatch):
        def fake_post(url, **kwargs):
            assert 'github.com/login/oauth/access_token' in url
            return FakeResponse(200, {'access_token': 'at-123', 'refresh_token': 'rt-456'})

        monkeypatch.setattr('requests.post', fake_post)
        data = oauth_handler._exchange_code_for_token('CODE')
        assert data['access_token'] == 'at-123'

    def test_exchange_http_error_raises(self, oauth_handler, monkeypatch):
        monkeypatch.setattr('requests.post', lambda url, **kw: FakeResponse(400, {}))
        with pytest.raises(Exception, match='Failed to exchange'):
            oauth_handler._exchange_code_for_token('BAD')

    def test_profile_github(self, oauth_handler, monkeypatch):
        def fake_get(url, **kwargs):
            if '/user/emails' in url:
                return FakeResponse(200, [{'email': 'a@x.com', 'primary': False},
                                          {'email': 'primary@x.com', 'primary': True}])
            return FakeResponse(200, {'id': 9, 'login': 'octo', 'avatar_url': 'http://av'})

        monkeypatch.setattr('requests.get', fake_get)
        profile = oauth_handler._get_user_profile('TOKEN')
        assert profile['email'] == 'primary@x.com'

    def test_profile_http_error_raises(self, oauth_handler, monkeypatch):
        monkeypatch.setattr('requests.get', lambda url, **kw: FakeResponse(500, {}))
        with pytest.raises(Exception, match='Failed to get user profile'):
            oauth_handler._get_user_profile('TOKEN')


class TestNormalizeProfile:
    def test_github_falls_back_to_login(self, oauth_handler):
        normalized = oauth_handler._normalize_profile({'id': 5, 'login': 'octo'})
        assert normalized['name'] == 'octo'
        assert normalized['oauth_id'] == '5'

    def test_google_profile(self):
        handler = OAuthHandler('google')
        normalized = handler._normalize_profile(
            {'email': 'g@x.com', 'name': 'G', 'id': '1', 'locale': 'pt-BR', 'picture': 'u'})
        assert normalized['locale'] == 'pt-BR'
        assert normalized['avatar_url'] == 'u'

    def test_microsoft_profile_mail_fallback(self):
        handler = OAuthHandler('microsoft')
        normalized = handler._normalize_profile({'userPrincipalName': 'm@x.com', 'displayName': 'M'})
        assert normalized['email'] == 'm@x.com'
        assert normalized['avatar_url'] is None


# ---------------------------------------------------------------------------
# handle_callback (mocked HTTP + DB)
# ---------------------------------------------------------------------------

class TestHandleCallback:
    def test_state_mismatch_returns_none(self, oauth_handler):
        assert oauth_handler.handle_callback('code', 'received', expected_state='other') is None

    def test_missing_access_token_returns_none(self, oauth_handler, monkeypatch):
        monkeypatch.setattr('requests.post', lambda url, **kw: FakeResponse(200, {'error': 'x'}))
        assert oauth_handler.handle_callback('code', 'state') is None

    def test_profile_without_email_returns_none(self, oauth_handler, monkeypatch):
        monkeypatch.setattr('requests.post', lambda url, **kw: FakeResponse(200, {'access_token': 'T'}))
        monkeypatch.setattr('requests.get', lambda url, **kw: FakeResponse(200, {'id': 1}))
        assert oauth_handler.handle_callback('code', 'state') is None

    def test_exception_path_returns_none(self, oauth_handler, monkeypatch):
        def boom(url, **kw):
            raise ConnectionError('network down')

        monkeypatch.setattr('requests.post', boom)
        assert oauth_handler.handle_callback('code', 'state') is None


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class TestDatabaseManager:
    def test_init_sqlite_memory(self, tmp_path, monkeypatch):
        monkeypatch.delenv('DATABASE_URL', raising=False)
        manager = DatabaseManager('sqlite:///:memory:')
        session = manager.get_session()
        assert session is not None
        session.close()

    def test_create_and_drop_tables(self, tmp_path):
        manager = DatabaseManager(f'sqlite:///{tmp_path}/t.db')
        manager.create_tables()
        manager.drop_tables()

    def test_session_scope_commits(self, tmp_path):
        manager = DatabaseManager(f'sqlite:///{tmp_path}/s.db')
        manager.create_tables()
        with manager.session_scope() as session:
            session.add(User(email='scope@x.com', name='S'))
        with manager.get_session() as check:
            assert check.query(User).filter_by(email='scope@x.com').first() is not None

    def test_session_scope_rolls_back_on_error(self, tmp_path):
        manager = DatabaseManager(f'sqlite:///{tmp_path}/r.db')
        with pytest.raises(ValueError):
            with manager.session_scope() as session:
                session.add(User(email='rollback@x.com', name='R'))
                raise ValueError('fail')
        assert manager.engine is not None

    def test_singleton_get_db_manager(self, monkeypatch):
        monkeypatch.delenv('DATABASE_URL', raising=False)
        assert get_db_manager() is get_db_manager()

    def test_session_scope_function(self, tmp_path, monkeypatch):
        monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path}/f.db')
        from importlib import reload
        import auth.database as dbmod
        reload(dbmod)
        dbmod.get_db_manager().create_tables()
        with dbmod.session_scope() as session:
            session.add(User(email='fn@x.com', name='F'))
        with dbmod.get_session() as check:
            assert check.query(User).filter_by(email='fn@x.com').first() is not None


# ---------------------------------------------------------------------------
# Decorators (mocked streamlit)
# ---------------------------------------------------------------------------

def _stub(): return 'ok'


class TestRequireAdmin:
    def test_blocks_anonymous(self, fake_st):
        decorated = require_admin(lambda: 'payload')
        with pytest.raises(FakeStopException):
            decorated()
        fake_st.warning.assert_called()

    def test_blocks_non_admin(self, fake_st):
        fake_st.session_state['user'] = {'is_admin': False, 'email': 'u@x.com'}
        decorated = require_admin(lambda: 'payload')
        with pytest.raises(FakeStopException):
            decorated()
        fake_st.error.assert_called()

    def test_passes_admin(self, fake_st):
        fake_st.session_state['user'] = {'is_admin': True, 'email': 'a@x.com'}
        assert require_admin(lambda: 'payload')() == 'payload'

    def test_object_user_non_admin_blocked(self, fake_st):
        fake_st.session_state['user'] = SimpleNamespace(is_admin=False, email='o@x.com')
        decorated = require_admin(lambda: 'payload')
        with pytest.raises(FakeStopException):
            decorated()


class TestGuestRequired:
    def test_passes_when_anonymous(self, fake_st):
        assert guest_required(lambda: 'page')() == 'page'

    def test_stops_when_logged(self, fake_st):
        fake_st.session_state['user'] = {'name': 'Maria'}
        decorated = guest_required(lambda: 'page')
        with pytest.raises(FakeStopException):
            decorated()
        fake_st.info.assert_called()