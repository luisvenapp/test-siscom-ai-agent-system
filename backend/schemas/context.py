from pydantic import BaseModel
from pydantic import root_validator
from typing import Optional, List


class MetadataSchema(BaseModel):
    id: str
    topic: Optional[str] = "trini"
    source: Optional[str]
    page: Optional[int] = None


class DocumentSchema(BaseModel):
    id: str
    page_content: str
    metadata: MetadataSchema


class PaginatedResponseSchema(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[DocumentSchema]


class BulkInsertRequestSchema(BaseModel):
    details: str
    documents: List[DocumentSchema]


class BulkDeleteRequestSchema(BaseModel):
    ids: List[str]


class SourcesResponse(BaseModel):
    """
    Response schema for the /sources endpoint.
    """
    sources: List[str]
