import asyncio
import json
from typing import Any, Dict, List, Optional

from core.logging_config import get_logger
from schemas.room_info import RoomData
from schemas.slang import SlangAnalysis
from services.agent.nodes.base import NodeAbstractClass
from services.agent.tools.scraping_page import scrape_text_from_urls
from services.agent.tools.search_google import get_country_slang
from services.document_extractor import PostgresDocumentExtractor
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)


class SlangAnalysisNode(NodeAbstractClass):
    """
    A node that analyzes slang and common phrases for a list of countries to extract
    culturally and commercially relevant information in parallel.

    This node performs the following steps for each country:
    1. Checks for a cached analysis in the database.
    2. If not cached, uses the `get_country_slang` tool to find web pages about the country's slang.
    3. Uses the `scrape_text_from_urls` tool to get the full content of those pages.
    4. Sends the scraped content to a specialized LLM prompt to analyze the information.
    5. Stores the new analysis in the database.
    6. Combines the cultural synthesis from all countries into a single context string.
    """

    async def _analyze_single_country(
        self, country: str, db_extractor: PostgresDocumentExtractor
    ) -> Optional[SlangAnalysis]:
        """
        Analyzes slang for a single country, checking cache first.
        """
        # Step 1: Check if the country already exists in the slang_analysis table
        try:
            country_record = db_extractor.get_document_by_country(
                database_name="agent_memory",
                table_name="slang_analysis",
                country=country,
            )
            if country_record:
                logger.info(
                    f"Country '{country}' found in cache. Returning cached result."
                )
                return SlangAnalysis(**country_record)
        except Exception as db_err:
            logger.warning(f"Could not query slang_analysis table for {country}: {db_err}")
            # If DB fails, continue to try to fetch new data

        # Step 2: Use the `get_country_slang` tool to find relevant pages.
        logger.info(f"Searching for slang info for {country}.")
        slang_search_result = await get_country_slang.ainvoke({"country": country})

        if (
            isinstance(slang_search_result, str)
            or not slang_search_result
            or not slang_search_result.slang_items
        ):
            error_message = (
                slang_search_result
                if isinstance(slang_search_result, str)
                else f"No information found for {country}'s slang."
            )
            logger.warning(f"Could not get slang info for {country}: {error_message}")
            return None

        # Step 3: Scrape text from the URLs found.
        urls_to_scrape = [item.link for item in slang_search_result.slang_items]
        logger.info(f"Scraping {len(urls_to_scrape)} URLs for {country}.")
        scraped_content = await scrape_text_from_urls.ainvoke(
            {"urls": urls_to_scrape}
        )

        # Fallback to using snippets if scraping fails or returns no content.
        if not scraped_content or "No se pudo extraer" in scraped_content:
            logger.warning(
                f"Failed to scrape content for {country}. Using search snippets as fallback."
            )
            scraped_content = "\n\n".join(
                f"Source: {item.link}\nContent: {item.snippet}"
                for item in slang_search_result.slang_items
            )

        # Step 4: Analyze the content with a specialized LLM prompt.
        analysis_prompt = await compile_prompt(
            "analyze_scraped_slang_content",
            country=country,
            scraped_content=scraped_content,
        )

        try:
            logger.info(f"Generating final analysis for {country} slang and culture.")
            json_string_response = await self.llm_manager.ainvoke(
                prompt=analysis_prompt
            )
            
            # Clean and parse the JSON response from the LLM
            try:
                clean_json_str = json_string_response.strip("` \n").removeprefix("json\n")
                raw_slang_data = json.loads(clean_json_str)
                slang_analysis_data = SlangAnalysis.from_raw_data(
                    country, raw_slang_data
                )
                logger.info(f"Slang analysis for {country} parsed successfully.")

                # Step 5: Store the new analysis in the database
                try:
                    db_extractor.insert_document(
                        database_name="agent_memory",
                        table_name="slang_analysis",
                        data=slang_analysis_data.dict(),
                    )
                    logger.info(f"Cached new slang analysis for {country}.")
                except Exception as e:
                    logger.error(f"Failed to cache slang analysis for {country}: {e}")

                return slang_analysis_data
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to parse JSON from LLM for {country}. Response: {json_string_response}"
                )
                return None
        except Exception as err:
            logger.error(f"Error generating slang analysis for {country}: {err}")
            return None

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes country-specific slang for multiple countries in parallel.

        Args:
            state (dict): The current graph state.

        Returns:
            dict: An updated state with 'slang_context' containing the combined analysis.
        """
        logger.info("---ANALYZING COUNTRY SLANG AND CULTURE---")
        room_info: Optional[RoomData] = state.get("room_details")

        if not room_info or not room_info.agents:
            logger.warning(
                "No room_details or agents found in state. Skipping slang analysis."
            )
            return {"slang_context": ""}

        countries: List[str] = list(set(agent.country for agent in room_info.agents))
        if not countries:
            logger.warning("No countries found in agent details. Skipping slang analysis.")
            return {"slang_context": ""}

        logger.info(f"Analyzing slang for countries: {countries}")

        db_extractor = PostgresDocumentExtractor()
        tasks = [
            self._analyze_single_country(country, db_extractor) for country in countries
        ]
        
        analysis_results = await asyncio.gather(*tasks)
        db_extractor.close_all_connections()

        successful_analyses: List[SlangAnalysis] = [
            res for res in analysis_results if res
        ]

        if not successful_analyses:
            logger.warning("Slang analysis failed for all countries.")
            return {"slang_context": ""}

        logger.info(
            f"Combined cultural synthesis generated for {len(successful_analyses)} countries."
        )
        return {"slang_context": successful_analyses}