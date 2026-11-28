from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
    UserUpdateRequest,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/", summary="Auth Module Status")
def auth_status():
    return {"module": "auth", "status": "active", "version": "v1"}


@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED, summary="Register New User")
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account with role validation and password hashing."""
    service = AuthService(db)
    return service.register(req)


@router.post("/login", response_model=TokenResponse, summary="User Login")
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate credentials and generate a signed JWT bearer token."""
    service = AuthService(db)
    return service.login(req)


@router.get("/me", response_model=UserProfileResponse, summary="Get Current User Profile")
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.put("/profile", response_model=UserProfileResponse, summary="Update Current User Profile")
def update_profile(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name or phone for the current user."""
    service = AuthService(db)
    return service.update_profile(current_user, req)


@router.post("/change-password", response_model=MessageResponse, summary="Change Password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password verifying current password first."""
    service = AuthService(db)
    service.change_password(current_user, req)
    return MessageResponse(message="Password changed successfully.")


@router.post("/logout", response_model=MessageResponse, summary="Logout User")
def logout(current_user: User = Depends(get_current_user)):
    """
    Stateless JWT Logout:
    Tokens are stateless and cryptographically signed. Clients must discard the token.
    Previously issued tokens remain cryptographically valid until expiration time.
    """
    return MessageResponse(
        message="Logout successful. Please discard your client-side access token."
    )


@router.post("/seed-demo", summary="Seed Demo Accounts (Admin, Development Only)")
def seed_demo(
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Idempotent demo account seeder.
    Secured: requires authenticated ADMIN and strictly disabled in production environments.
    """
    from app.core.config import get_settings
    settings = get_settings()
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is strictly disabled in production environments.",
        )
    return AuthService.seed_demo_accounts(db)

