"""
Authentication endpoints for VerificAI Backend
"""

from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.common import BaseResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user"""
    # Check if user already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(**user_data.model_dump(exclude={"confirm_password"}))
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Login user and return access token"""
    print("--- LOGIN ATTEMPT ---")
    print(f"Username: {form_data.username}")
    user = db.query(User).filter(User.username == form_data.username).first()
    print(f"User found in DB: {'Yes' if user else 'No'}")

    if not user or not user.verify_password(form_data.password):
        print("Authentication failed: Incorrect username or password.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print("Password verification successful.")
    print(f"Is user active? {user.is_active}")

    if not user.is_active:
        print("Authentication failed: Inactive user.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Update last login
    print("Updating last login...")
    user.update_last_login()
    db.commit()
    print("Last login updated.")

    # Create access token
    print("Creating access token...")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    print("Access token created.")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "preferred_language": user.preferred_language,
            "timezone": user.timezone
        }
    }


@router.post("/login-simple")
def login_simple(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Simple login test without update_last_login"""
    try:
        user = db.query(User).filter(User.username == form_data.username).first()

        if not user or not user.verify_password(form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.username, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": "QA_ENGINEER"  # Temporarily hardcoded
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/login/json", response_model=dict)
def login_json(
    user_data: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """Login user using JSON payload"""
    try:
        user = db.query(User).filter(User.username == user_data.username).first()

        if not user or not user.verify_password(user_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Update last login
        user.update_last_login()
        db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.username, expires_delta=access_token_expires
        )
        
        # Safely handle role which might be Enum or string
        user_role = getattr(user.role, 'value', user.role) if user.role else "QA_ENGINEER"

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user_role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "bio": user.bio,
                "avatar_url": getattr(user, 'avatar_url', None),
                "preferred_language": getattr(user, 'preferred_language', 'pt-BR'),
                "timezone": getattr(user, 'timezone', 'UTC')
            }
        }
    except HTTPException:
        # Re-raise standard HTTP exceptions 
        raise
    except Exception as e:
        # Fallback error wrapper properly serialized
        import logging
        logging.error(f"Login JSON error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error during login: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user information"""
    return current_user


@router.post("/refresh")
def refresh_token(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=current_user.username, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout", response_model=BaseResponse)
def logout(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Logout user (client-side token removal)"""
    return {"success": True, "message": "Successfully logged out"}


# Import required dependency
from app.core.dependencies import get_current_user# Force reload 6 - save config endpoint


@router.post("/prompts-save-config", response_model=dict)
def save_prompt_config(
    prompt_config: dict,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Save prompt configuration"""
    # Placeholder for save functionality
    return {
        "success": True,
        "message": "Prompt configuration saved successfully",
        "timestamp": "2024-01-01T00:00:00Z",
        "saved_by": current_user.username
    }
