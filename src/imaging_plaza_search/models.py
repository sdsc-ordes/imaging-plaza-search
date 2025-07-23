from pydantic import BaseModel, Field
from typing import List, Optional


class Filter(BaseModel):
    key: str
    schema_key: str
    value: List[str]


class SearchRequest(BaseModel):
    search: str
    filters: Optional[List[Filter]] = Field(default_factory=list)
