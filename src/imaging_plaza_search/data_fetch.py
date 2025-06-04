from typing import List, Optional
from imaging_plaza_search.models import Filter
from SPARQLWrapper import SPARQLWrapper, N3
from urllib.error import HTTPError  # Import HTTPError
from rdflib import Graph


from typing import List, Optional
from rdflib import Graph
from SPARQLWrapper import SPARQLWrapper, N3
from urllib.error import HTTPError


def get_data_from_graphdb(
    db_host: str,
    db_user: str,
    db_password: str,
    filters: Optional[List[Filter]],
    graph: str = "https://imaging-plaza.epfl.ch/finalGraph",
) -> str:
    """
    Constructs and executes a SPARQL CONSTRUCT query against a GraphDB instance,
    using the provided filters, and returns the result as a UTF-8 decoded string.

    Parameters:
        db_host (str): The GraphDB endpoint URL.
        db_user (str): The username for authentication.
        db_password (str): The password for authentication.
        filters (Optional[List[Filter]]): A list of filter objects to build the query.
        graph (str): The graph IRI to query.

    Returns:
        str: The SPARQL CONSTRUCT query result in N-Triples format as a UTF-8 string.

    Raises:
        RuntimeError: If an HTTPError occurs during the SPARQL query execution.
    """
    if not filters:
        return ""

    conditions: List[str] = []
    for filter in filters:
        if filter.selected:
            values = ", ".join(f'"{val}"' for val in filter.selected)
            condition = (
                f"?s {filter.schema} ?{filter.key}. FILTER(?{filter.key} IN ({values}))"
            )
            conditions.append(condition)

    filter_conditions: str = " ".join(conditions)

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
        GRAPH <{graph}> {{
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
    print(query)
    try:
        result_bytes: bytes = sparql.query().convert()
        return result_bytes.decode("utf-8")
    except HTTPError as e:
        raise RuntimeError(f"HTTPError during SPARQL query: {e}")
