import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import json

# Attempt to import the app. Adjust the import path as necessary based on project structure.
# This assumes 'src' is in PYTHONPATH or tests are run in a way that src is discoverable.
from src.imaging_plaza_search.main import app

# If .env files are used for configuration, ensure they are loaded or mocked.
# For tests, it's often better to explicitly mock environment variables.

client = TestClient(app)

# Sample data for mocking
MOCK_NT_DATA = """
<http://example.com/tool/1> <http://example.org/fuzon#searchIndexPredicate> "Sample Tool One" .
<http://example.com/tool/1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://schema.org/SoftwareSourceCode> .
<http://example.com/tool/2> <http://example.org/fuzon#searchIndexPredicate> "Another Tool Two" .
<http://example.com/tool/2> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://schema.org/SoftwareSourceCode> .
"""

class MockFuzonTerm:
    def __init__(self, label, uri):
        self.label = label
        self.uri = uri

    def __str__(self): # For TermMatcher's internal use if it relies on stringification
        return f"Term(label={self.label}, uri={self.uri})"

MOCK_FUZON_RESULTS = [
    MockFuzonTerm("Sample Tool One", "http://example.com/tool/1"),
    MockFuzonTerm("Another Tool Two", "http://example.com/tool/2"),
]

# Helper for environment variable mocking
@pytest.fixture
def mock_db_env_vars():
    with patch.dict(os.environ, {
        "GRAPHDB_URL": "http://mock-graphdb:7200",
        "GRAPHDB_USER": "testuser",
        "GRAPHDB_PASSWORD": "testpassword"
    }):
        yield

@pytest.fixture
def mock_fuzon_matcher(mocker):
    mock_matcher_instance = MagicMock()
    mock_matcher_instance.top.return_value = MOCK_FUZON_RESULTS

    mock_term_matcher_from_files = mocker.patch(
        "src.imaging_plaza_search.main.TermMatcher.from_files",
        return_value=mock_matcher_instance
    )
    return mock_term_matcher_from_files, mock_matcher_instance

# Basic test to ensure the test setup is working
def test_read_main_app():
    response = client.get("/docs") # A common FastAPI endpoint to check if app is up
    assert response.status_code == 200

# --- Tests for /v1/search endpoint ---

@patch("src.imaging_plaza_search.main.get_data_from_graphdb", return_value=MOCK_NT_DATA)
def test_search_success_with_term_only(mock_get_data, mock_db_env_vars, mock_fuzon_matcher):
    """Test successful search with only a search term."""
    mock_fuzon_files, mock_fuzon_instance = mock_fuzon_matcher

    response = client.get("/v1/search?search=testquery")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(MOCK_FUZON_RESULTS)
    for item, mock_item in zip(data, MOCK_FUZON_RESULTS):
        assert item["label"] == mock_item.label
        assert item["uri"] == mock_item.uri

    mock_get_data.assert_called_once_with(
        "http://mock-graphdb:7200", "testuser", "testpassword", []
    )
    mock_fuzon_files.assert_called_once() # Check if TermMatcher.from_files was called
    mock_fuzon_instance.top.assert_called_once_with("testquery", 10)


