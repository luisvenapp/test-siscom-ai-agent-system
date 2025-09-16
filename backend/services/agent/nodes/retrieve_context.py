from typing import Any, Dict, Optional

from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from services.llm_manager import LLMManager
from services.vectorstore_manager import VectorStoreManager
from utils.get_prompts import compile_prompt
from utils.helpers import clean_text

logger = get_logger(__name__)

EXTRA_CONTEXT_INFO: str = ""


class RetrieveContextNode(NodeAbstractClass):
    """
    Node that retrieves additional context from a vector store.

    Uses similarity search on a PGVector-backed store to fetch relevant
    documents (e.g., DDL, docs, Q&A snippets) that complement the
    user's question. The aggregated context is stored in state under
    the key "additional_context".
    """

    def __init__(
        self,
        vector_store: VectorStoreManager,
        k: int = 10,
        max_score: float = 0.7,
        llm_manager: Optional[LLMManager] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the RetrieveContextNode.

        Args:
            vector_store: Configured VectorStoreManager instance.
            k: Number of top documents to retrieve (default: 10).
            max_score: Maximum similarity score to include (default: 0.7).
            llm_manager: Optional LLMManager instance.
        """
        super().__init__(llm_manager=llm_manager, *args, **kwargs)
        self.vector_store = vector_store
        self.k = k
        self.max_score = max_score

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and aggregate additional context based on the conversation.

        The query is formed from "conversation_summary" and "question"
        in the state. If none are found, returns empty context.

        Args:
            state: Current state containing at least a summary or question.

        Returns:
            Updated state with "additional_context" key.
        """
        summary = state.get("conversation_summary", "")
        question = state.get("question", "")
        chat_name = state.get("room_name", "")
        chat_description = state.get("chat_description", "")
        topics = state.get("topics", "")
        room_id = state.get("room_id", "")
        
        query = " === ".join([summary, question]).strip()

        if not query:
            logger.warning(f"No query text found; skipping context retrieval.")
            state["additional_context"] = ""
            return state

        try:
            logger.info(
                f"Retrieving context for query '{query}' (top {self.k} docs).")
            # docs_with_scores = self.vector_store.similarity_search_with_score(
            #     query, k=self.k
            # )
            webscraping_docs = self.vector_store.get_recent_documents("dev_scrapping_db", "webscrapping", 1000)

            live_stream_documents = self.vector_store.get_recent_documents("dev_live_stream_sst_db", "transcription_segments", 200)
            agent_responses = self.vector_store.get_recent_documents("agent_memory", "responses", 200)

            # for doc, score in docs_with_scores:
            #     snippet = doc.page_content[:200]
            #     logger.debug(f"Doc snippet: '{snippet}...' score={score:.3f}")
            #     if score > self.max_score:
            #         continue
            #     context += f"\n\n{doc.page_content}"

            context_agent_response = "<agent_response>\n\n"
            for doc in agent_responses:
                if doc['room_id'] == room_id:
                    context_agent_response += f"\n\nFecha: {doc['timestamp']}\ntext: {doc['agent_response']}"
            context_agent_response += "\n\n</agent_response>"

            context_news = "<webscraping_data>\n\n"
            for doc in webscraping_docs:
                text = clean_text(doc['output'])
                # context_news += f"\n\nFecha: {doc['fecha_ejecucion']}\nCanal de noticia: {doc['url']}\nMensaje: {doc['output'].strip()}"
                context_news += f"\n\nFecha: {doc['fecha_ejecucion']}\nMensaje: {text}"
            context_news += "\n\n</webscraping_data>"

            context_live_stream = "<live_stream_data>\n\n"
            for text in live_stream_documents:
                context_live_stream += f"{text['transcript_text']} "
            
            context_live_stream += "\n\n</live_stream_data>"

            # Extract messages related to the topics
            prompt_template = await compile_prompt(
                "filter_relevant_news",
                topics=", ".join(topics),
                list_messages=context_news
            )

            context_news = await self.llm_manager.ainvoke(
                prompt=prompt_template
            )

            context_news = f"<webscraping_data>\n\n{context_news}\n\n</webscraping_data>"

            full_context = f"{context_agent_response}\n\n{context_news.strip()}\n\n{context_live_stream.strip()}"  

            # logger.info(f"Aggregated additional context: {full_context}... ")
            return {"additional_context": full_context}

        except Exception as err:
            logger.error(f"Error retrieving context: {err}")
            return {"additional_context": EXTRA_CONTEXT_INFO}
