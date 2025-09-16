from typing import List, Optional, Sequence, Tuple, Dict, Any, Union
import sqlalchemy
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document
from langchain_postgres.vectorstores import PGVector as BasePGVector, _results_to_docs


class PGVector(BasePGVector):
    """
    Extension of PGVector to support:
      - Default metadata filters applied on every query.
      - Pagination using offset and limit parameters.
      - Both synchronous and asynchronous APIs.
    """

    def __init__(
        self,
        filters: Optional[Dict[str, Any]] = None,
        *args, **kwargs
    ):
        """
        Initialize PGVector with default filters.

        Args:
            embedding_name: Name of the embedding model.
            collection_name: Name of the vector collection.
            connection: DB connection string.
            use_jsonb: Whether to use JSONB for metadata storage.
            filters: Default metadata filters to apply on every query.
        """
        super().__init__(*args, **kwargs)
        self.default_filters = filters or {}

    def _merge_filters(self, override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine the default filters with any override filters.
        Override filters take precedence.
        """
        combined = dict(self.default_filters)
        if override:
            combined.update(override)
        return combined

    # SYNCHRONOUS METHODS

    def paginated_query_collection(
        self,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Sequence[Any]:
        """
        Queries the collection with offset/limit and metadata filtering.
        """
        combined_filter = self._merge_filters(filter)
        with self._make_sync_session() as session:
            collection = self.get_collection(session)
            if not collection:
                raise ValueError("Collection not found")
            filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

            # apply merged metadata filters
            if combined_filter:
                if self.use_jsonb:
                    clause = self._create_filter_clause(combined_filter)
                    if clause is not None:
                        filter_by.append(clause)
                else:
                    clauses = self._create_filter_clause_json_deprecated(
                        combined_filter)
                    filter_by.extend(clauses)

            results = (
                session.query(
                    self.EmbeddingStore,
                    self.distance_strategy(embedding).label("distance"),
                )
                .filter(*filter_by)
                .join(
                    self.CollectionStore,
                    self.EmbeddingStore.collection_id == self.CollectionStore.uuid,
                )
                .order_by(sqlalchemy.asc("distance"))
                .offset(offset)
                .limit(limit)
                .all()
            )
            return results

    def paginated_similarity_search_with_score_by_vector(
        self,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Similarity search with pagination & scores.
        """
        results = self.paginated_query_collection(
            embedding, limit, offset, filter)
        return self._results_to_docs_and_scores(results)

    def paginated_similarity_search_by_vector(
        self,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Similarity search with pagination, returning only documents.
        """
        docs_and_scores = self.paginated_similarity_search_with_score_by_vector(
            embedding, limit, offset, filter
        )
        return _results_to_docs(docs_and_scores)

    def get_all(self, filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Retrieve all documents, applying default + override filters.
        """
        combined_filter = self._merge_filters(filter)
        with self._make_sync_session() as session:
            collection = self.get_collection(session)
            if not collection:
                raise ValueError("Collection not found")
            filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

            if combined_filter:
                if self.use_jsonb:
                    clause = self._create_filter_clause(combined_filter)
                    if clause is not None:
                        filter_by.append(clause)
                else:
                    clauses = self._create_filter_clause_json_deprecated(
                        combined_filter)
                    filter_by.extend(clauses)

            results = session.query(
                self.EmbeddingStore).filter(*filter_by).all()
            return [
                Document(id=r.id, page_content=r.document,
                         metadata=r.cmetadata)
                for r in results
            ]

    def count(self) -> int:
        """
        Count documents, applying default filters.
        """
        combined_filter = self._merge_filters(None)
        with self._make_sync_session() as session:
            collection = self.get_collection(session)
            if not collection:
                raise ValueError("Collection not found")
            filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

            if combined_filter:
                if self.use_jsonb:
                    clause = self._create_filter_clause(combined_filter)
                    if clause is not None:
                        filter_by.append(clause)
                else:
                    clauses = self._create_filter_clause_json_deprecated(
                        combined_filter
                    )
                    filter_by.extend(clauses)

            return session.query(func.count(self.EmbeddingStore.id)).filter(*filter_by).scalar()

    def _get_slice(self, start: int, stop: int) -> List[Document]:
        """
        Retrieve a slice (start:stop) of documents, with filters.
        """
        length = stop - start
        combined_filter = self._merge_filters(None)
        with self._make_sync_session() as session:
            collection = self.get_collection(session)
            if not collection:
                raise ValueError("Collection not found")
            filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

            if combined_filter:
                if self.use_jsonb:
                    clause = self._create_filter_clause(combined_filter)
                    if clause is not None:
                        filter_by.append(clause)
                else:
                    clauses = self._create_filter_clause_json_deprecated(
                        combined_filter)
                    filter_by.extend(clauses)

            results = (
                session.query(self.EmbeddingStore)
                .filter(*filter_by)
                .order_by(self.EmbeddingStore.id)
                .offset(start)
                .limit(length)
                .all()
            )
            return [
                Document(id=r.id, page_content=r.document,
                         metadata=r.cmetadata)
                for r in results
            ]

    def __getitem__(self, key: Union[int, slice]) -> Union[Document, List[Document]]:
        """
        Enable vectorstore[0] and vectorstore[0:10] with filters.
        """
        if isinstance(key, int):
            if key < 0:
                key = self.count() + key
            docs = self._get_slice(key, key + 1)
            if not docs:
                raise IndexError("Index out of range")
            return docs[0]
        elif isinstance(key, slice):
            start = key.start or 0
            stop = key.stop
            if stop is None:
                raise IndexError("Slice stop must be defined")
            if start < 0 or stop < 0:
                total = self.count()
                start = total + start if start < 0 else start
                stop = total + stop if stop < 0 else stop
            return self._get_slice(start, stop)
        else:
            raise TypeError("Invalid argument type for slicing")

    # ASYNCHRONOUS METHODS

    async def apaginated_query_collection(
        self,
        session: AsyncSession,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> Sequence[Any]:
        """
        Async version of paginated_query_collection.
        """
        combined_filter = self._merge_filters(filter)
        collection = await self.aget_collection(session)
        if not collection:
            raise ValueError("Collection not found")
        filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

        if combined_filter:
            if self.use_jsonb:
                clause = self._create_filter_clause(combined_filter)
                if clause is not None:
                    filter_by.append(clause)
            else:
                clauses = self._create_filter_clause_json_deprecated(
                    combined_filter)
                filter_by.extend(clauses)

        stmt = (
            select(
                self.EmbeddingStore,
                self.distance_strategy(embedding).label("distance"),
            )
            .filter(*filter_by)
            .join(
                self.CollectionStore,
                self.EmbeddingStore.collection_id == self.CollectionStore.uuid,
            )
            .order_by(sqlalchemy.asc("distance"))
            .offset(offset)
            .limit(limit)
        )
        return (await session.execute(stmt)).all()

    async def apaginated_similarity_search_with_score_by_vector(
        self,
        session: AsyncSession,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Async similarity search w/ pagination & scores.
        """
        results = await self.apaginated_query_collection(session, embedding, limit, offset, filter)
        return self._results_to_docs_and_scores(results)

    async def apaginated_similarity_search_by_vector(
        self,
        session: AsyncSession,
        embedding: List[float],
        limit: int,
        offset: int = 0,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Async similarity search w/ pagination, docs only.
        """
        docs_and_scores = await self.apaginated_similarity_search_with_score_by_vector(
            session, embedding, limit, offset, filter
        )
        return _results_to_docs(docs_and_scores)

    async def aget_all(self, session: AsyncSession, filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Async retrieve all docs, applying filters.
        """
        combined_filter = self._merge_filters(filter)
        collection = await self.aget_collection(session)
        if not collection:
            raise ValueError("Collection not found")
        filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

        if combined_filter:
            if self.use_jsonb:
                clause = self._create_filter_clause(combined_filter)
                if clause is not None:
                    filter_by.append(clause)
            else:
                clauses = self._create_filter_clause_json_deprecated(
                    combined_filter)
                filter_by.extend(clauses)

        stmt = select(self.EmbeddingStore).filter(*filter_by)
        results = (await session.execute(stmt)).scalars().all()
        return [
            Document(id=str(r.id), page_content=r.document,
                     metadata=r.cmetadata)
            for r in results
        ]

    async def acount(self, session: AsyncSession) -> int:
        """
        Async count docs, applying default filters.
        """
        combined_filter = self._merge_filters(None)
        collection = await self.aget_collection(session)
        if not collection:
            raise ValueError("Collection not found")
        filter_by = [self.EmbeddingStore.collection_id == collection.uuid]

        if combined_filter:
            if self.use_jsonb:
                clause = self._create_filter_clause(combined_filter)
                if clause is not None:
                    filter_by.append(clause)
            else:
                clauses = self._create_filter_clause_json_deprecated(
                    combined_filter)
                filter_by.extend(clauses)

        stmt = select(func.count(self.EmbeddingStore.id)).filter(*filter_by)
        return (await session.execute(stmt)).scalar_one()
