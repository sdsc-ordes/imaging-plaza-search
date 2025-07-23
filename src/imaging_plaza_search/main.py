from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.data_fetch import (
    get_literals_query,
    execute_query,
    test_connection,
)
from imaging_plaza_search.config import LABEL_PREDICATES_WEIGHTED
from imaging_plaza_search.utils import clean_uri, format_results
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

@app.get("/")
def welcome():
    return {"Welcome to the Imaging Plaza Search service v0.1.0"}


@app.post("/v1/search")
def search(request: SearchRequest):
    try:
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

            raw_triples = []
            choices = []

            for s, p, o in g.triples((None, None, None)):
                s_str, p_str, o_str = str(s), str(p), str(o)
                raw_triples.append((s_str, p_str, o_str))
                choices.append(o_str)

            if clean_search:
                raw_results = process.extract(
                    clean_search,
                    choices,
                    scorer=fuzz.partial_ratio,
                    processor=str.lower,
                    score_cutoff=threshold,
                    limit=None,
                )

                # Step 1: Collect scores per predicate per subject
                predicate_scores = defaultdict(lambda: defaultdict(list))

                for label, score, idx in raw_results:
                    s, p, o = raw_triples[idx]

                    for predicate, weight in LABEL_PREDICATES_WEIGHTED:
                        if URIRef(p) == predicate:
                            weighted_score = score * weight
                            predicate_scores[s][predicate].append(weighted_score)
                # Step 2: Average scores per predicate, then sum for each subject
                summed_scores = {}
                for s, pred_dict in predicate_scores.items():
                    total = 0
                    for scores in pred_dict.values():
                        avg_score = sum(scores) / len(scores)
                        total += avg_score
                    summed_scores[s] = total

                # Step 3: Sort and format
                weighted_score_threshold = 50
                sorted_terms = sorted(
                    (
                        (s, score)
                        for s, score in summed_scores.items()
                        if score >= weighted_score_threshold
                    ),
                    key=lambda item: item[1],
                    reverse=True,
                )

                sorted_terms = [
                    (s, score, idx) for idx, (s, score) in enumerate(sorted_terms)
                ]

                return JSONResponse(content=format_results(sorted_terms))

        else:
            query = get_literals_query(graph, request.filters)
            nt_data = execute_query(
                db_host, db_user, db_password, query, return_format="nt"
            )
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".nt", delete=False
            ) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            clean_search = request.search.replace(" ", "")
            g = Graph()
            g.parse(tmpfile_path, format="nt")

            raw_triples = []
            for predicate in label_predicates:
                for s, p, o in g.triples((None, predicate, None)):
                    value_to_uri[str(s)][predicate].append(str(o))
                    raw_triples.append((str(s), str(p), str(o)))
            unique_subjects = set(s for s, _, _ in raw_triples)

            bindings = []
            for s in unique_subjects:
                bindings.append({"s": {"type": "uri", "value": s}})

            return {"head": {"vars": ["s"]}, "results": {"bindings": bindings}}

    except Exception as e:
        return JSONResponse(
            content={"error": f"Search failed: {str(e)}"},
            status_code=500,
        )
