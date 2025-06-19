from typing import List, Optional
from imaging_plaza_search.models import Filter
from SPARQLWrapper import SPARQLWrapper, N3, JSON
from urllib.error import HTTPError
from rdflib import Graph


def build_filter_conditions(filters: Optional[List[Filter]]) -> str:
    if not filters:
        return ""

    conditions = []
    for filter in filters:
        values = ", ".join(f'"{val}"' for val in filter.value)
        condition = (
            f"?s {filter.schema_key} ?{filter.key}. FILTER(?{filter.key} IN ({values}))"
        )
        conditions.append(condition)
    return " ".join(conditions)


def execute_query(
    db_host: str, db_user: str, db_password: str, query: str, return_format: str = "nt"
) -> str:
    sparql = SPARQLWrapper(db_host)
    sparql.setQuery(query)
    sparql.setCredentials(user=db_user, passwd=db_password)

    if return_format == "nt":
        sparql.setReturnFormat(N3)
        sparql.addCustomHttpHeader("Accept", "application/n-triples")
    else:
        sparql.setReturnFormat(JSON)

    try:
        result_bytes = sparql.query().convert()
        return (
            result_bytes.decode("utf-8")
            if isinstance(result_bytes, bytes)
            else result_bytes
        )
    except HTTPError as e:
        raise RuntimeError(f"HTTPError during SPARQL query: {e}")


def get_fuzon_query(graph: str, filters: Optional[List[Filter]]) -> str:
    filter_conditions = build_filter_conditions(filters)
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX schema: <http://schema.org/>
    PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
    PREFIX fuzon: <http://example.org/fuzon#>

    CONSTRUCT {{
        ?s rdfs:label ?literal .
    }}
    WHERE {{
        GRAPH <{graph}> {{
            ?s rdf:type schema:SoftwareSourceCode ;
               ?p ?o .

            OPTIONAL {{ ?o ?p2 ?o2 .
                       OPTIONAL {{ ?o2 ?p3 ?o3 }} }}

            FILTER(isLiteral(?o))
            BIND(str(?o) AS ?literal)
            {filter_conditions}
        }}
    }}
    """


def get_subjects_query(graph: str) -> str:
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX schema: <http://schema.org/>

    SELECT DISTINCT ?s
    WHERE {{
        GRAPH <{graph}> {{
            ?s rdf:type schema:SoftwareSourceCode .
        }}
    }}
    """


def test_connection(db_host: str, db_user: str, db_password: str) -> bool:
    sparql = SPARQLWrapper(db_host)
    sparql.setCredentials(user=db_user, passwd=db_password)
    sparql.setQuery("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")
    sparql.setReturnFormat(JSON)

    try:
        sparql.query()
        return True
    except HTTPError as e:
        raise RuntimeError(
            f"HTTPError during connection test: {e}. Ensure your GRAPHDB_URL ends in /repositories/..."
        )
