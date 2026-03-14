from fastapi import Depends, Header, HTTPException, status
from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from listed_backend.supabase_client import get_supabase


async def get_current_user(
    authorization: str = Header(..., description="Bearer <access_token>"),
    client: AsyncClient = Depends(get_supabase),
):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        response = await client.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return response.user
