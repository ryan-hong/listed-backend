from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from listed_backend.database import get_db
from listed_backend.models.user import User
from listed_backend.supabase_client import get_supabase


async def get_current_user(
    authorization: str = Header(..., description="Bearer <access_token>"),
    client: AsyncClient = Depends(get_supabase),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    try:
        response = await client.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == response.user.id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
