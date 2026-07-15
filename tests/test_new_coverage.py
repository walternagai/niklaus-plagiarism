"""
New test coverage for areas previously untested:
  - auth/session.py  (SessionManager logic)
  - auth/repository.py  (SubmissionRepository with in-memory SQLite)
  - ui/tabs/history.py  (_normalize_submission_analysis)
  - core/llm_client.py  (MaritacaClient prompt building, mocked API)
  - auth/config.py  (encrypt_token / decrypt_token)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# auth/config.py — token encryption helpers
# ---------------------------------------------------------------------------

class TestTokenEncryption:
    """Test Fernet token encryption/decryption roundtrip."""

    def test_encrypt_decrypt_roundtrip(self):
        from auth.config import encrypt_token, decrypt_token
        plaintext = "ya29.test-access-token-value"
        ciphertext = encrypt_token(plaintext)
        assert ciphertext is not None
        assert ciphertext != plaintext  # must be encrypted
        assert decrypt_token(ciphertext) == plaintext

    def test_encrypt_none_returns_none(self):
        from auth.config import encrypt_token
        assert encrypt_token(None) is None

    def test_decrypt_none_returns_none(self):
        from auth.config import decrypt_token
        assert decrypt_token(None) is None

    def test_decrypt_plaintext_fallback(self):
        """decrypt_token should return the original string if it was not encrypted."""
        from auth.config import decrypt_token
        # A plaintext token (stored before encryption was introduced) should be
        # returned as-is by the fallback path.
        plain = "legacy-plaintext-token"
        result = decrypt_token(plain)
        assert result == plain

    def test_encrypt_empty_string_returns_empty(self):
        from auth.config import encrypt_token
        assert encrypt_token("") is None or encrypt_token("") == ""


# ---------------------------------------------------------------------------
# auth/session.py — SessionManager
# ---------------------------------------------------------------------------

class TestSessionManager:
    """Test SessionManager using mocked Streamlit session state."""

    @pytest.fixture(autouse=True)
    def mock_st(self):
        """Provide a clean fake session_state for each test."""
        state = {}

        class FakeState(dict):
            def clear(self):
                self.update({k: None for k in list(self.keys())})
                for k in list(self.keys()):
                    del self[k]

        fake_state = FakeState()

        with patch("auth.session.st") as mock_st, \
             patch("auth.session.get_session") as mock_db:
            mock_st.session_state = fake_state
            # Mock the DB call inside login()
            mock_repo = MagicMock()
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_repo)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            # Make closing() work with the session mock
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            yield mock_st, fake_state

    def test_login_sets_user(self, mock_st):
        from auth.session import SessionManager
        st_mock, state = mock_st
        user_dict = {'id': 1, 'email': 'a@b.com', 'name': 'Alice', 'role': 'user'}
        SessionManager.login(user_dict)
        assert state.get('user') == user_dict

    def test_logout_clears_session(self, mock_st):
        from auth.session import SessionManager
        st_mock, state = mock_st
        state['user'] = {'id': 1}
        state['something_else'] = True
        SessionManager.logout()
        assert len(state) == 0

    def test_is_authenticated_false_when_empty(self, mock_st):
        from auth.session import SessionManager
        _, state = mock_st
        # No user in state
        assert SessionManager.is_authenticated() is False

    def test_get_current_user_returns_none_when_expired(self, mock_st):
        from auth.session import SessionManager
        _, state = mock_st
        state['user'] = {'id': 1, 'email': 'x@y.com'}
        # Set expiry in the past
        from datetime import timezone
        state['session_expires'] = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        # Session is expired — should log out and return None
        result = SessionManager.get_current_user()
        assert result is None


# ---------------------------------------------------------------------------
# auth/repository.py — SubmissionRepository with in-memory SQLite
# ---------------------------------------------------------------------------

class TestSubmissionRepository:
    """Integration tests using an in-memory SQLite database."""

    @pytest.fixture
    def db_session(self):
        """Set up an in-memory SQLite DB with tables created."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from auth.models import Base

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def user(self, db_session):
        from auth.models import User
        u = User(email="test@example.com", name="Test User", role="user")
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u

    def test_create_submission(self, db_session, user):
        from auth.repository import SubmissionRepository
        repo = SubmissionRepository(db_session)
        sub = repo.create(
            user_id=user.id,
            filename="test.zip",
            language="python",
            threshold=0.7,
            files_count=3,
            suspicious_pairs_count=1,
            status="completed",
        )
        assert sub.id is not None
        assert sub.user_id == user.id
        assert sub.filename == "test.zip"

    def test_find_by_user(self, db_session, user):
        from auth.repository import SubmissionRepository
        repo = SubmissionRepository(db_session)
        repo.create(user_id=user.id, filename="a.zip", language="python", status="completed")
        repo.create(user_id=user.id, filename="b.zip", language="java", status="completed")

        results = repo.find_by_user(user.id, limit=10, use_cache=False)
        assert len(results) == 2

    def test_find_by_user_status_filter(self, db_session, user):
        from auth.repository import SubmissionRepository
        repo = SubmissionRepository(db_session)
        repo.create(user_id=user.id, filename="a.zip", language="python", status="completed")
        repo.create(user_id=user.id, filename="b.zip", language="python", status="error")

        completed = repo.find_by_user(user.id, status="completed", use_cache=False)
        assert all(s.status == "completed" for s in completed)
        assert len(completed) == 1

    def test_delete_all_by_user(self, db_session, user):
        from auth.repository import SubmissionRepository
        repo = SubmissionRepository(db_session)
        repo.create(user_id=user.id, filename="a.zip", language="python", status="completed")
        repo.create(user_id=user.id, filename="b.zip", language="python", status="completed")

        count = repo.delete_all_by_user(user.id)
        assert count == 2
        remaining = repo.find_by_user(user.id, use_cache=False)
        assert len(remaining) == 0

    def test_user_counters_incremented_on_create(self, db_session, user):
        from auth.repository import SubmissionRepository
        from auth.models import User
        repo = SubmissionRepository(db_session)
        repo.create(
            user_id=user.id,
            filename="x.zip",
            language="python",
            suspicious_pairs_count=2,
            status="completed",
        )
        db_session.refresh(user)
        assert user.submissions_count == 1
        assert user.total_analyses == 1
        assert user.total_suspicious_pairs == 2


