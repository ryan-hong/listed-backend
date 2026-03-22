from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class SignUpResponse(BaseModel):
    message: str
    check_id: str | None = None


class ConfirmStatusResponse(BaseModel):
    confirmed: bool


class UserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
