from tavily import AsyncTavilyClient

from src.settings.settings import get_settings


settings = get_settings()


async def search_web(query: str) -> str:
    """Useful for using the web to answer questions."""
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    return str(await client.search(query))
