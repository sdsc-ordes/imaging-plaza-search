"""
Main FastAPI application for the Imaging Plaza Search service.

Provides an API endpoint to search for imaging-related software and resources
based on keywords and filters.
"""

import logging # Added for logging
from fastapi import FastAPI, HTTPException, Depends, Request # Added Request
# CORSMiddleware is imported but not used; can be removed if no CORS setup is intended.
# from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from imaging_plaza_search.models import SearchRequest, Filter
from imaging_plaza_search.data_fetch import get_data_from_graphdb
from pyfuzon import TermMatcher # type: ignore # Assuming pyfuzon might not have stubs
from pyfuzon.match import Term # type: ignore # For type hinting term.label
import os
from dotenv import load_dotenv
import tempfile
import json
from pydantic import parse_obj_as, ValidationError
from typing import List, Optional, Dict, Any, Union

load_dotenv()

app = FastAPI(
    title="Imaging Plaza Search API",
    description="API for searching imaging-related resources using Fuzon.",
    version="1.0.0"
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example of how CORS middleware would be added if needed:
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )

# Custom HTTPException Handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles HTTPExceptions raised throughout the application.

    Returns a JSON response with the original status code and a structured
    error message including a 'source' field.
    """
    # The 'source' here indicates that the error was an anticipated one,
    # handled via raising an HTTPException. The detail of the error (exc.detail)
    # should ideally contain context about where it originated.
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "source": "api_handled_error"},
    )

# Generic Exception Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handles any uncaught exceptions in the application.

    Logs the full exception for debugging and returns a generic 500 error
    JSON response with a 'source' field.
    """
    logger.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "source": "unhandled_system_error"},
    )


@app.get("/v1/search", response_model=List[Dict[str, str]])
def search(request: SearchRequest = Depends()) -> JSONResponse: # Note: Return type is simplified, actual return is JSONResponse or raises Exception
    """
    Performs a search for imaging resources based on a query and optional filters.

    The endpoint fetches relevant data from a GraphDB instance, uses Fuzon for
    semantic matching of the search term against the data, and returns the
    top matching terms with their labels and URIs.

    Args:
        request: A SearchRequest object populated from query parameters.
                 `request.search` is the user's search term.
                 `request.filters` is an optional JSON string representing a list of
                 Filter objects (e.g., '[{"key": "modality", "schema": "...", "selected": ["value1"]}]').

    Returns:
        JSONResponse: A list of dictionaries, where each dictionary contains
                      the 'label' and 'uri' of a matching term.
                      Example: [{"label": "Some Tool", "uri": "http://example.com/tool/1"}]

    Raises:
        HTTPException:
            - 400: If the 'filters' query parameter is not a valid JSON string or
                   if its structure is invalid according to the Filter model.
            - 500: If there's an internal server error during data fetching,
                   processing, or any other unexpected issue.
            - 503: If GraphDB connection details (URL, user, password) are not configured.
    """
    # The source of errors will be indicated in the detail of HTTPException
    # or by the generic handler's "source" field.
    db_host: Optional[str] = os.getenv("GRAPHDB_URL")
    db_user: Optional[str] = os.getenv("GRAPHDB_USER")
    db_password: Optional[str] = os.getenv("GRAPHDB_PASSWORD")

    if not all([db_host, db_user, db_password]):
        # Detail provides specific information about the error's origin.
        raise HTTPException(status_code=503, detail="Configuration Error: GraphDB connection details (URL, user, or password) are missing.")

    parsed_filters: Optional[List[Filter]] = []
    if request.filters:
        try:
            parsed_filters = parse_obj_as(List[Filter], json.loads(request.filters))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Query Parameter Error: 'filters' parameter is not valid JSON.")
        except ValidationError as e: # Pydantic validation errors
            raise HTTPException(status_code=400, detail=f"Query Parameter Error: 'filters' structure is invalid - {e}")

    try:
        # Get RDF graph from GraphDB in N-Triples format
        # Ensure db_host, db_user, db_password are not None before passing, checked by all() above.
        nt_data: str = get_data_from_graphdb(db_host, db_user, db_password, parsed_filters) # type: ignore

        if not nt_data.strip():
            return JSONResponse(content=[])

        tmpfile_path: Optional[str] = None # Initialize to None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", encoding="utf-8", suffix=".nt", delete=False
            ) as tmpfile:
                tmpfile.write(nt_data)
                tmpfile_path = tmpfile.name

            matcher: TermMatcher = TermMatcher.from_files([tmpfile_path])
        except Exception as e:
            # This covers errors in tempfile creation or TermMatcher.from_files
            # The detail string indicates the source of the error.
            raise HTTPException(status_code=500, detail=f"Fuzon Initialization Error: Failed to initialize Fuzon matcher - {e}")
        finally:
            if tmpfile_path and os.path.exists(tmpfile_path):
                 os.unlink(tmpfile_path)

        top_terms: List[Term] = matcher.top(request.search, 10)

        def clean_label(label: Any) -> str:
            """
            Cleans a label by extracting its string value.

            If the label is an rdflib.Literal or similar object with a '.value'
            attribute, that is returned. Otherwise, the label is converted to a
            string and stripped of surrounding quotes if present.

            Args:
                label: The label to clean (e.g., from a Fuzon Term object).
                       Can be a string or an object with a .value attribute.

            Returns:
                The cleaned string representation of the label.
            """
            if hasattr(label, 'value'):
                return str(label.value)
            else:
                return str(label).strip('"')

        results: List[Dict[str, str]] = [
            {"label": clean_label(term.label), "uri": str(term.uri)}
            for term in top_terms
        ]

        return JSONResponse(content=results)

    except HTTPException:
        # This will be caught by custom_http_exception_handler
        raise
    except RuntimeError as e: # Specific errors from get_data_from_graphdb
        # Detail provides specific information.
        raise HTTPException(status_code=500, detail=f"Data Fetching Error: {e}")
    except Exception as e:
        # This will be caught by generic_exception_handler, which will log it.
        # Re-raising it ensures it's caught by the generic handler if not an HTTPException.
        # Alternatively, to provide a more specific message through the HTTPException handler:
        logger.error(f"Unexpected error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search Processing Error: An unexpected issue occurred - {e}")
    # Redundant finally block for tmpfile_path removed as it's handled in the Fuzon initialization try/finally.
