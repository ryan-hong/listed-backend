from fastapi import APIRouter, Depends, Header

from listed_backend.dependencies.auth import get_current_user
from listed_backend.schemas.auth import AuthResponse, ConfirmStatusResponse, LoginRequest, RefreshRequest, SignUpRequest, SignUpResponse, UserResponse
from listed_backend.services import auth as auth_service
from listed_backend.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignUpResponse, status_code=201)
async def signup(body: SignUpRequest, client=Depends(get_supabase)):
    return await auth_service.sign_up(
        client, body.email, body.password, body.first_name, body.last_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, client=Depends(get_supabase)):
    return await auth_service.login(client, body.email, body.password)


@router.post("/logout", status_code=204)
async def logout(
    authorization: str = Header(..., description="Bearer <access_token>"),
    client=Depends(get_supabase),
):
    token = authorization.removeprefix("Bearer ").strip()
    await auth_service.logout(client, token)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(body: RefreshRequest, client=Depends(get_supabase)):
    return await auth_service.refresh(client, body.refresh_token)


@router.get("/confirm-status/{user_id}", response_model=ConfirmStatusResponse)
async def confirm_status(user_id: str, client=Depends(get_supabase)):
    return await auth_service.check_email_confirmed(client, user_id)


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return UserResponse(id=str(user.id), email=user.email)
