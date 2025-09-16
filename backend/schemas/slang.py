from typing import Any, Dict
from pydantic import BaseModel, Field

class SlangAnalysis(BaseModel):
    """
    Schema for the slang analysis response, including a unique ID for each country.
    """
    id: str = Field(..., description="Unique identifier for the country's slang analysis (lowercase country name)")
    country: str = Field(..., description="Country for which slang analysis is performed")
    representative_phrases: list[str] = Field(default=[], description="List of representative phrases or slang")
    keywords: list[str] = Field(default=[], description="List of keywords related to slang")
    main_topics: list[str] = Field(default=[], description="List of main topics covered in the slang analysis")
    cultural_synthesis: str = Field(default="", description="Cultural synthesis or summary of the slang")

    @staticmethod
    def from_raw_data(country: str, raw_data: dict):
        """
        Construct a SlangAnalysis object from the raw dictionary response.
        """
        return SlangAnalysis(
            id=country.lower(),  # Use lowercase country name as ID
            country=country,
            representative_phrases=raw_data.get("representative_phrases", []),
            keywords=raw_data.get("keywords", []),
            main_topics=raw_data.get("main_topics", []),
            cultural_synthesis=raw_data.get("cultural_synthesis", "")
        )