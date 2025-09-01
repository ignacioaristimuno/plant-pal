from tavily import AsyncTavilyClient
from llama_index.core.workflow import Context

from src.settings.settings import get_settings
from src.settings.logger import custom_logger


# Set up logger
logger = custom_logger("WebSearchAgent")

# Get settings
settings = get_settings()


# Tool implementation
async def search_web(ctx: Context, query: str) -> str:
    """Useful for using the web to answer questions."""
    logger.info(f"Searching the web for: {query}")
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    search_results = await client.search(query)

    # Save the search results to the context store
    await ctx.store.set("search_results", str(search_results))
    return str(search_results)
