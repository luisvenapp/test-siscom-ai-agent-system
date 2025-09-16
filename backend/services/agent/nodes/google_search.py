import os
import httpx
from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate

from core.logging_config import get_logger
from conf import settings
from services.agent.nodes.base import NodeAbstractClass

logger = get_logger(__name__)

class GoogleResearchNode(NodeAbstractClass):
    """
    Node to perform Google searches using Serper API:
    1. Search for latest news on given topics.
    2. Research user's question based on conversation summary.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topics: List[str] = state.get("topics", [])
        messages: list = state.get("conversation_summary", [])
        question: str = state.get("question", "")

        messages = state.get("messages", [])
        messages_users = "\n\n".join([f"{msg.sender} ({msg.role}): {msg.content}" for msg in messages if msg.role != "assistant"])

        latest_news_summary = await self._get_latest_news(topics)
        question_answer_summary = await self._answer_question_from_summary(messages_users, question)

        logger.info(f"Latest news summary: {latest_news_summary}")
        logger.info(f"Question answer summary: {question_answer_summary}") 

        return {
            "latest_news_summary": latest_news_summary,
            "question_answer_summary": question_answer_summary,
        }

    async def _get_latest_news(self, topics: List[str]) -> str:
        """
        Perform Google searches on provided topics and format the results.
        """
        if not topics:
            logger.warning("No topics provided.")
            return "No topics available for news summary."

        url = "https://google.serper.dev/news"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        results = []
        async with httpx.AsyncClient() as client:
            for topic in topics:
                payload = {"q": topic}
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 200 and response.json().get("news"):
                        news_items = response.json()["news"][:5]  # limit to top 5
                        topic_summary = f"\n📌 *{topic.capitalize()}*:\n"
                        for item in news_items:
                            topic_summary += f"- [{item.get('title')}]: {item.get('snippet')}: \n"
                        results.append(topic_summary)
                except Exception as e:
                    logger.error(f"Failed to fetch news for topic '{topic}': {e}")

        return "\n".join(results) if results else "No relevant news found for the given topics."

    async def _answer_question_from_summary(self, summary: str, question: str) -> str:
        """
        Uses LLM to generate a search query from conversation summary,
        performs search, and extracts an answer using the LLM.
        """
        if not summary:
            logger.warning("No conversation summary provided.")
            return "No summary available to generate a question."

        try:
            # Step 1: Generate search query from conversation summary
            prompt_template = ChatPromptTemplate.from_messages([
                                ("system", "Eres un asistente útil que genera consultas de búsqueda claras y efectivas en Google."),
                                ("user", f"""
                    Analiza el siguiente resumen de conversación y genera una lista de máximo 5 consultas (sin tener en cuenta las preguntas o mensajes del agente) de búsqueda independientes 
                    (en español o inglés) que podrían ayudar a encontrar respuestas a los temas o preguntas planteadas. 
                    Devuelve solo la lista de queries, cada una en una línea:

                    {summary}
                    """)])

            generated_query_list = await self.llm_manager.ainvoke(prompt_template)

            queries = [
                q.strip("-• \n") for q in generated_query_list.split("\n")
                if q.strip()
            ][:5]

            queries.append(question)

            if not queries:
                logger.warning("No queries generated from summary.")
                return "No se generaron consultas de búsqueda."

            logger.info(f"Generated queries: {queries}")

            search_url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json",
            }

            all_snippets = []

            async with httpx.AsyncClient() as client:
                for query in queries:
                    payload = {"q": query}
                    response = await client.post(search_url, headers=headers, json=payload)

                    if response.status_code != 200:
                        logger.warning(f"Search failed for query: {query}")
                        continue

                    data = response.json()
                    organic = data.get("organic", [])[:3]
                    for item in organic:
                        snippet = item.get("snippet")
                        if snippet:
                            all_snippets.append(f"🔎 **{query}**:\n{snippet}")

            if not all_snippets:
                # import pdb; pdb.set_trace()
                return "No se encontraron resultados relevantes."

            combined_snippets = "\n\n".join(all_snippets)

            # Paso 3: Sintetizar una respuesta desde todos los snippets
            prompt_answer = ChatPromptTemplate.from_messages([
                            ("system", "Eres un asistente útil que sintetiza respuestas a partir de fragmentos de resultados de búsqueda."),
                            ("user", f"""
                Usa la información recopilada en los siguientes fragmentos de búsqueda para redactar una respuesta útil, concisa y bien estructurada que resuma los puntos clave de los temas consultados.

                Fragmentos:
                {combined_snippets}
                """)
                        ])

            answer = await self.llm_manager.ainvoke(prompt_answer)
            return answer.strip()

        except Exception as e:
            logger.error(f"Error answering from summary: {e}")
            return "Ocurrió un error al procesar la respuesta desde Google."
