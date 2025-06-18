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
from rdflib import Graph
from pyfuzon import TermMatcher
import os
from dotenv import load_dotenv
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
            query = get_fuzon_query(graph, request.filters)
            nt_data = execute_query(
                db_host, db_user, db_password, query, return_format="nt"
            )

            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".nt", delete=False
            ) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            matcher = TermMatcher.from_files([tmpfile_path])
            threshold = 0.8
            all_terms = matcher.rank(request.search)
            top_terms = [term.uri for term in all_terms if matcher.score(request.search)[term] >= threshold]


        else:
            query = get_subjects_query(graph)
            result_json = execute_query(
                db_host, db_user, db_password, query, return_format="json"
            )

            top_terms = [
                binding["s"]["value"]
                for binding in result_json["results"]["bindings"]
                if "s" in binding
            ]

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
        raise HTTPException(status_code=500, detail=str(e))
