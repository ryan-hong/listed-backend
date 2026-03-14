import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase_auth.errors import AuthApiError
from supabase import AsyncClient

from listed_backend.models.user import User
from listed_backend.schemas.auth import AuthResponse, UserResponse


def _build_auth_response(session, user) -> AuthResponse:
    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        token_type=session.token_type,
        user=UserResponse(id=str(user.id), email=user.email),
    )


async def sign_up(client: AsyncClient, db: AsyncSession, email: str, password: str) -> AuthResponse:
    try:
        response = await client.auth.sign_up({"email": email, "password": password})
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if response.session is None or response.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sign up succeeded but no session returned. Check your email for confirmation.",
        )

    db.add(User(id=uuid.UUID(str(response.user.id)), email=response.user.email))
    await db.commit()

    return _build_auth_response(response.session, response.user)


async def login(client: AsyncClient, email: str, password: str) -> AuthResponse:
    try:
        response = await client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return _build_auth_response(response.session, response.user)


async def logout(client: AsyncClient, access_token: str) -> None:
    try:
        await client.auth.admin.sign_out(access_token)
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def refresh(client: AsyncClient, refresh_token: str) -> AuthResponse:
    try:
        response = await client.auth.refresh_session(refresh_token)
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return _build_auth_response(response.session, response.user)
