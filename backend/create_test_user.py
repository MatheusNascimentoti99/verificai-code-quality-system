#!/usr/bin/env python3
"""
Script to create a test user for VerificAI
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent / "backend"))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def create_test_user():
    """Create a test user"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if existing_user:
            print("User 'testuser' already exists")
            return

        # Create new user
        test_user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.QA_ENGINEER,
            hashed_password=get_password_hash("test123"),
            is_active=True
        )

        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        print(f"Test user created successfully:")
        print(f"Username: testuser")
        print(f"Password: test123")
        print(f"Email: test@example.com")
        print(f"Role: {test_user.role}")

    except Exception as e:
        print(f"Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()