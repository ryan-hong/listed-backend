from supabase import AsyncClient, acreate_client

_client: AsyncClient | None = None


async def init_supabase(url: str, key: str) -> None:
    global _client
    _client = await acreate_client(url, key)


async def get_supabase() -> AsyncClient:
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase() first.")
    return _client
