#!/usr/bin/env python3
"""
Test OAuth callback processing manually with the code from the URL.
Usage: python scripts/test_oauth_callback_manual.py <code> <state>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.oauth import OAuthHandler
from auth.database import get_session, init_db
from auth.repository import UserRepository
from auth.config import OAuthConfig

def run_callback_test(code: str, state: str):
    print("=" * 60)
    print("Testing OAuth Callback Processing")
    print("=" * 60)
    print()
    
    print(f"Code: {code[:50]}...")
    print(f"State: {state[:50]}...")
    print()
    
    # Initialize database
    init_db()
    
    # Process callback
    provider = 'google'
    handler = OAuthHandler(provider)
    
    try:
        print(f"🔄 Exchanging authorization code for access token...")
        token_data = handler._exchange_code_for_token(code)
        
        if 'access_token' in token_data:
            print(f"✅ Access token received: {token_data['access_token'][:20]}...")
            print()
            
            print(f"🔄 Fetching user profile from Google...")
            profile = handler._get_user_profile(token_data['access_token'])
            
            print(f"✅ User profile received:")
            print(f"  Email: {profile.get('email')}")
            print(f"  Name: {profile.get('name')}")
            print(f"  ID: {profile.get('id')}")
            print()
            
            print(f"🔄 Creating/updating user in database...")
            user = handler.create_user_from_oauth(
                email=profile.get('email'),
                name=profile.get('name', profile.get('email', '').split('@')[0]),
                provider=provider,
                oauth_id=str(profile.get('id')),
                avatar_url=profile.get('picture')
            )
            
            print(f"✅ User {user.email} authenticated successfully!")
            print(f"  ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Role: {user.role}")
            print(f"  Admin: {user.role == 'admin'}")
            print()
            
            # Check admin status
            config = OAuthConfig()
            if config.is_admin(user.email):
                print(f"👑 User {user.email} is an admin!")
            print()
            
            print("=" * 60)
            print("✅ OAUTH CALLBACK SUCCESSFUL")
            print("=" * 60)
            print()
            print("You can now login via the web interface!")
            
        else:
            print(f"❌ No access token in response: {token_data}")
            
    except Exception as e:
        print(f"❌ Error during callback processing:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/test_oauth_callback_manual.py <code> <state>")
        print()
        print("Get the code and state from your browser URL after OAuth redirect:")
        print("http://localhost:8501/?code=XXX&state=YYY")
        sys.exit(1)
    
    code = sys.argv[1]
    state = sys.argv[2]
    
    run_callback_test(code, state)
