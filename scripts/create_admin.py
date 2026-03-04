#!/usr/bin/env python3
"""
Create admin user manually.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.database import get_session
from auth.repository import UserRepository
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    print("👤 Create Admin User")
    print("=" * 40)
    
    email = input("Email: ").strip()
    name = input("Name: ").strip()
    
    if not email or not name:
        print("❌ Email and name are required")
        return
    
    db = get_session()
    user_repo = UserRepository(db)
    
    existing = user_repo.find_by_email(email)
    if existing:
        print(f"\n⚠️  User {email} already exists")
        promote = input("Promote to admin? (y/n): ").strip().lower()
        
        if promote == 'y':
            user_repo.set_role(existing.id, 'admin')
            print(f"✅ User {email} promoted to admin")
    else:
        user = user_repo.create(
            email=email,
            name=name,
            role='admin',
            is_active=True,
            is_verified=True
        )
        print(f"\n✅ Admin user created successfully")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
    
    db.close()


if __name__ == "__main__":
    main()