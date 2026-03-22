from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from supabase import AsyncClient

from listed_backend.schemas.auth import AuthResponse, ConfirmStatusResponse, SignUpResponse, UserResponse


def _build_auth_response(session, user) -> AuthResponse:
    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        token_type=session.token_type,
        user=UserResponse(id=str(user.id), email=user.email),
    )


async def sign_up(
    client: AsyncClient,
    email: str,
    password: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> SignUpResponse:
    data: dict[str, str] = {}
    if first_name:
        data["first_name"] = first_name
    if last_name:
        data["last_name"] = last_name

    try:
        response = await client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": data},
        })
    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    is_duplicate = (
        response.user is not None
        and not response.user.identities
    )
    if is_duplicate:
        try:
            await client.auth.reset_password_for_email(email)
        except AuthApiError:
            pass
        return SignUpResponse(message="Check your email to confirm your account.")

    check_id = str(response.user.id) if response.user else None
    return SignUpResponse(
        message="Check your email to confirm your account.",
        check_id=check_id,
    )


async def check_email_confirmed(client: AsyncClient, user_id: str) -> ConfirmStatusResponse:
    try:
        response = await client.auth.admin.get_user_by_id(user_id)
    except AuthApiError:
        return ConfirmStatusResponse(confirmed=False)

    confirmed = response.user.email_confirmed_at is not None
    return ConfirmStatusResponse(confirmed=confirmed)


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
