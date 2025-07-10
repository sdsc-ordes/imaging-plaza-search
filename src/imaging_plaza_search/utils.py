from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest
from imaging_plaza_search.config import LABEL_PREDICATES_WEIGHTED


def clean_uri(term: str) -> str:
    """
    Remove angle brackets from a URI string if present.
    """
    term_str = str(term)
    if term_str.startswith("<") and term_str.endswith(">"):
        return term_str[1:-1]
    return term_str



def format_results(sorted_terms, ):
    bindings = []

    for uri, score, idx in sorted_terms:
        bindings.append({
            "s": {
                "type": "uri",
                "value": uri
            }
        })

    result = {
        "head": {"vars": ["s"]},
        "results": {"bindings": bindings},
    }

    print(result)
    return result
