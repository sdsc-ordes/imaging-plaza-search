from pydantic import BaseModel
from typing import List, Optional

class Filter(BaseModel):
    key: str
    schema: str
    selected: List[str]

class SearchRequest(BaseModel):
    search: str
    filters: Optional[List[Filter]] = []
