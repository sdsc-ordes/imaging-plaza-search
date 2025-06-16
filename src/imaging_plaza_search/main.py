from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.data_fetch import get_data_from_graphdb
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


@app.post("/v1/search")
def search(request: SearchRequest):
    print(request)

    try:
        # Get RDF graph from GraphDB in N-Triples format
        nt_data = get_data_from_graphdb(db_host, db_user, db_password, request.filters, graph)

        if request.search:
            # Save to temporary file for Fuzon to read
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".nt", delete=False) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            # Initialize Fuzon matcher
            matcher = TermMatcher.from_files([tmpfile_path])
            top_terms = matcher.top(request.search, 10)

        else:
            g = Graph()
            g.parse(data=nt_data, format="nt")
            # If no search term, get all URIs from the (optionally filtered) graph
            qres = g.query("""
            PREFIX schema: <http://schema.org/>
                SELECT DISTINCT ?s WHERE { ?s ?p ?o .}
            """)
            top_terms = [row[0] for row in qres]  
            print("SPARQL query URIs:")
            for row in qres:
                print(str(row[0]))


        results = {
            "head": {
                "vars": ["s"]
            },
            "results": {
                "bindings": [
                    {
                        "s": {
                            "type": "uri",
                            "value": str(term)[1:-1] if str(term).startswith("<") and str(term).endswith(">") else str(term)
                        }
                    }
                    for term in top_terms
                ]
            }
        }

        print(results)
        return JSONResponse(content=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