# ---------------------------------------------------------------------------
# ui/tabs/history.py — _normalize_submission_analysis (pure Python, no UI)
# ---------------------------------------------------------------------------

class TestNormalizeSubmissionAnalysis:
    """Test the schema-normalization helper in isolation."""

    def _make_submission(self, **kwargs):
        """Create a minimal mock submission object."""
        defaults = {
            'threshold': 0.7,
            'language': 'python',
            'analysis_time_seconds': 1.5,
            'average_similarity': 0.6,
            'max_similarity': 0.9,
        }
        defaults.update(kwargs)
        sub = MagicMock()
        for k, v in defaults.items():
            setattr(sub, k, v)
        return sub

    def _normalize(self, submission, data):
        from ui.tabs.history import _normalize_submission_analysis
        return _normalize_submission_analysis(submission, data)

    def test_returns_none_for_none_data(self):
        sub = self._make_submission()
        assert self._normalize(sub, None) is None

    def test_returns_none_for_invalid_string(self):
        sub = self._make_submission()
        assert self._normalize(sub, "not json") is None

    def test_parses_json_string(self):
        import json
        sub = self._make_submission()
        data = json.dumps({'files': ['a.py', 'b.py'], 'pairwise_results': []})
        result = self._normalize(sub, data)
        assert result is not None
        assert result['files'] == ['a.py', 'b.py']

    def test_fills_missing_average_similarity(self):
        sub = self._make_submission(average_similarity=0.55)
        data = {'files': ['a.py'], 'pairwise_results': []}
        result = self._normalize(sub, data)
        assert result['average_similarity'] == 0.55

    def test_preserves_schema_v2(self):
        sub = self._make_submission()
        data = {
            'schema_version': 2,
            'files': ['x.py', 'y.py'],
            'pairwise_results': [],
            'suspicious_pairs': [],
        }
        result = self._normalize(sub, data)
        assert result['schema_version'] == 2

    def test_builds_suspicious_pairs_from_pairwise(self):
        sub = self._make_submission(threshold=0.7)
        data = {
            'files': ['a.py', 'b.py'],
            'pairwise_results': [
                {'file1': 'a.py', 'file2': 'b.py', 'similarity': 0.85, 'is_suspicious': True}
            ],
        }
        result = self._normalize(sub, data)
        assert len(result['suspicious_pairs']) == 1
        assert result['suspicious_pairs'][0][2] == 0.85


# ---------------------------------------------------------------------------
# core/llm_client.py — MaritacaClient (mocked HTTP)
# ---------------------------------------------------------------------------

class TestMaritacaClient:
    """Test MaritacaClient prompt generation and mocked API calls."""

    def test_build_prompt_contains_code(self):
        from core.llm_client import MaritacaClient
        client = MaritacaClient(api_key="fake-key")
        prompt = client._build_user_prompt(
            code1="def foo(): pass",
            code2="def bar(): pass",
            file1="a.py",
            file2="b.py",
            textual_similarity=0.8,
            ast_similarity=0.75,
            plagiarism_type="RENOMEACAO_VARIAVEIS",
            confidence=0.9,
        )
        assert "a.py" in prompt
        assert "b.py" in prompt
        assert "def foo(): pass" in prompt
        assert "def bar(): pass" in prompt

    def test_analyze_plagiarism_uses_openai_client(self):
        """analyze_plagiarism should call the OpenAI-compatible API and return a string."""
        from core.llm_client import MaritacaClient

        client = MaritacaClient(api_key="fake-key")

        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "Análise: plágio detectado."

        with patch.object(client.client.chat.completions, "create", return_value=fake_response):
            result = client.analyze_plagiarism(
                code1="def foo(): return 1",
                code2="def bar(): return 1",
                file1="a.py",
                file2="b.py",
                textual_similarity=0.95,
                ast_similarity=0.95,
                plagiarism_type="COPIA_DIRETA",
                confidence=0.99,
            )
        assert "plágio" in result.lower() or isinstance(result, str)

    def test_analyze_plagiarism_handles_api_error(self):
        """analyze_plagiarism should raise MaritacaAPIError on API failure."""
        from core.llm_client import MaritacaClient
        from utils.exceptions import MaritacaAPIError

        client = MaritacaClient(api_key="fake-key")

        with patch.object(
            client.client.chat.completions, "create",
            side_effect=Exception("connection error")
        ):
            with pytest.raises(MaritacaAPIError):
                client.analyze_plagiarism(
                    code1="x", code2="y", file1="a.py", file2="b.py",
                    textual_similarity=0.5, ast_similarity=0.5,
                    plagiarism_type="REUSO_LEGITIMO", confidence=0.3,
                )
