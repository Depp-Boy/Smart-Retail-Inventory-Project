from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserProfileResponse

router = APIRouter()


@router.get("/", response_model=List[UserProfileResponse], summary="List Users")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    """List system users (restricted to ADMIN and WAREHOUSE_MANAGER)."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.upper())
    return query.offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserProfileResponse, summary="Get User by ID")
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve user profile by ID."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found.")
    return user
