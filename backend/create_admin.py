import asyncio
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings

def create_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("Creating admin user...")
            admin = User(
                username="admin",
                email="admin@verificai.local",
                full_name="Administrator",
                # GET PASSWORD FROM ENV VAR
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_admin=True,
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            db.commit()
            print("Admin created. Username: admin, Password: admin")
        else:
            print("Admin user already exists.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
