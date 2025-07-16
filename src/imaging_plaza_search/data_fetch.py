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


def get_literals_query(graph: str, filters: Optional[List[Filter]]) -> str:
    filter_conditions = build_filter_conditions(filters)
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX schema: <http://schema.org/>
    PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
    PREFIX fuzon: <http://example.org/fuzon#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    CONSTRUCT {{
        ?s ?p ?o
    }}
    WHERE {{
        GRAPH <{graph}> {{
        ?s ?p ?o .
            ?s rdf:type schema:SoftwareSourceCode ;
            #    OPTIONAL {{?s rdfs:label ?label; }}
            #    OPTIONAL {{?s schema:name ?name ; }}
            FILTER(isLiteral(?o))
               .
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
