from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.data_fetch import (
    get_literals_query,
    get_subjects_query,
    execute_query,
    test_connection,
)
from imaging_plaza_search.config import LABEL_PREDICATES_WEIGHTED

from rdflib import Graph, URIRef
import os
from dotenv import load_dotenv
import tempfile
from rapidfuzz import process, fuzz
from collections import defaultdict

load_dotenv()

app = FastAPI()

db_host = os.getenv("GRAPHDB_URL")
db_user = os.getenv("GRAPHDB_USER")
db_password = os.getenv("GRAPHDB_PASSWORD")
graph = os.getenv("GRAPHDB_GRAPH")
threshold = float(os.getenv("SEARCH_THRESHOLD"))

label_predicates = [pred for pred, _ in LABEL_PREDICATES_WEIGHTED]


if test_connection(db_host=db_host, db_user=db_user, db_password=db_password) is False:
    raise HTTPException(
        status_code=500,
        detail="Failed to connect to the GraphDB instance. Please check your configuration, maybe you are not on EPFL network.",
    )
else:
    print("Connection to GraphDB instance successful.")


def clean_uri(term: str) -> str:
    """
    Remove angle brackets from a URI string if present.
    """
    term_str = str(term)
    if term_str.startswith("<") and term_str.endswith(">"):
        return term_str[1:-1]
    return term_str

def normalize_results(rapid_out, triples):
    bindings = []
    for score, term, idx in rapid_out:
        s, p, o = triples[idx]
        bindings.append({
            "s": {
                "type": "uri",
                "value": s,
            }
        })
    return {
        "head": {"vars": ["s"]},
        "results": {"bindings": bindings},
    }




def sort_terms(results, value_to_uri, label_predicates):
    # Convert the list of (label, score, index) into a sorted list
    def get_weighted_score(index):
        uri = str(index)
        if uri not in value_to_uri:
            return 0

        weighted_sum = sum(
            weight
            for pred, weight in label_predicates
            if pred in value_to_uri[uri]
        )
        normalization = max(
            1,
            sum(
                len(value_to_uri[uri].get(pred, []))
                for pred, _ in label_predicates
                if pred in value_to_uri[uri]
            )
        )
        return weighted_sum / normalization

    # Sort results by weighted score (descending)
    return sorted(results, key=lambda tup: get_weighted_score(tup[2]), reverse=True)


@app.post("/v1/search")
def search(request: SearchRequest):
    try:
        top_terms = []
        value_to_uri = defaultdict(lambda: defaultdict(list))
        if request.search and request.search.strip() != "":
            # 1. Query the data
            query = get_literals_query(graph, request.filters)
            nt_data = execute_query(
                db_host, db_user, db_password, query, return_format="nt"
            )
            # 2. Write to temporary NT file
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".nt", delete=False
            ) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            clean_search = request.search.replace(" ", "")
            # 3. Parse RDF graph from file
            g = Graph()
            g.parse(tmpfile_path, format="nt")


            # Define predicates with associated weights for later sorting
            raw_triples = []
            for predicate in label_predicates:
                for s, p, o in g.triples((None, predicate, None)):
                    value_to_uri[str(s)][predicate].append(str(o)) #dont use append
                    raw_triples.append((str(s), str(p), str(o)))  # list append
            print(f"\n\n\n\n value_to_uri: \n\n\n\n")
            print(value_to_uri)
            metadata = []
            choices = []

            for uri, preds in value_to_uri.items():
                for pred, values in preds.items():
                    for val in values:
                        metadata.append((uri, pred, val))
                        choices.append(val)

            clean_search = request.search.replace(" ", "")
            print(f"\n\n\n\n choices: \n\n\n\n")
            print(choices)
            if clean_search:
                # 1. Fuzzy match mode
                raw_results = process.extract(
                    clean_search, #term to match
                    choices, #the dictionary in which to search
                    scorer=fuzz.partial_ratio,
                    processor=str.lower,
                    score_cutoff=threshold,
                    limit=None,
                )
                print(f"raw_results: {raw_results}")

                sorted_terms = sort_terms(raw_results, value_to_uri, LABEL_PREDICATES_WEIGHTED)
                print(f"\n\n\nsorted_terms: {sorted_terms}")

                

            return JSONResponse(content=normalize_results(sorted_terms, raw_triples))


        else:
            # 3. Return all subjects if no search term
            query = get_literals_query(graph, request.filters)
            nt_data = execute_query(
                db_host, db_user, db_password, query, return_format="nt"
            )
            # 2. Write to temporary NT file
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".nt", delete=False
            ) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            clean_search = request.search.replace(" ", "")
            # 3. Parse RDF graph from file
            g = Graph()
            g.parse(tmpfile_path, format="nt")

            # Define predicates with associated weights for later sorting
            raw_triples = []
            for predicate in label_predicates:
                for s, p, o in g.triples((None, predicate, None)):
                    value_to_uri[str(s)][predicate].append(str(o)) #dont use append
                    raw_triples.append((str(s), str(p), str(o)))  # list append
            unique_subjects = set(s for s, _, _ in raw_triples)

            bindings = []
            for s in unique_subjects:
                bindings.append({
                    "s": {
                        "type": "uri",
                        "value": s
                    }
                })

            return {
                "head": {"vars": ["s"]},
                "results": {"bindings": bindings}
            }


    except Exception as e:
        return JSONResponse(
            content={"error": f"Search failed: {str(e)}"},
            status_code=500,
        )