@patch("src.imaging_plaza_search.main.get_data_from_graphdb", return_value=MOCK_NT_DATA)
def test_search_success_with_term_and_filters(mock_get_data, mock_db_env_vars, mock_fuzon_matcher):
    """Test successful search with a search term and valid filters."""
    mock_fuzon_files, mock_fuzon_instance = mock_fuzon_matcher

    filters_query_param = json.dumps([{"key": "modality", "schema": "s:modality", "selected": ["X-Ray"]}])
    response = client.get(f"/v1/search?search=testquery&filters={filters_query_param}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(MOCK_FUZON_RESULTS) # Assuming mock results for simplicity

    expected_parsed_filters = [{"key": "modality", "schema": "s:modality", "selected": ["X-Ray"]}]
    # The actual Filter objects are created inside the endpoint, so we check the raw list passed to get_data_from_graphdb
    # Pydantic models are compared by value, so this should work if Filter objects are passed.
    # However, get_data_from_graphdb receives List[Filter], not List[Dict].
    # For assertion, it's easier to check the arguments get_data_from_graphdb was called with.
    # We can check the properties of the Filter objects passed.

    args, _ = mock_get_data.call_args
    assert args[0] == "http://mock-graphdb:7200"
    assert args[1] == "testuser"
    assert args[2] == "testpassword"
    assert len(args[3]) == 1 # The list of filters
    passed_filter = args[3][0] # The first Filter object
    assert passed_filter.key == "modality"
    assert passed_filter.schema == "s:modality"
    assert passed_filter.selected == ["X-Ray"]

    mock_fuzon_files.assert_called_once()
    mock_fuzon_instance.top.assert_called_once_with("testquery", 10)

@patch("src.imaging_plaza_search.main.get_data_from_graphdb", return_value="") # Empty NT data
def test_search_success_empty_nt_data(mock_get_data, mock_db_env_vars, mock_fuzon_matcher):
    """Test search when get_data_from_graphdb returns empty N-Triples data."""
    mock_fuzon_files, _ = mock_fuzon_matcher # We don't expect .top to be called if nt_data is empty

    response = client.get("/v1/search?search=testquery")

    assert response.status_code == 200
    assert response.json() == []
    mock_get_data.assert_called_once()
    mock_fuzon_files.assert_not_called() # Fuzon matcher shouldn't be initialized if no data


# --- Tests for error handling and specific status codes ---

def test_search_missing_search_term(mock_db_env_vars):
    """Test request with missing 'search' term (should be 422)."""
    # No query parameters, 'search' is required by SearchRequest model
    response = client.get("/v1/search")
    assert response.status_code == 422 # FastAPI validation error for missing required field
    content = response.json()
    assert content["detail"][0]["type"] == "missing"
    assert content["detail"][0]["loc"] == ["query", "search"]


def test_search_invalid_filter_json(mock_db_env_vars):
    """Test search with malformed JSON in 'filters' parameter (should be 400)."""
    response = client.get("/v1/search?search=test&filters=not_valid_json{")
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Query Parameter Error: 'filters' parameter is not valid JSON."
    assert content["source"] == "api_handled_error"


def test_search_invalid_filter_structure(mock_db_env_vars):
    """Test search with valid JSON but incorrect structure for 'filters' (should be 400)."""
    filters_query_param = json.dumps([{"wrong_key": "modality"}]) # Incorrect structure
    response = client.get(f"/v1/search?search=test&filters={filters_query_param}")
    assert response.status_code == 400
    content = response.json()
    assert "Query Parameter Error: 'filters' structure is invalid" in content["detail"]
    assert content["source"] == "api_handled_error"


def test_search_db_config_missing():
    """Test search when DB environment variables are missing (should be 503)."""
    # No mock_db_env_vars fixture here, os.environ will be accessed directly
    # Ensure relevant env vars are unset if they exist from a previous test or environment
    with patch.dict(os.environ, {}, clear=True): # Clear all env vars for this test
        response = client.get("/v1/search?search=test")
    assert response.status_code == 503
    content = response.json()
    assert content["detail"] == "Configuration Error: GraphDB connection details (URL, user, or password) are missing."
    assert content["source"] == "api_handled_error"


@patch("src.imaging_plaza_search.main.get_data_from_graphdb", side_effect=RuntimeError("GraphDB unavailable"))
def test_search_graphdb_error(mock_get_data, mock_db_env_vars):
    """Test search when get_data_from_graphdb raises a RuntimeError (should be 500)."""
    response = client.get("/v1/search?search=test")
    assert response.status_code == 500
    content = response.json()
    assert content["detail"] == "Data Fetching Error: GraphDB unavailable"
    assert content["source"] == "api_handled_error"
    mock_get_data.assert_called_once()


@patch("src.imaging_plaza_search.main.get_data_from_graphdb", return_value=MOCK_NT_DATA)
@patch("src.imaging_plaza_search.main.TermMatcher.from_files", side_effect=Exception("Fuzon init failed"))
def test_search_fuzon_init_error(mock_fuzon_from_files, mock_get_data, mock_db_env_vars):
    """Test search when TermMatcher.from_files raises an Exception (should be 500)."""
    response = client.get("/v1/search?search=test")
    assert response.status_code == 500
    content = response.json()
    assert content["detail"] == "Fuzon Initialization Error: Failed to initialize Fuzon matcher - Fuzon init failed"
    assert content["source"] == "api_handled_error"
    mock_get_data.assert_called_once()
    mock_fuzon_from_files.assert_called_once()


# --- Test for Generic Exception Handler ---
# To test the generic exception handler, we need an endpoint or a situation
# where a non-HTTPException is raised and not caught by other specific handlers.

# We can create a temporary test endpoint for this or try to make an existing part raise a generic Exception.
# For simplicity in this context, we'll assume a part of the search logic (not already raising HTTPException) fails.
# Let's mock the 'clean_label' utility function inside 'search' to cause an unexpected error.

@patch("src.imaging_plaza_search.main.get_data_from_graphdb", return_value=MOCK_NT_DATA)
@patch("src.imaging_plaza_search.main.TermMatcher.from_files") # Standard mock for TermMatcher
@patch("src.imaging_plaza_search.main.search.<locals>.clean_label", side_effect=Exception("Unexpected clean_label error"))
def test_search_unexpected_error_in_processing(
    mock_clean_label, mock_fuzon_from_files, mock_get_data, mock_db_env_vars, mock_fuzon_matcher # mock_fuzon_matcher provides mock_fuzon_instance
):
    """Test search when an unexpected non-HTTP error occurs during result processing."""
    # Configure the mock_fuzon_matcher's instance part (mock_fuzon_instance.top)
    _, mock_fuzon_instance = mock_fuzon_matcher
    mock_fuzon_from_files.return_value = mock_fuzon_instance # Ensure TermMatcher.from_files returns the instance configured by mock_fuzon_matcher

    response = client.get("/v1/search?search=test")

    # This error is now caught by the final `except Exception as e:` in `search`
    # which logs it and then raises an HTTPException. So, it will be handled by `custom_http_exception_handler`.
    assert response.status_code == 500
    content = response.json()
    assert "Search Processing Error: An unexpected issue occurred - Unexpected clean_label error" in content["detail"]
    assert content["source"] == "api_handled_error"

    # To truly test the generic_exception_handler, the error must escape all try-except blocks in `search`
    # or occur outside of the `search` endpoint's main try-block but within FastAPI's processing.
    # This test as written now tests the last `except Exception` block in `search` endpoint.

# To properly test generic_exception_handler, we'd need to patch something at a higher level or make a route that directly fails.
# For example, if a dependency used by FastAPI itself failed in a way not converted to HTTPException.

# Let's simulate an error in a dependency that is not an HTTPException
# This requires a bit more specific mocking.
# If `json.loads` in the `custom_http_exception_handler` itself failed, for instance (highly unlikely).
# Or if `logger.error` in `generic_exception_handler` failed.

# A more direct way to test the generic handler:
@pytest.fixture
def temporary_broken_route_app():
    from fastapi import FastAPI, Request
    temp_app = FastAPI()

    @temp_app.get("/broken")
    async def broken_route(request: Request):
        raise ValueError("This is a deliberate non-HTTP unhandled error.")

    # Add the generic exception handler to this temporary app
    from src.imaging_plaza_search.main import generic_exception_handler as main_generic_handler
    temp_app.add_exception_handler(Exception, main_generic_handler)

    return temp_app

def test_generic_exception_handler_direct(temporary_broken_route_app):
    """Test the generic exception handler directly with a route that raises a standard Exception."""
    broken_client = TestClient(temporary_broken_route_app)
    response = broken_client.get("/broken")
    assert response.status_code == 500
    content = response.json()
    assert content["detail"] == "An internal server error occurred."
    assert content["source"] == "unhandled_system_error"

# More tests will be added below
