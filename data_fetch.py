from typing import List, Optional
from models import Filter

from SPARQLWrapper import SPARQLWrapper
from urllib.error import HTTPError  # Import HTTPError


def get_data_from_graphdb(db_host: str, 
                          db_user: str, 
                          db_password: str,
                          filters: Optional[List[Filter]] ,
                          graph:str = 'https://imaging-plaza.epfl.ch/finalGraph') -> bytes:
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

    if not filters:
        return ""

    conditions = []
    for filter in filters:
        if filter.selected:
            values = ', '.join(f'"{val}"' for val in filter.selected)
            condition = f'?s {filter.schema} ?{filter.key}. FILTER(?{filter.key} IN ({values}))'
            conditions.append(condition)

    filter_conditions = ' '.join(conditions)
    
    get_relevant_software_query: str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX schema: <http://schema.org/>
        PREFIX imag: <https://imaging-plaza.epfl.ch/ontology#>
        SELECT DISTINCT ?s
        WHERE {{
        GRAPH <{graph}> {{
            ?s rdf:type schema:SoftwareSourceCode.
            {filter_conditions}
        }}
        }}""".format( graph=graph, filter_conditions=filter_conditions) 

    sparql = SPARQLWrapper(db_host)
    sparql.setQuery(get_relevant_software_query)
    sparql.setReturnFormat('json-ld')
    sparql.setCredentials(user=db_user, passwd=db_password)
    sparql.addCustomHttpHeader("Accept", "application/sparql-results+json")

    try:
        print("Executing SPARQL query...")
        print(f"Query: {get_relevant_software_query}")
        results = sparql.query().convert()
        print("Query executed successfully.")
        print(f"Results: {results}")
        return results
    except HTTPError as e:
        print(f"HTTP error occurred: {e}")
        print(f"DB Host: {db_host}")
        print(f"DB User: {db_user}")
        print(f"DB Password: {db_password}")
        print(f"Graph: {graph}")
        print(f"Query: {get_relevant_software_query}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise