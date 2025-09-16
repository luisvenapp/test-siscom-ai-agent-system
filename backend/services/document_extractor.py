from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any

from conf import settings
from core.logging_config import get_logger
from db.pg_vector import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from services.llm_manager import LLMManager
from langchain_core.prompts import ChatPromptTemplate

logger = get_logger(__name__)

class VectorDocumentExtractor:
    """
    Extracts documents from a vector store based on semantic similarity.
    It uses a hybrid approach, starting with a broad semantic search and
    falling back to a keyword-based search if the initial results are not
    sufficiently relevant.
    """

    def __init__(self, collection_name: str, db_connection_string: str):
        """
        Initializes the extractor with a connection to the vector database
        and the necessary AI models.

        Args:
            collection_name (str): The name of the collection in the vector store.
            db_connection_string (str): The connection string for the PostgreSQL database.
        """
        self.llm_manager = LLMManager()
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_NAME)
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=collection_name,
            connection=db_connection_string,
            use_jsonb=True,
        )
        self.keyword_extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert in analyzing conversations. Your task is to extract the most relevant and important keywords or topics from the following text. Return them as a comma-separated list."),
            ("user", "{conversation_text}")
        ])

    async def _extract_keywords(self, text: str) -> List[str]:
        """
        Uses an LLM to extract relevant keywords from a text.

        Args:
            text (str): The text to analyze.

        Returns:
            List[str]: A list of extracted keywords.
        """
        logger.info("Performing keyword extraction fallback.")
        prompt = self.keyword_extraction_prompt
        response = await self.llm_manager.ainvoke(prompt, conversation_text=text)
        keywords = [keyword.strip() for keyword in response.split(',') if keyword.strip()]
        logger.info(f"Extracted keywords: {keywords}")
        return keywords

    async def extract_documents(
        self,
        messages: List[str],
        top_k: int = 5,
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Extracts relevant documents from the vector store based on a list of messages.

        It first performs a semantic search on the entire conversation. If the top result's
        similarity score is below the threshold, it falls back to extracting keywords and
        performing a search based on those.

        Args:
            messages (List[str]): A list of messages from the conversation.
            top_k (int): The maximum number of documents to return.
            similarity_threshold (float): The minimum similarity score to consider a match valid.

        Returns:
            List[Dict[str, Any]]: A list of relevant documents with their content and metadata.
        """
        if not messages:
            return []

        conversation_text = "\n".join(messages)
        # Embed conversation (sync embed inside async; acceptable here, adjust to executor if needed)
        conversation_embedding = self.vector_store.embeddings.embed_query(conversation_text)

        # 1. Initial semantic search
        logger.info("Performing initial semantic search on conversation.")
        search_results = self.vector_store.paginated_similarity_search_with_score_by_vector(
            embedding=conversation_embedding,
            limit=top_k,
            offset=0
        )

        # 2. Check if fallback is needed
        if not search_results or search_results[0][1] < similarity_threshold:
            logger.warning(f"Initial search yielded low confidence (score: {search_results[0][1] if search_results else 'N/A'}).")
            keywords = await self._extract_keywords(conversation_text)
            if not keywords:
                logger.warning("No keywords extracted. Returning initial low-confidence results.")
                return [{"page_content": doc.page_content, "metadata": doc.metadata, "score": score} for doc, score in search_results]

            keyword_text = " ".join(keywords)
            keyword_embedding = self.vector_store.embeddings.embed_query(keyword_text)

            # 3. Keyword-based search
            logger.info("Performing keyword-based search.")
            search_results = self.vector_store.paginated_similarity_search_with_score_by_vector(
                embedding=keyword_embedding,
                limit=top_k,
                offset=0
            )

        return [{"page_content": doc.page_content, "metadata": doc.metadata, "score": score} for doc, score in search_results]


class PostgresDocumentExtractor:

    def get_document_by_country(self, database_name: str, table_name: str, country: str) -> dict | None:
        """
        Retrieves a single document from the specified table where the country matches.

        Args:
            database_name (str): The PostgreSQL database to query.
            table_name (str): The table to extract the document from.
            country (str): The country to match (case-insensitive, stripped).

        Returns:
            dict | None: The record if found, else None.
        """
        self._authenticate(database_name)
        session = self.Session()
        try:
            inspector = inspect(self.engine)
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            if "country" not in columns:
                raise ValueError(f"Table '{table_name}' does not have a 'country' column.")

            query = text(f"SELECT * FROM {table_name} WHERE LOWER(TRIM(country)) = :country LIMIT 1")
            result = session.execute(query, {"country": country.strip().lower()})
            row = result.fetchone()
            if row:
                keys = result.keys()
                return dict(zip(keys, row))
            return None
        finally:
            session.close()
    """
    Extracts documents from PostgreSQL tables after authenticating access
    based on the provided database name.
    """

    def __init__(self):
        """
        Initializes the object without binding it to a specific database.
        The connection will be created dynamically per request.
        """
        self.engines = {}  # ← Cache de engines
        self.sessions = {}  # ← Cache de sessionmakers

    def _authenticate(self, database_name: str) -> None:
        if database_name in self.engines:
            self.engine = self.engines[database_name]
            self.Session = self.sessions[database_name]
            return

        authorized_databases = ["dev_scrapping_db", "dev_live_stream_sst_db", "agent_memory", "siscom"]
        if database_name not in authorized_databases:
            raise ValueError(f"Access to database '{database_name}' is not authorized.")

        connection_string = (
            f"postgresql+psycopg://{settings.LLM_DATABASE_POSTGRES_USER}:"
            f"{settings.LLM_DATABASE_POSTGRES_PASSWORD}@"
            f"{settings.LLM_DATABASE_POSTGRES_HOST}:"
            f"{settings.LLM_DATABASE_POSTGRES_WRITE_PORT}/"
            f"{database_name}"
        )

        engine = create_engine(connection_string, pool_size=5, max_overflow=10)
        Session = sessionmaker(bind=engine)

        # Guardar en cache
        self.engines[database_name] = engine
        self.sessions[database_name] = Session

        self.engine = engine
        self.Session = Session

    def get_recent_documents(self, database_name: str, table_name: str, limit: int = 2000) -> List[Dict[str, Any]]:
        """
        Authenticates the user and retrieves recent rows from the specified table.

        Args:
            database_name (str): The PostgreSQL database to query.
            table_name (str): The table to extract documents from.
            limit (int): Maximum number of rows to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of records from the table.

        Raises:
            Exception: If authentication or query fails.
        """
        self._authenticate(database_name)

        session = self.Session()
        try:
            inspector = inspect(self.engine)
            columns = [col["name"] for col in inspector.get_columns(table_name)]

            order_field = None
            if "fecha_ejecucion" in columns:
                order_field = "fecha_ejecucion"
            elif "created_at" in columns:
                order_field = "created_at"

            base_query = f"SELECT * FROM {table_name}"
            if order_field:
                base_query += f" ORDER BY {order_field} DESC"
            base_query += " LIMIT :limit"

            query = text(base_query)
            result = session.execute(query, {"limit": limit})
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result.fetchall()]
        finally:
            session.close()
            

    def insert_document(self, database_name: str, table_name: str, data: Dict[str, Any], conflict_target: str = None) -> None:
        """
        Inserts a new document (record) into a specific table. If a conflict_target (e.g., a primary key column name)
        is provided, it performs an "UPSERT" operation, updating the existing record on conflict.

        Args:
            database_name (str): The database to connect to.
            table_name (str): The table where the record will be inserted or updated.
            data (Dict[str, Any]): A dictionary representing the column names and their values.
            conflict_target (str, optional): The column name to use for conflict detection (e.g., 'id').
                                             If provided, an UPSERT will be performed. Defaults to None.
        """
        self._authenticate(database_name)

        session = self.Session()
        try:
            # Reflect table columns dynamically
            inspector = inspect(self.engine)
            columns_info = inspector.get_columns(table_name)
            columns_names = [col['name'] for col in columns_info]

            # Filter data to only include valid columns
            valid_data = {k: v for k, v in data.items() if k in columns_names}

            if not valid_data:
                raise ValueError("No valid columns found in input data for insertion.")

            # Base INSERT statement
            insert_clause = f"INSERT INTO {table_name} ({', '.join(valid_data.keys())}) VALUES ({', '.join([f':{key}' for key in valid_data.keys()])})"

            # Handle UPSERT logic if conflict_target is specified
            if conflict_target and conflict_target in valid_data:
                update_columns = [col for col in valid_data.keys() if col != conflict_target]
                if not update_columns:
                    conflict_clause = f" ON CONFLICT ({conflict_target}) DO NOTHING"
                else:
                    update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
                    conflict_clause = f" ON CONFLICT ({conflict_target}) DO UPDATE SET {update_clause}"
                final_stmt_str = insert_clause + conflict_clause
            else:
                final_stmt_str = insert_clause

            session.execute(text(final_stmt_str), valid_data)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def close_all_connections(self) -> None:
        """
        Closes all cached SQLAlchemy engine connections and clears the caches.
        """
        for engine in self.engines.values():
            engine.dispose()
        self.engines.clear()
        self.sessions.clear()

if __name__ == "__main__":
    # This is an example of how you might test the VectorDocumentExtractor
    import asyncio

    async def test_vector_extractor():
        # IMPORTANT: Replace with your actual database connection string and collection name
        # You might want to load this from your settings configuration
        DB_CONNECTION_STRING = f"postgresql+psycopg://{settings.LLM_DATABASE_POSTGRES_USER}:{settings.LLM_DATABASE_POSTGRES_PASSWORD}@{settings.LLM_DATABASE_POSTGRES_HOST}:{settings.LLM_DATABASE_POSTGRES_WRITE_PORT}/agent_memory"
        COLLECTION_NAME = "your_collection_name" # <--- CHANGE THIS

        extractor = VectorDocumentExtractor(
            collection_name=COLLECTION_NAME,
            db_connection_string=DB_CONNECTION_STRING
        )

        # Example messages from a WhatsApp chat
        sample_messages = [
            "Hey, does anyone remember the details for the Q3 project kickoff?",
            "I think it's next Tuesday.",
            "No, I checked the calendar, it's on Wednesday at 10 AM.",
            "Ah, right. Do we need to prepare a presentation?",
            "Yes, the project manager mentioned a 5-slide deck is required from each team."
        ]

        print("Extracting documents for Q3 project kickoff...")
        documents = await extractor.extract_documents(sample_messages)

        if documents:
            print(f"Found {len(documents)} relevant documents:")
            for doc in documents:
                print(f"  - Score: {doc['score']:.4f}")
                print(f"    Content: {doc['page_content'][:150]}...")
                print(f"    Metadata: {doc['metadata']}")
        else:
            print("No relevant documents found.")

    # To run the async test
    # asyncio.run(test_vector_extractor())

    extractor = PostgresDocumentExtractor()
    extractor.close_all_connections()