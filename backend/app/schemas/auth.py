from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="SHOP_OWNER", description="Public registration permits SHOP_OWNER only")
    location_id: Optional[int] = None
    phone: Optional[str] = None
    location_name: Optional[str] = Field(default=None, max_length=255, description="Auto-create a shop location if location_id is not provided")
    location_type: Optional[str] = Field(default="SHOP", description="SHOP")
    location_address: Optional[str] = Field(default=None, description="Address for the auto-created shop location")



class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: int
    role: str


class UserProfileResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    location_id: Optional[int] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)
