"""
Test OAuth implementation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.oauth import OAuthHandler
from auth.config import OAuthConfig


def test_oauth_config():
    """Test OAuth configuration loading."""
    print("Testing OAuth configuration...")
    config = OAuthConfig()
    
    providers = config.get_available_providers()
    print(f"  Available providers: {providers}")
    
    for provider in providers:
        assert provider in ['google', 'github', 'microsoft']
        assert config.is_oauth_configured(provider)
    
    print("✓ OAuth configuration loaded successfully")


def test_authorization_urls():
    """Test authorization URL generation."""
    print("\nTesting authorization URL generation...")
    config = OAuthConfig()
    
    for provider in config.get_available_providers():
        handler = OAuthHandler(provider)
        
        state = "test_state_123"
        auth_url = handler.get_authorization_url(state=state)
        
        assert auth_url, f"No auth URL for {provider}"
        assert state in auth_url, f"State not in URL for {provider}"
        assert handler.providers[provider]['client_id'] in auth_url
        
        print(f"  {provider}: {auth_url[:80]}...")
    
    print("✓ Authorization URLs generated successfully")


def test_handler_creation():
    """Test OAuth handler creation."""
    print("\nTesting OAuth handler creation...")
    config = OAuthConfig()
    
    for provider in config.get_available_providers():
        handler = OAuthHandler(provider)
        assert handler.provider == provider
        assert handler.config is not None
        print(f"  {provider}: ✓")
    
    print("✓ OAuth handlers created successfully")


def test_invalid_provider():
    """Test error handling for invalid provider."""
    print("\nTesting invalid provider handling...")
    
    try:
        handler = OAuthHandler('invalid_provider')
        print("✗ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")


def test_validate_state():
    """Test OAuth state validation helper."""
    assert OAuthHandler.validate_state("abc", "abc") is True
    assert OAuthHandler.validate_state("abc", "xyz") is False
    assert OAuthHandler.validate_state("", "xyz") is False
    assert OAuthHandler.validate_state("abc", "") is False


def test_signed_state_roundtrip():
    """Signed state should preserve provider and validate signature."""
    state = OAuthHandler.create_state("google")

    assert OAuthHandler.extract_provider_from_state(state) == "google"
    assert OAuthHandler.verify_state_signature(state) is True


def test_signed_state_rejects_tampering():
    """Tampered signed state must fail signature verification."""
    state = OAuthHandler.create_state("github")
    provider, nonce, signature = state.split(":")
    tampered = f"{provider}:tampered-{nonce}:{signature}"

    assert OAuthHandler.verify_state_signature(tampered) is False


if __name__ == "__main__":
    print("=" * 60)
    print("OAuth Implementation Tests")
    print("=" * 60)
    
    try:
        test_oauth_config()
        test_authorization_urls()
        test_handler_creation()
        test_invalid_provider()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
