from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SearchRequest
from data_fetch import get_data_from_graphdb
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Optional: allow CORS if needed (e.g., frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/search")
def search(request: SearchRequest):
    db_host = os.getenv("GRAPHDB_URL")
    db_user = os.getenv("GRAPHDB_USER")
    db_password = os.getenv("GRAPHDB_PASSWORD")

    try:
        results = get_data_from_graphdb(db_host, db_user, db_password, request.filters)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
