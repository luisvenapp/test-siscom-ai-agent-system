from pydantic import BaseModel, Field
from typing import List


class SlangItem(BaseModel):
    """
    Represents a single slang item found by the get_country_slang tool.
    """
    title: str = Field(..., description="The title of the search result.")
    snippet: str = Field(..., description="A short summary or snippet from the page.")
    link: str = Field(..., description="The URL to the source page.")


class CountrySlangResponse(BaseModel):
    """
    The response model for the get_country_slang tool, containing a list of slang items.
    """
    slang_items: List[SlangItem] = Field(..., description="A list of slang items found.")