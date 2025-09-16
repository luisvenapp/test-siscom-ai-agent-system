from typing import List, Optional, Tuple, Union, Any
from langchain_community.embeddings import HuggingFaceEmbeddings
from db.pg_vector import PGVector
from langchain_core.documents import Document
from conf import settings
from core.logging_config import get_logger
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

logger = get_logger(__name__)

# Construct the PostgreSQL connection string using psycopg (psycopg3)
CONNECTION_STRING = "".join(
    [
        f"postgresql+psycopg://",
        f"{settings.LLM_DATABASE_POSTGRES_USER}:",
        f"{settings.LLM_DATABASE_POSTGRES_PASSWORD}@",
        f"{settings.LLM_DATABASE_POSTGRES_HOST}:",
        f"{settings.LLM_DATABASE_POSTGRES_WRITE_PORT}/",
        f"{settings.LLM_DATABASE_VECTOR_STORE_POSTGRES_DB}",
    ]
)


class VectorStoreManager:
    """
    VectorStoreManager manages a vector store based on PaginatedPGVector using HuggingFaceEmbeddings.

    It provides methods to add, delete, and query documents in the vector store, including paginated
    searches that allow retrieving "pages" of results directly from the database.
    """

    def __init__(
        self,
        embedding_name: str = settings.EMBEDDING_NAME,
        collection_name: str = settings.LLM_DATABASE_POSTGRES_VECTOR_COLLECTION,
        filters: Optional[dict] = None,
    ):
        """
        Initializes the VectorStoreManager with the specified embedding model and collection name.

        Args:
            embedding_name (str, optional): The HuggingFace embedding model name to use.
                Defaults to settings.EMBEDDING_NAME.
            collection_name (str, optional): The collection name within the vector store.
                Defaults to settings.LLM_DATABASE_POSTGRES_VECTOR_COLLECTION.
        """
        logger.info("Initializing VectorStoreManager...")
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_name)
        # Use the extended version that supports pagination
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=collection_name,
            connection=CONNECTION_STRING,
            filters=filters,
            use_jsonb=True,
        )
        logger.info(
            f"VectorStoreManager initialized with collection '{collection_name}'.")

    def add_documents(self, docs: List[Document], ids: Optional[List[str]] = None) -> Any:
        """
        Adds a list of documents to the vector store.

        Args:
            docs (List[Document]): A list of Document objects to be indexed.
            ids (Optional[List[str]], optional): A list of document IDs. If provided, documents with matching IDs
                will be overwritten.

        Returns:
            Any: The result of the add_documents operation.
        """
        logger.info(
            f"Adding {len(docs)} documents to collection '{self.vector_store.collection_name}'.")
        try:
            result = self.vector_store.add_documents(docs, ids=ids)
            logger.info("Documents added successfully.")
            return result
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def clear_all(self) -> Any:
        """
        Elimina todos los documentos de la colección vectorial.

        Returns:
            Any: El resultado de la operación de borrado.
        """
        logger.info(
            f"Clearing all documents from collection '{self.vector_store.collection_name}'.")
        try:
            # Obtiene todos los documentos indexados.
            docs = self.get_all()
            if not docs:
                logger.info("No documents found to delete.")
                return None
            # Extrae los IDs de cada documento.
            ids = [doc.id for doc in docs if doc.id is not None]
            if not ids:
                logger.info("No valid IDs found in documents.")
                return None
            # Llama al método delete_documents para eliminar.
            result = self.delete_documents(ids)
            logger.info("All documents have been deleted successfully.")
            return result
        except Exception as e:
            logger.error(f"Error clearing documents: {e}")
            raise

    def delete_documents(self, ids: List[str]) -> Any:
        """
        Deletes documents from the vector store by their IDs.

        Args:
            ids (List[str]): A list of document IDs to remove.

        Returns:
            Any: The result of the delete operation.
        """
        logger.info(
            f"Deleting documents with IDs {ids} from collection '{self.vector_store.collection_name}'.")
        try:
            result = self.vector_store.delete(ids=ids)
            logger.info("Documents deleted successfully.")
            return result
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise

    def similarity_search(self, query: str, k: int = 10, filter: Optional[dict] = None) -> List[Document]:
        """
        Performs a similarity search for the given query.

        Args:
            query (str): The query text to search for.
            k (int, optional): Number of top matching documents to retrieve. Defaults to 10.
            filter (Optional[dict], optional): Metadata filters to apply.

        Returns:
            List[Document]: A list of Document objects similar to the query.
        """
        logger.info(
            f"Performing similarity search for query: '{query}' (top {k} results).")
        try:
            results = self.vector_store.similarity_search(
                query, k=k, filter=filter)
            logger.info(
                f"Similarity search returned {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            raise

    def similarity_search_with_score(
        self, query: str, k: int = 10, filter: Optional[dict] = None
    ) -> List[Tuple[Document, float]]:
        """
        Performs a similarity search and returns documents with their similarity scores.

        Args:
            query (str): The query text.
            k (int, optional): Number of top matching documents to retrieve. Defaults to 10.
            filter (Optional[dict], optional): Metadata filters to apply.

        Returns:
            List[Tuple[Document, float]]: A list of tuples (Document, score).
        """
        logger.info(
            f"Performing similarity search with score for query: '{query}' (top {k} results).")
        try:
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter)
            logger.info(
                f"Similarity search with score returned {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search with score: {e}")
            raise

    def paginated_similarity_search(self, query: str, limit: int, offset: int = 0, filter: Optional[dict] = None) -> List[Document]:
        """
        Performs a paginated similarity search.

        Args:
            query (str): The query text.
            limit (int): Number of results (page size) to return.
            offset (int, optional): Number of results to skip. Defaults to 0.
            filter (Optional[dict], optional): Metadata filters to apply.

        Returns:
            List[Document]: A list of Document objects corresponding to the requested "page".
        """
        logger.info(
            f"Performing paginated similarity search for query: '{query}' with limit {limit} and offset {offset}.")
        try:
            embedding = self.vector_store.embeddings.embed_query(query)
            results = self.vector_store.paginated_similarity_search_by_vector(
                embedding, limit=limit, offset=offset, filter=filter
            )
            logger.info(f"Paginated search returned {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(f"Error during paginated similarity search: {e}")
            raise

    def get_all(self) -> List[Document]:
        """
        Retrieves all documents from the collection.

        Returns:
            List[Document]: A list of all Document objects in the collection.
        """
        logger.info(
            f"Retrieving all documents from collection '{self.vector_store.collection_name}'.")
        try:
            # import pdb; pdb.set_trace()
            results = self.vector_store.get_all()
            logger.info(
                f"Retrieved {len(results)} documents from the collection.")
            return results
        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            raise

    def paginated_similarity_search_with_score(self, query: str, limit: int, offset: int = 0, filter: Optional[dict] = None) -> List[Tuple[Document, float]]:
        """
        Performs a paginated similarity search and returns documents with their similarity scores.

        Args:
            query (str): The query text.
            limit (int): Number of results (page size) to return.
            offset (int, optional): Number of results to skip. Defaults to 0.
            filter (Optional[dict], optional): Metadata filters to apply.

        Returns:
            List[Tuple[Document, float]]: A list of tuples (Document, score) corresponding to the requested page.
        """
        logger.info(
            f"Performing paginated similarity search with score for query: '{query}' with limit {limit} and offset {offset}.")
        try:
            embedding = self.vector_store.embeddings.embed_query(query)
            results = self.vector_store.paginated_similarity_search_with_score_by_vector(
                embedding, limit=limit, offset=offset, filter=filter
            )
            logger.info(
                f"Paginated search with score returned {len(results)} documents.")
            return results
        except Exception as e:
            logger.error(
                f"Error during paginated similarity search with score: {e}")
            raise

    def as_retriever(self, search_type: str = "mmr", search_kwargs: Optional[dict] = None):
        """
        Converts the vector store into a retriever object for integration with chains.

        Args:
            search_type (str, optional): The search algorithm to use (e.g., "mmr"). Defaults to "mmr".
            search_kwargs (Optional[dict], optional): Additional search parameters.

        Returns:
            Any: A retriever object based on the vector store.
        """
        logger.info(
            f"Converting vector store to retriever using search type '{search_type}'.")
        try:
            retriever = self.vector_store.as_retriever(
                search_type=search_type, search_kwargs=search_kwargs)
            logger.info("Retriever created successfully.")
            return retriever
        except Exception as e:
            logger.error(f"Error converting vector store to retriever: {e}")
            raise

    def __repr__(self) -> str:
        return f"<VectorStoreManager(collection_name={self.vector_store.collection_name})>"

    def count(self) -> int:
        """
        Returns the number of documents in the collection.

        Returns:
            int: The number of documents in the collection.
        """
        return self.vector_store.count()

    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, key: Union[int, slice]) -> Union[Document, List[Document]]:
        return self.vector_store[key]

    def get_by_ids(self, ids: List[str]) -> List[Document]:
        """
        Retrieves documents from the collection by their IDs.

        Args:
            ids (List[str]): A list of document IDs to retrieve.

        Returns:
            List[Document]: A list of Document objects with matching IDs.
        """
        return self.vector_store.get_by_ids(ids)
