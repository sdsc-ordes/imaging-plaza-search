from typing import List, Optional
from models import Filter
from pyfuzon.matcher import TermMatcher

import os
from pathlib import Path

data_path = str(Path(__file__).resolve().parent.parent / "searchable-plaza.nt")
TOP_N_MATCHES = 5

def extract_relevant_terms(ontology_path: str, query: str, n: int = 5) -> List[str]:
    matcher = TermMatcher.from_files([ontology_path])
    return [match[0] for match in matcher.top(query, n)]

def build_search_condition(search: str) -> str:
    matched_uris = extract_relevant_terms(data_path, search, TOP_N_MATCHES)
    if not matched_uris:
        return ""
    uris = ' '.join(f"<{uri}>" for uri in matched_uris)
    return f"?s schema:identifier ?match_uri. FILTER(?match_uri IN ({uris}))"

def build_filter_conditions(filters: Optional[List[Filter]]) -> str:
    if not filters:
        return ""

    conditions = []
    for filter in filters:
        if filter.selected:
            values = ', '.join(f'"{val}"' for val in filter.selected)
            condition = f'?s {filter.schema} ?{filter.key}. FILTER(?{filter.key} IN ({values}))'
            conditions.append(condition)

    return ' '.join(conditions)

def build_sparql_query(search: str, filters: Optional[List[Filter]]) -> str:
    search_condition = build_search_condition(search)
    filter_conditions = build_filter_conditions(filters)

    query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX schema: <http://schema.org/>
PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
SELECT DISTINCT ?s
WHERE {{
  GRAPH <https://imaging-plaza.epfl.ch/finalGraph> {{
    {search_condition}
    ?s rdf:type schema:SoftwareSourceCode.
    {filter_conditions}
  }}
}}"""
    return query
