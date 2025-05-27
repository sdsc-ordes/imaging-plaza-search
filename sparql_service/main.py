from fastapi import FastAPI
from models import SearchRequest
from query_builder import build_sparql_query

app = FastAPI()

@app.post("/query")

def get_data_from_graphdb(db_host: str, 
                          db_user: str, 
                          db_password: str,
                          softwareURI: str,
                          graph:str) -> bytes:
    """
    Get data from GraphDB.

    Args:
        db_host: The host URL of the GraphDB.
        db_user: The username for authentication.
        db_password: The password for authentication.
        softwareURI: Indentifier of target software
        graph: Graph where the entry is located

    Returns:
        The data as a bytes object.
    """

    get_relevant_software_query: str = """
    PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
    CONSTRUCT {{
    ?subject imag:graph <{graph}>  .
    ?subject ?predicate ?object .
    ?object ?p ?o .
    ?o ?something ?else .
    }} WHERE {{
        GRAPH <{graph}> {{
        {{?subject ?predicate ?object .
        filter(?subject = <{softwareURI}> )
        OPTIONAL {{ ?object ?p ?o . 
        OPTIONAL {{?o ?something ?else}}}}
                }}}}}}
    """.format(softwareURI=softwareURI, graph=graph) 

    sparql = SPARQLWrapper(db_host)
    sparql.setQuery(get_relevant_software_query)
    sparql.setReturnFormat(TURTLE)
    sparql.setCredentials(user=db_user, passwd=db_password)
    results = sparql.query().convert()
    return results


def generate_query(request: SearchRequest):
    sparql_query = build_sparql_query(request.search, request.filters)
    return {"sparql": sparql_query}
