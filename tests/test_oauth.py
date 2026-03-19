"""
Test OAuth implementation.

Functions that previously relied on Streamlit secrets being configured (live
test_oauth_config / test_authorization_urls) have been moved to
scripts/test_oauth_callback_manual.py.  Only pure-logic tests are here.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from auth.oauth import OAuthHandler


# ---------------------------------------------------------------------------
# Pure-logic tests (no secrets / live providers needed)
# ---------------------------------------------------------------------------

def test_validate_state_matching():
    """validate_state returns True when both strings are identical."""
    assert OAuthHandler.validate_state("abc", "abc") is True


def test_validate_state_mismatch():
    """validate_state returns False on mismatch."""
    assert OAuthHandler.validate_state("abc", "xyz") is False


def test_validate_state_empty_received():
    assert OAuthHandler.validate_state("", "xyz") is False


def test_validate_state_empty_expected():
    assert OAuthHandler.validate_state("abc", "") is False


def test_invalid_provider_raises():
    """OAuthHandler raises ValueError for unknown providers."""
    with pytest.raises(ValueError):
        OAuthHandler("invalid_provider")


def test_signed_state_roundtrip():
    """Signed state should preserve provider and pass signature verification."""
    state = OAuthHandler.create_state("google")

    assert OAuthHandler.extract_provider_from_state(state) == "google"
    assert OAuthHandler.verify_state_signature(state) is True


def test_signed_state_rejects_tampering():
    """Tampered signed state must fail signature verification."""
    state = OAuthHandler.create_state("github")
    provider, nonce, signature = state.split(":")
    tampered = f"{provider}:tampered-{nonce}:{signature}"

    assert OAuthHandler.verify_state_signature(tampered) is False


def test_extract_provider_from_valid_state():
    state = OAuthHandler.create_state("microsoft")
    assert OAuthHandler.extract_provider_from_state(state) == "microsoft"


def test_extract_provider_returns_none_for_garbage():
    assert OAuthHandler.extract_provider_from_state("not-a-valid-state") is None


def test_extract_provider_returns_none_for_unknown_provider():
    # State looks structurally valid but uses unknown provider
    state = "unknown:nonce:sig"
    assert OAuthHandler.extract_provider_from_state(state) is None


def test_state_format():
    """State must have exactly provider:nonce:signature (3 colon-separated parts)."""
    state = OAuthHandler.create_state("google")
    parts = state.split(":")
    assert len(parts) == 3
    provider, nonce, sig = parts
    assert provider == "google"
    assert len(nonce) > 0
    assert len(sig) == 24  # signature is truncated to 24 hex chars
