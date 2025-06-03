"""Pydantic models for search requests and filters."""

from pydantic import BaseModel
from typing import List, Optional
# import json # Not strictly needed here anymore after previous refactor


class Filter(BaseModel):
    """
    Represents a filter criterion for the search.

    Attributes:
        key: The field key to filter on (e.g., "modality").
        schema: The schema or predicate URI associated with the key.
        selected: A list of selected string values for the filter.
    """
    key: str
    schema: str
    selected: List[str]


class SearchRequest(BaseModel):
    """
    Represents a search request from the client.

    Attributes:
        search: The search term or query string.
        filters: An optional JSON string representing a list of Filter objects.
                 This is expected to be parsed into List[Filter] by the endpoint.
                 Example: '[{"key": "modality", "schema": "...", "selected": ["value1"]}]'
    """
    search: str
    filters: Optional[str] = None
