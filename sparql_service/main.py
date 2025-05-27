from fastapi import FastAPI
from models import SearchRequest
from query_builder import build_sparql_query

app = FastAPI()

@app.post("/query")
def generate_query(request: SearchRequest):
    sparql_query = build_sparql_query(request.search, request.filters)
    return {"sparql": sparql_query}
