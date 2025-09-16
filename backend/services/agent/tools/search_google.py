import httpx
import re
import asyncio
from typing import Callable, List, Union
from langchain.tools import tool
 
from core.logging_config import get_logger
from conf import settings
from schemas.tools import CountrySlangResponse, SlangItem

logger = get_logger(__name__)

async def retry_async(func: Callable, retries: int = 3, delay: float = 1.0):
    """Retry wrapper for async functions"""
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (attempt + 1))
    return None

@tool
async def get_latest_news(query_to_search_news: str) -> str:
    """Search the web last news using Serper API"""

    if not query_to_search_news:
        logger.warning("No topics provided.")
        return "No topics available for news summary."

    async def fetch_news():
        url = "https://google.serper.dev/news"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query_to_search_news}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()  # raises for 4xx/5xx
            return response.json()

    # Replace any special characters in the query
    query_to_search_news = re.sub(r"[^\w\s]", "", query_to_search_news)    
    query_to_search_news = query_to_search_news.replace("\n", " ").strip()
    
    logger.info(f"Searching for latest news on: {query_to_search_news}")

    data = await retry_async(fetch_news)

    if not data or "news" not in data:
        return f"No se pudo obtener noticias recientes sobre *{query_to_search_news}* en este momento."

    news_items = data["news"][:5]
    if not news_items:
        return f"No hay noticias relevantes sobre *{query_to_search_news}*."

    topic_summary = f"\n📌 *{query_to_search_news.capitalize()}*:\n"
    for item in news_items:
        topic_summary += f"- [{item.get('title')}]: {item.get('snippet')}\nLink: {item.get('link')}\n\n"

    return topic_summary

@tool
async def search_google(query: str) -> str:
    """Search the web using the Serper API"""

    if not query:
        logger.warning("No query provided.")
        return "No se proporcionó ninguna consulta para buscar."

    async def fetch_search():
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    query = re.sub(r"[^\w\s]", "", query)    
    query = query.replace("\n", " ").strip()
    
    logger.info(f"Searching Google for: {query}")
    
    data = await retry_async(fetch_search)

    if not data or "organic" not in data:
        return f"No se pudo obtener resultados para *{query}* en este momento."

    organic = data["organic"][:5]
    snippets = []
    for item in organic:
        snippet = item.get("snippet")
        link = item.get("link")
        if snippet:
            snippets.append(f"🔎 **{query}**:\n{snippet}.\nLink: {link}")

    if not snippets:
        return f"No se encontraron resultados relevantes sobre *{query}*."

    return "\n\n".join(snippets)


@tool
async def get_country_slang(country: str) -> Union[CountrySlangResponse, str]:
    """
    Search for common slang, words, and phrases for a given country.
    Returns a CountrySlangResponse object on success, or a string with an error message on failure.
    """

    if not country:
        logger.warning("No country provided.")
        return "No se proporcionó ningún país para buscar jergas."

    query = f"Jerga y frases comunes de {country}"

    async def fetch_slang():
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    data = await retry_async(fetch_slang)

    if not data or "organic" not in data:
        return f"No se pudo obtener resultados para la jerga de *{country}* en este momento."

    organic = data.get("organic", [])[:5]
    slang_items = []
    for item in organic:
        if item.get("snippet") and item.get("title") and item.get("link"):
            slang_items.append(
                SlangItem(
                    title=item.get("title"),
                    snippet=item.get("snippet"),
                    link=item.get("link"),
                )
            )

    if not slang_items:
        return f"No se encontraron resultados relevantes sobre la jerga de *{country}*."

    return CountrySlangResponse(slang_items=slang_items)