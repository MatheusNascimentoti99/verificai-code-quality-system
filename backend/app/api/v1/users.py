"""
User management endpoints for VerificAI Backend
"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, CommonQueryParams, verify_admin_permission, get_pagination_params
from app.models.user import User, UserRole
from app.schemas.user import (
    UserResponse, UserUpdate, UserPasswordUpdate, UserProfile,
    UserListResponse, UserStats, APIKeyCreate, APIKeyResponse,
    UserPreferences, UserSearchFilters
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user information"""
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", response_model=dict)
def update_current_user_password(
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user password"""
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.set_password(password_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.get("/me/preferences", response_model=UserPreferences)
def get_current_user_preferences(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user preferences"""
    return UserPreferences(
        language=current_user.preferred_language,
        timezone=current_user.timezone,
        email_notifications=current_user.email_notifications,
        analysis_reports=current_user.email_analysis_reports,
        security_alerts=current_user.email_security_alerts
    )


@router.put("/me/preferences", response_model=UserPreferences)
def update_current_user_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user preferences"""
    current_user.preferred_language = preferences.language
    current_user.timezone = preferences.timezone
    current_user.email_notifications = preferences.email_notifications
    current_user.email_analysis_reports = preferences.analysis_reports
    current_user.email_security_alerts = preferences.security_alerts

    db.commit()
    db.refresh(current_user)

    return preferences


@router.post("/me/api-key", response_model=APIKeyResponse)
def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create new API key for current user"""
    from app.core.security import APIKeyManager
    import datetime

    api_key, api_key_hash = APIKeyManager.generate_api_key()

    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=key_data.expires_in_days)

    current_user.api_key_hash = api_key_hash
    current_user.api_key_created_at = datetime.datetime.utcnow()

    db.commit()

    return APIKeyResponse(
        id=current_user.id,
        name=key_data.name,
        api_key=api_key,
        created_at=current_user.api_key_created_at,
        expires_at=expires_at,
        last_used=None,
        is_active=True
    )


@router.delete("/me/api-key", response_model=dict)
def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Revoke current user's API key"""
    current_user.api_key_hash = None
    current_user.api_key_created_at = None

    db.commit()

    return {"message": "API key revoked successfully"}


@router.get("/", response_model=PaginatedResponse[UserResponse])
def list_users(
    params: CommonQueryParams = Depends(),
    filters: UserSearchFilters = Depends(),
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """List all users (admin only)"""
    query = db.query(User)

    # Apply filters
    if filters.role:
        query = query.filter(User.role == filters.role)
    if filters.is_active is not None:
        query = query.filter(User.is_active == filters.is_active)
    if filters.is_verified is not None:
        query = query.filter(User.is_verified == filters.is_verified)
    if filters.search:
        query = query.filter(
            User.username.contains(filters.search) |
            User.email.contains(filters.search) |
            User.full_name.contains(filters.search)
        )

    # Get total count
    total = query.count()

    # Apply pagination
    users = query.offset(params.skip).limit(params.limit).all()

    return PaginatedResponse(
        items=users,
        total=total,
        skip=params.skip,
        limit=params.limit,
        pages=(total + params.limit - 1) // params.limit,
        current_page=(params.skip // params.limit) + 1,
        has_next=params.skip + params.limit < total,
        has_prev=params.skip > 0
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.post("/{user_id}/activate", response_model=dict)
def activate_user(
    user_id: int,
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Activate user account (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}


@router.post("/{user_id}/deactivate", response_model=dict)
def deactivate_user(
    user_id: int,
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Deactivate user account (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    user.is_active = False
    db.commit()

    return {"message": "User deactivated successfully"}


@router.get("/stats", response_model=UserStats)
def get_user_stats(
    current_user: User = Depends(verify_admin_permission),
    db: Session = Depends(get_db)
) -> Any:
    """Get user statistics (admin only)"""
    from datetime import datetime, timedelta

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    today = datetime.utcnow().date()
    new_users_today = db.query(User).filter(
        User.created_at >= today
    ).count()

    week_ago = today - timedelta(days=7)
    new_users_week = db.query(User).filter(
        User.created_at >= week_ago
    ).count()

    month_ago = today - timedelta(days=30)
    new_users_month = db.query(User).filter(
        User.created_at >= month_ago
    ).count()

    # Count by role
    users_by_role = {}
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        users_by_role[role.value] = count

    return UserStats(
        total_users=total_users,
        active_users=active_users,
        new_users_today=new_users_today,
        new_users_week=new_users_week,
        new_users_month=new_users_month,
        users_by_role=users_by_role
    )