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
from imaging_plaza_search.utils import (clean_uri, format_results) 
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
        

        print(f"uri: {uri}, weighted_sum: {weighted_sum}, normalization: {normalization}")
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

            

            raw_triples = []
            choices = []

            for s, p, o in g.triples((None, None, None)):
                s_str, p_str, o_str = str(s), str(p), str(o)
                raw_triples.append((s_str, p_str, o_str))
                choices.append(o_str)

            clean_search = request.search.replace(" ", "")

            if clean_search:
                raw_results = process.extract(
                    clean_search,
                    choices,
                    scorer=fuzz.partial_ratio,
                    processor=str.lower,
                    score_cutoff=threshold,
                    limit=None,
                )

                print((len(raw_results)))
                sorted_terms = sort_terms(raw_results, value_to_uri, label_predicates)

            # Step 1: Collect scores per predicate per subject
                predicate_scores = defaultdict(lambda: defaultdict(list))  # subject -> predicate -> list of scores

                for label, score, idx in raw_results:
                    s, p, o = raw_triples[idx]

                    for predicate, weight in LABEL_PREDICATES_WEIGHTED:
                        if URIRef(p) == predicate:
                            weighted_score = score * weight
                            predicate_scores[s][predicate].append(weighted_score)
                print(f"Predicate scores: {predicate_scores}")
            # Step 2: Average scores per predicate, then sum for each subject
                summed_scores = {}
                for s, pred_dict in predicate_scores.items():
                    total = 0
                    for scores in pred_dict.values():
                        avg_score = sum(scores) / len(scores)
                        total += avg_score
                    summed_scores[s] = total

            # Step 3: Sort and format
                sorted_terms = sorted(
                    summed_scores.items(), key=lambda item: item[1], reverse=True
                )
                sorted_terms = [(s, score, idx) for idx, (s, score) in enumerate(sorted_terms)]

                print(f"Sorted terms: {sorted_terms}")

                return JSONResponse(content=format_results(sorted_terms))
 
                            



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
