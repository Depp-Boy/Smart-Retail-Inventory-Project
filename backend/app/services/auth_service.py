from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.location import Location
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserUpdateRequest,
)

VALID_ROLES = {"SHOP_OWNER", "WAREHOUSE_MANAGER", "WAREHOUSE_WORKER", "ADMIN"}


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, req: UserRegisterRequest) -> User:
        role = req.role.upper()
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{req.role}'. Supported roles are: {', '.join(sorted(VALID_ROLES))}",
            )

        if self.user_repo.get_by_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A user with email '{req.email}' is already registered.",
            )

        if req.location_id is not None:
            location = self.db.query(Location).filter(Location.location_id == req.location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location with ID {req.location_id} does not exist.",
                )

        new_user = User(
            name=req.name.strip(),
            email=req.email.lower().strip(),
            password_hash=hash_password(req.password),
            role=role,
            location_id=req.location_id,
            phone=req.phone.strip() if req.phone else None,
        )
        return self.user_repo.create(new_user)

    def login(self, req: UserLoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        settings = get_settings()
        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"sub": str(user.user_id), "email": user.email, "role": user.role},
            expires_delta=expires,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.user_id,
            role=user.role,
        )

    def update_profile(self, user: User, req: UserUpdateRequest) -> User:
        if req.name is not None:
            user.name = req.name.strip()
        if req.phone is not None:
            user.phone = req.phone.strip()
        return self.user_repo.update(user)

    def change_password(self, user: User, req: ChangePasswordRequest) -> None:
        if not verify_password(req.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        user.password_hash = hash_password(req.new_password)
        self.user_repo.update(user)
