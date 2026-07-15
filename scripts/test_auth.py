#!/usr/bin/env python3
"""
Test authentication flow.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import (
    SessionManager,
    OAuthHandler,
    OAuthConfig,
    get_session,
    UserRepository,
)
from auth.database import init_db


def test_oauth_config():
    print("📋 Testing OAuth Config...")
    config = OAuthConfig()
    
    print(f"  Google Client ID: {'✓' if config.google_client_id else '✗'}")
    print(f"  GitHub Client ID: {'✓' if config.github_client_id else '✗'}")
    print(f"  Microsoft Client ID: {'✓' if config.microsoft_client_id else '✗'}")
    print(f"  Admin Emails: {config.admin_emails}")
    print()


def test_session_manager():
    print("📋 Testing Session Manager...")
    manager = SessionManager()
    
    print(f"  Is authenticated: {manager.is_authenticated()}")
    print(f"  Current user: {manager.get_current_user()}")
    print()
    
    test_user = {
        'id': 1,
        'email': 'test@example.com',
        'name': 'Test User',
        'role': 'user'
    }
    
    print("  Setting test user...")
    manager.login(test_user)
    print(f"  Is authenticated: {manager.is_authenticated()}")
    print(f"  Current user: {manager.get_current_user()}")
    
    print("  Logging out...")
    manager.logout()
    print(f"  Is authenticated: {manager.is_authenticated()}")
    print()


def test_repositories():
    print("📋 Testing Repositories...")
    db = get_session()
    user_repo = UserRepository(db)
    
    print("  Creating test user...")
    user = user_repo.create(
        email="test_user@example.com",
        name="Test User",
        role="user",
        is_active=True,
        is_verified=True
    )
    print(f"  Created user: {user.email} (ID: {user.id})")
    
    print("  Finding user by email...")
    found = user_repo.find_by_email("test_user@example.com")
    print(f"  Found: {found.email if found else 'None'}")
    
    print("  Finding user by ID...")
    found = user_repo.find_by_id(user.id)
    print(f"  Found: {found.email if found else 'None'}")
    
    db.query(type(user)).filter_by(email="test_user@example.com").delete()
    db.commit()
    db.close()
    
    print("  Test user deleted")
    print()


def test_oauth_handler():
    print("📋 Testing OAuth Handler...")
    
    config = OAuthConfig()
    
    if config.google_client_id:
        handler = OAuthHandler('google')
        auth_url = handler.get_authorization_url(state='test123')
        print(f"  Google Auth URL: {auth_url[:60]}...")
    else:
        print("  Google OAuth not configured (skipped)")
    
    if config.github_client_id:
        handler = OAuthHandler('github')
        auth_url = handler.get_authorization_url(state='test456')
        print(f"  GitHub Auth URL: {auth_url[:60]}...")
    else:
        print("  GitHub OAuth not configured (skipped)")
    
    if config.microsoft_client_id:
        handler = OAuthHandler('microsoft')
        auth_url = handler.get_authorization_url(state='test789')
        print(f"  Microsoft Auth URL: {auth_url[:60]}...")
    else:
        print("  Microsoft OAuth not configured (skipped)")
    
    print()


def main():
    print("=" * 60)
    print("Authentication System Test")
    print("=" * 60)
    print()
    
    init_db()
    
    test_oauth_config()
    test_session_manager()
    test_repositories()
    test_oauth_handler()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()