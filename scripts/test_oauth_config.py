#!/usr/bin/env python3
"""
Test OAuth configuration loading.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.config import OAuthConfig

def test_oauth_config():
    """Test if OAuth configuration is loaded correctly."""
    print("=" * 60)
    print("OAuth Configuration Test")
    print("=" * 60)
    print()
    
    config = OAuthConfig()
    
    # Google
    print("📁 Google OAuth:")
    print(f"  Client ID: {config.google_client_id[:20] + '...' if config.google_client_id else '❌ NOT SET'}")
    print(f"  Client Secret: {'✓ SET' if config.google_client_secret else '❌ NOT SET'}")
    print(f"  Redirect URI: {config.google_redirect_uri}")
    print(f"  Configured: {'✅ YES' if config.is_oauth_configured('google') else '❌ NO'}")
    print()
    
    # GitHub
    print("📁 GitHub OAuth:")
    print(f"  Client ID: {config.github_client_id[:20] + '...' if config.github_client_id else '❌ NOT SET'}")
    print(f"  Client Secret: {'✓ SET' if config.github_client_secret else '❌ NOT SET'}")
    print(f"  Redirect URI: {config.github_redirect_uri}")
    print(f"  Configured: {'✅ YES' if config.is_oauth_configured('github') else '❌ NO'}")
    print()
    
    # Microsoft
    print("📁 Microsoft OAuth:")
    print(f"  Client ID: {config.microsoft_client_id[:20] + '...' if config.microsoft_client_id else '❌ NOT SET'}")
    print(f"  Client Secret: {'✓ SET' if config.microsoft_client_secret else '❌ NOT SET'}")
    print(f"  Redirect URI: {config.microsoft_redirect_uri}")
    print(f"  Configured: {'✅ YES' if config.is_oauth_configured('microsoft') else '❌ NO'}")
    print()
    
    # Available providers
    providers = config.get_available_providers()
    print(f"📋 Available Providers: {providers if providers else 'NONE'}")
    print()
    
    # Admin emails
    print(f"👑 Admin Emails: {config.admin_emails if config.admin_emails else 'NONE'}")
    print()
    
    # Instructions
    if not providers:
        print("=" * 60)
        print("⚠️  NO OAUTH PROVIDERS CONFIGURED")
        print("=" * 60)
        print()
        print("Please check your .streamlit/secrets.toml file:")
        print()
        print("Option 1 - Nested format (recommended):")
        print("""
[google]
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
redirect_uri = "http://localhost:8501"

[github]
client_id = "your-github-client-id"
client_secret = "your-github-client-secret"
redirect_uri = "http://localhost:8501"

ADMIN_EMAILS = "admin@example.com"
""")
        print()
        print("Option 2 - Flat format:")
        print("""
GOOGLE_CLIENT_ID = "your-google-client-id"
GOOGLE_CLIENT_SECRET = "your-google-client-secret"
GOOGLE_REDIRECT_URI = "http://localhost:8501"

GITHUB_CLIENT_ID = "your-github-client-id"
GITHUB_CLIENT_SECRET = "your-github-client-secret"
GITHUB_REDIRECT_URI = "http://localhost:8501"

ADMIN_EMAILS = "admin@example.com"
""")
        print("=" * 60)
    else:
        print("=" * 60)
        print("✅ OAUTH CONFIGURATION SUCCESSFUL")
        print("=" * 60)
        print()
        print(f"Providers available: {', '.join(providers).upper()}")
        print()
        print("You can now login using:")
        for provider in providers:
            print(f"  - {provider.capitalize()}")
        print()

if __name__ == "__main__":
    test_oauth_config()