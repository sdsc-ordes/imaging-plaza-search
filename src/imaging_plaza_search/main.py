from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.data_fetch import (
    get_fuzon_query,
    get_subjects_query,
    execute_query,
    test_connection
)
from rdflib import Graph, URIRef
from pyfuzon import TermMatcher
import os
from dotenv import load_dotenv
import tempfile
from rapidfuzz import process, fuzz
import tempfile

load_dotenv()

app = FastAPI()

db_host = os.getenv("GRAPHDB_URL")
db_user = os.getenv("GRAPHDB_USER")
db_password = os.getenv("GRAPHDB_PASSWORD")
graph = os.getenv("GRAPHDB_GRAPH")

if test_connection(db_host=db_host, db_user=db_user, db_password=db_password) is False:
    raise HTTPException(
        status_code=500,
        detail="Failed to connect to the GraphDB instance. Please check your configuration, maybe you are not on EPFL network.",
    )
else:
    print("Connection to GraphDB instance successful.")


@app.post("/v1/search")

def search(request: SearchRequest):
    try:
        if request.search:
            # 1. Query the data
            query = get_fuzon_query(graph, request.filters)
            nt_data = execute_query(
                db_host, db_user, db_password, query, return_format="nt"
            )

            # 2. Write to temporary NT file
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".nt", delete=False) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name
            
            matcher = TermMatcher.from_files([tmpfile_path])
            threshold = float(os.getenv("SEARCH_THRESHOLD"))
            clean_search = request.search.replace(" ", "")

            # 3. Parse RDF graph from file
            g = Graph()
            g.parse(tmpfile_path, format="nt")

            # 4. Build mapping of labels to URIs
            label_to_uri = {}
            for s, p, o in g.triples((None, URIRef("http://schema.org/name") , None)):
                label_to_uri[str(o)] = str(s)

            # 5. Clean search input and fuzzy match with rapidfuzz
            clean_search = request.search.replace(" ", "")
            if clean_search:
                # 1. Fuzzy match mode
                raw_results = process.extract(
                    clean_search,
                    label_to_uri,
                    scorer=fuzz.partial_ratio,
                    processor=str.lower,
                    score_cutoff=threshold,
                    limit=None,
                )
                print(len(raw_results), "raw results found")
                # 2. Just extract the URI part
                top_terms = [uri for uri, _, _ in raw_results]

            else:
                # 3. Return all subjects if no search term
                query = get_subjects_query(graph)
                result_json = execute_query(
                    db_host, db_user, db_password, query, return_format="json"
                )

                # 4. Pull URIs from the JSON results
                top_terms = [
                    binding["s"]["value"]
                    for binding in result_json["results"]["bindings"]
                    if "s" in binding
                ]

            # 5. Normalize into SPARQL-style result format
            results = {
                "head": {"vars": ["s"]},
                "results": {
                    "bindings": [
                        {
                            "s": {
                                "type": "uri",
                                "value": (
                                    str(term)[1:-1]
                                    if str(term).startswith("<") and str(term).endswith(">")
                                    else str(term)
                                ),
                            }
                        }
                        for term in top_terms
                    ]
                },
            }

        
        return JSONResponse(content=results)

    except Exception as e:
        return JSONResponse(
            content={"error": f"Search failed: {str(e)}"},
            status_code=500,
        )