from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.data_fetch import get_data_from_graphdb
from pyfuzon import TermMatcher
import os
from dotenv import load_dotenv
import tempfile

load_dotenv()

app = FastAPI()

@app.post("/search")
def search(request: SearchRequest):
    db_host = os.getenv("GRAPHDB_URL")
    db_user = os.getenv("GRAPHDB_USER")
    db_password = os.getenv("GRAPHDB_PASSWORD")

    try:
        # Get RDF graph from GraphDB in N-Triples format
        nt_data = get_data_from_graphdb(db_host, db_user, db_password, request.filters)

        # Save to temporary file for Fuzon to read
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.nt', delete=False) as tmpfile:
            tmpfile.write(nt_data)
            tmpfile_path = tmpfile.name

        # Initialize Fuzon matcher
        matcher = TermMatcher.from_files([tmpfile_path])

        top_terms = matcher.top(request.search, 10)

        def clean_label(label):
            # If label is an rdflib Literal or similar, get lexical value, else strip quotes if present
            try:
                return label.value  # if this fails, except will catch it
            except AttributeError:
                return label.strip('"')

        # Return cleaned term labels and URIs only
        results = [
            {"label": clean_label(term.label), "uri": str(term.uri)}
            for term in top_terms
        ]

        return JSONResponse(content=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

