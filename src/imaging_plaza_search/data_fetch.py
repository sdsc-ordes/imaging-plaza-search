"""Fetches data from a GraphDB SPARQL endpoint based on provided filters."""

from typing import List, Optional
from imaging_plaza_search.models import Filter
from SPARQLWrapper import SPARQLWrapper, N3
from urllib.error import HTTPError
# from rdflib import Graph # Graph is not used directly


def get_data_from_graphdb(
    db_host: str,
    db_user: str,
    db_password: str,
    filters: Optional[List[Filter]],
    graph_uri: str = "https://imaging-plaza.epfl.ch/finalGraph",
) -> str:
    """
    Queries a GraphDB repository to fetch data in N-Triples format based on filters.

    The function constructs a SPARQL CONSTRUCT query to retrieve triples
    related to schema:SoftwareSourceCode entries that match the given filters.
    It fetches a subgraph around the matched entities.

    Args:
        db_host: The URL of the SPARQL endpoint (e.g., "http://localhost:7200/repositories/myrepo").
        db_user: Username for GraphDB authentication.
        db_password: Password for GraphDB authentication.
        filters: An optional list of Filter objects. If None or empty, or if filters
                 have no selected values, the function may return an empty string
                 or a less filtered result depending on the query logic.
                 Currently, if `filters` is None or empty, it returns an empty string early.
        graph_uri: The URI of the graph to query within GraphDB.

    Returns:
        A string containing the RDF data in N-Triples format.
        Returns an empty string if no filters are provided or if the query
        otherwise results in no data.

    Raises:
        RuntimeError: If an HTTPError occurs during the SPARQL query execution,
                      indicating issues like connection problems or authentication failure.
    """
    if not filters: # Early exit if no filters are provided.
        return ""

    conditions: List[str] = []
    for item_filter in filters: # Renamed 'filter' to 'item_filter' to avoid shadowing built-in
        if item_filter.selected:
            # Ensuring values are properly quoted for the SPARQL IN clause
            values: str = ", ".join(f'"{val}"' for val in item_filter.selected)
            condition: str = (
                f"?s <{item_filter.schema}> ?{item_filter.key}_val. " # Use valid variable names
                f"FILTER(?{item_filter.key}_val IN ({values}))"
            )
            conditions.append(condition)

    if not conditions: # If filters were present but all had empty 'selected' lists
        return ""

    filter_conditions: str = " ".join(conditions)

    # Note: The original query had ?s {filter.schema} ?{filter.key}.
    # This is changed to ?s <{filter.schema}> ?{filter.key}_val for correctness,
    # as filter.schema is a URI and filter.key might not be a valid variable name part.
    # The variable used in FILTER (?{filter.key}_val) must match the one in the triple pattern.
    query: str = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX schema: <http://schema.org/>
    PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
    PREFIX fuzon: <http://example.org/fuzon#>

    CONSTRUCT 
    {{
        ?s fuzon:searchIndexPredicate ?literal .
        ?s ?p ?o .
        ?o ?p2 ?o2 .
        ?o2 ?p3 ?o3 .
    }}
    WHERE {{
        GRAPH <{graph_uri}> {{
            ?s rdf:type schema:SoftwareSourceCode ;
            ?p ?o .

            OPTIONAL {{ 
                ?o ?p2 ?o2 .
                OPTIONAL {{ ?o2 ?p3 ?o3 }} 
            }}

            FILTER(isLiteral(?o))

            BIND(str(?o) as ?literal)
            {filter_conditions}
        }}
    }}
    """

    sparql = SPARQLWrapper(db_host)
    sparql.setQuery(query)
    sparql.setReturnFormat(N3)
    sparql.setCredentials(user=db_user, passwd=db_password)
    sparql.addCustomHttpHeader("Accept", "application/n-triples")
    # print(query) # Commented out print statement, typically for debugging

    try:
        result_bytes: bytes = sparql.query().convert()
        return result_bytes.decode("utf-8")
    except HTTPError as e:
        # Log the error or handle it more gracefully if needed
        raise RuntimeError(f"HTTPError during SPARQL query: {e.code} {e.reason}. Query:\n{query}")
    except Exception as e:
        # Catch other potential errors during query conversion or decoding
        raise RuntimeError(f"An unexpected error occurred during SPARQL query execution: {e}. Query:\n{query}")
