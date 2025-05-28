from typing import List, Optional
from models import Filter

from SPARQLWrapper import SPARQLWrapper, N3
from urllib.error import HTTPError  # Import HTTPError


from rdflib import Graph

def get_data_from_graphdb(
    db_host: str, 
    db_user: str, 
    db_password: str,
    filters: Optional[List[Filter]],
    graph: str = 'https://imaging-plaza.epfl.ch/finalGraph'
) -> str:
    if not filters:
        return ""

    conditions = []
    for filter in filters:
        if filter.selected:
            values = ', '.join(f'"{val}"' for val in filter.selected)
            condition = f'?s {filter.schema} ?{filter.key}. FILTER(?{filter.key} IN ({values}))'
            conditions.append(condition)

    filter_conditions = ' '.join(conditions)

    query = f"""
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
        result_bytes = sparql.query().convert()
        return result_bytes.decode('utf-8')  
    except HTTPError as e:
        raise RuntimeError(f"HTTPError during SPARQL query: {e}")
