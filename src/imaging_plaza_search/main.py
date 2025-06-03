from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import Filter # Changed SearchRequest to Filter
from imaging_plaza_search.data_fetch import get_data_from_graphdb
import os
from unittest.mock import MagicMock # For dummy TermMatcher if import fails

# Try to import pyfuzon, provide a mock if it fails (e.g. due to Python version incompatibility)
# This allows tests to run by mocking TermMatcher at the point of use.
try:
    from pyfuzon import TermMatcher, Term
except ImportError:
    # If PYTEST_RUNNING is set, assume we are in a test environment
    # and can use a mock. Otherwise, re-raise the error.
    if os.getenv("PYTEST_RUNNING") == "1":
        TermMatcher = MagicMock()
        Term = MagicMock() # pyfuzon.Term is used in test_main.py to create mock pyfuzon terms
    else:
        # In a non-test environment, the import error is critical
        print("Error: pyfuzon could not be imported. Please ensure it's installed and compatible.")
        raise

from dotenv import load_dotenv
import tempfile
import json # Added json import
from typing import List, Optional # Added typing imports
from pydantic import parse_obj_as # Added pydantic import

load_dotenv()

app = FastAPI()


@app.get("/v1/search") # Changed from app.post("/search")
def search_items(search_term: str, filters: Optional[str] = Query(None)): # Changed function signature and parameters
    """
    Searches for terms in a graph database based on a search string and optional filters.

    Args:
        search_term (str): The term to search for.
        filters (Optional[str]): A JSON string representing a list of filter objects.
                                 Each filter specifies a key, schema, and selected values
                                 to narrow down the search space. Defaults to None.

    Returns:
        JSONResponse: A list of search results, where each result has a "label" and "uri".
                      Raises HTTPException for errors (e.g., invalid filter format, database issues).
    """
    db_host = os.getenv("GRAPHDB_URL")
    db_user = os.getenv("GRAPHDB_USER")
    db_password = os.getenv("GRAPHDB_PASSWORD")

    parsed_filters: Optional[List[Filter]] = None
    if filters:
        try:
            parsed_filters = parse_obj_as(List[Filter], json.loads(filters))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for filters")
        except Exception as e: # Catch pydantic validation error
            raise HTTPException(status_code=400, detail=f"Invalid filter structure: {e}")


    try:
        # Get RDF graph from GraphDB in N-Triples format
        nt_data = get_data_from_graphdb(db_host, db_user, db_password, parsed_filters) # Use parsed_filters

        # Save to temporary file for Fuzon to read
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".nt", delete=False
        ) as tmpfile:
            tmpfile.write(nt_data)
            tmpfile_path = tmpfile.name

        # Initialize Fuzon matcher
        matcher = TermMatcher.from_files([tmpfile_path])

        top_terms = matcher.top(search_term, 10) # Use search_term

        def clean_label(label):
            """
            Cleans a label, typically an RDF term, to extract its string representation.

            It first tries to access a `.value` attribute, common for RDF library literal types.
            If that fails (e.g., it's a plain string or a URI), it falls back to stripping
            any surrounding double quotes from the string representation of the label.

            Args:
                label: The label to clean. Can be an RDF term object or a string.

            Returns:
                str: The cleaned string representation of the label.
            """
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
        # Clean up temporary file if it was created
        if 'tmpfile_path' in locals() and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure temporary file is always cleaned up if it exists
        if 'tmpfile_path' in locals() and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
