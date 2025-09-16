import httpx
import asyncio
from typing import List
from langchain.tools import tool
from bs4 import BeautifulSoup

from core.logging_config import get_logger

logger = get_logger(__name__)


@tool
async def scrape_text_from_urls(urls: List[str]) -> str:
    """
    Scrapes the text content from a list of URLs.
    It uses httpx for asynchronous requests and BeautifulSoup for HTML parsing.
    The agent should first call another tool to get the URLs, then pass them to this tool.
    For example, call `get_country_slang`, extract the URLs from the result, and then call this tool.
    """

    if not urls:
        logger.warning("No URLs provided for scraping.")
        return "No se proporcionaron URLs para extraer texto."

    async def scrape_url(client, url):
        try:
            # Using a more generic user-agent can help avoid being blocked.
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await client.get(url, follow_redirects=True, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script, style, and other non-visible elements
            for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
                element.decompose()

            text = soup.get_text(separator='\n', strip=True)
            return f"Contenido extraído de {url}:\n\n{text}"
        except Exception as e:
            logger.error(f"Error al extraer texto de {url}: {e}")
            return f"No se pudo extraer el contenido de {url}."

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [scrape_url(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    return "\n\n---\n\n".join(results)