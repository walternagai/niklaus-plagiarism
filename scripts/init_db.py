#!/usr/bin/env python3
"""
Initialize database for Niklaus authentication.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.database import init_db
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    print("🔧 Initializing Niklaus database...")
    print("=" * 50)
    
    init_db()
    
    print("\n✅ Database initialized successfully!")
    print("\nTables created:")
    print("  ✓ users")
    print("  ✓ submissions")
    print("  ✓ analysis_cache")
    print("  ✓ audit_log")
    print("\nYou can now create users via OAuth login.")


if __name__ == "__main__":
    main()