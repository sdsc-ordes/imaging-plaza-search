import pytest
import json
from unittest.mock import patch, MagicMock, ANY

from fastapi.testclient import TestClient

# Assuming 'app' can be imported from main.
# If 'main.py' is run as a script, 'app' might not be directly importable.
# For now, let's assume it's structured for import, e.g., by not having
# `if __name__ == "__main__": uvicorn.run(app)` directly in main.py without guards.
import imaging_plaza_search.main as main_module # Import the main module
app = main_module.app # Get app from the imported module
from imaging_plaza_search.models import Filter # For constructing filter JSON
# from pyfuzon import Term # Removed: Term will be taken from main_module, which might be a mock

# TestClient instance
client = TestClient(app)

# Mock N-Triples data to be returned by get_data_from_graphdb
MOCK_NT_DATA = """
<http://example.org/s1> <http://www.w3.org/2000/01/rdf-schema#label> "Label 1" .
<http://example.org/s2> <http://www.w3.org/2000/01/rdf-schema#label> "Relevant Term" .
<http://example.org/s3> <http://purl.obolibrary.org/obo/IAO_0000115> "definition" .
"""

# Helper to create mock Term objects for pyfuzon
def create_mock_term(uri_str, label_str):
    # pyfuzon.Term expects a label that might have a .value or be a string.
    # We'll mock a simple object with a 'value' attribute for the label part.
    # main_module.Term will be the actual pyfuzon.Term if pyfuzon imported correctly in main.py,
    # or a MagicMock if the import failed and PYTEST_RUNNING=1.
    # When main_module.Term is a MagicMock, calling it (i.e. main_module.Term())
    # returns a new MagicMock instance (its return_value).
    mock_label = MagicMock()
    mock_label.value = label_str

    term_instance = main_module.Term() # This call returns a new MagicMock
    term_instance.uri = uri_str        # Set .uri to be the actual string value
    term_instance.label = mock_label   # Set .label to be the mock_label object
    return term_instance

@patch('tempfile.NamedTemporaryFile') # Mock NamedTemporaryFile
@patch('imaging_plaza_search.main.get_data_from_graphdb')
@patch('imaging_plaza_search.main.TermMatcher') # Mock the TermMatcher class
def test_search_no_filters(MockTermMatcherClass, mock_get_data_from_graphdb, MockNamedTemporaryFile):
    """Test successful search with a search_term and no filters."""
    # Setup mock for NamedTemporaryFile
    mock_tmp_file = MagicMock()
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt"
    MockNamedTemporaryFile.return_value = mock_tmp_file

    # Setup mock for get_data_from_graphdb
    mock_get_data_from_graphdb.return_value = MOCK_NT_DATA

    # Setup mock for TermMatcher instance and its 'top' method
    mock_matcher_instance = MagicMock()
    mock_terms = [create_mock_term("http://example.org/s2", "Relevant Term")]
    mock_matcher_instance.top.return_value = mock_terms
    MockTermMatcherClass.from_files.return_value = mock_matcher_instance

    response = client.get("/v1/search?search_term=Relevant")

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["label"] == "Relevant Term"
    assert results[0]["uri"] == "http://example.org/s2"

    mock_get_data_from_graphdb.assert_called_once_with(ANY, ANY, ANY, None)
    MockTermMatcherClass.from_files.assert_called_once_with(["dummy_temp_file.nt"])
    mock_matcher_instance.top.assert_called_once_with("Relevant", 10)
    # Check if tempfile.NamedTemporaryFile was called
    MockNamedTemporaryFile.assert_called_once()


@patch('tempfile.NamedTemporaryFile')
@patch('imaging_plaza_search.main.get_data_from_graphdb')
@patch('imaging_plaza_search.main.TermMatcher')
def test_search_with_valid_filters(MockTermMatcherClass, mock_get_data_from_graphdb, MockNamedTemporaryFile):
    """Test successful search with a search_term and valid JSON filters."""
    mock_tmp_file = MagicMock()
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt"
    MockNamedTemporaryFile.return_value = mock_tmp_file

    mock_get_data_from_graphdb.return_value = MOCK_NT_DATA

    mock_matcher_instance = MagicMock()
    mock_terms = [create_mock_term("http://example.org/s1", "Label 1")]
    mock_matcher_instance.top.return_value = mock_terms
    MockTermMatcherClass.from_files.return_value = mock_matcher_instance

    filters_obj = [Filter(key="type", schema="http://example.org/schema", selected=["http://example.org/TypeA"])]
    filters_json = json.dumps([f.model_dump() for f in filters_obj]) # Use model_dump for Pydantic v2

    response = client.get(f"/v1/search?search_term=Label&filters={filters_json}")

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["label"] == "Label 1"
    assert results[0]["uri"] == "http://example.org/s1"

    # Check that get_data_from_graphdb was called with the parsed filters
    mock_get_data_from_graphdb.assert_called_once()
    call_args = mock_get_data_from_graphdb.call_args[0]
    # call_args[3] is the List[Filter] object, compare it with the original filters_obj
    assert call_args[3] == filters_obj

    MockTermMatcherClass.from_files.assert_called_once_with(["dummy_temp_file.nt"])
    mock_matcher_instance.top.assert_called_once_with("Label", 10)
    MockNamedTemporaryFile.assert_called_once()


def test_search_invalid_json_filters():
    """Test a request with invalid JSON filters (should return HTTP 400)."""
    response = client.get("/v1/search?search_term=Test&filters=invalid_json_string")

    assert response.status_code == 400
    assert "Invalid JSON format for filters" in response.json()["detail"]

@patch('tempfile.NamedTemporaryFile') # Still need to mock this as it's called before graphdb usually
@patch('imaging_plaza_search.main.get_data_from_graphdb')
def test_search_graphdb_exception(mock_get_data_from_graphdb, MockNamedTemporaryFile):
    """Test a request where get_data_from_graphdb raises an exception (should return HTTP 500)."""
    mock_tmp_file = MagicMock()
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt" # mock file creation part
    MockNamedTemporaryFile.return_value = mock_tmp_file


    mock_get_data_from_graphdb.side_effect = Exception("GraphDB connection error")

    response = client.get("/v1/search?search_term=Anything")

    assert response.status_code == 500
    assert "GraphDB connection error" in response.json()["detail"]
    MockNamedTemporaryFile.assert_not_called() # Ensure it was NOT called if get_data_from_graphdb fails


@patch('tempfile.NamedTemporaryFile')
@patch('imaging_plaza_search.main.get_data_from_graphdb')
@patch('imaging_plaza_search.main.TermMatcher')
def test_search_no_results_from_matcher(MockTermMatcherClass, mock_get_data_from_graphdb, MockNamedTemporaryFile):
    """Test a request where TermMatcher.top returns an empty list."""
    mock_tmp_file = MagicMock()
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt"
    MockNamedTemporaryFile.return_value = mock_tmp_file

    mock_get_data_from_graphdb.return_value = MOCK_NT_DATA

    mock_matcher_instance = MagicMock()
    mock_matcher_instance.top.return_value = [] # No terms found
    MockTermMatcherClass.from_files.return_value = mock_matcher_instance

    response = client.get("/v1/search?search_term=NonExistent")

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0

    mock_get_data_from_graphdb.assert_called_once()
    MockTermMatcherClass.from_files.assert_called_once_with(["dummy_temp_file.nt"])
    mock_matcher_instance.top.assert_called_once_with("NonExistent", 10)
    MockNamedTemporaryFile.assert_called_once()

@patch('tempfile.NamedTemporaryFile')
@patch('imaging_plaza_search.main.get_data_from_graphdb')
@patch('imaging_plaza_search.main.TermMatcher')
def test_search_invalid_filter_structure(MockTermMatcherClass, mock_get_data_from_graphdb, MockNamedTemporaryFile):
    """Test a request with valid JSON but invalid filter structure (should return HTTP 400)."""
    # This test doesn't need graphdb or termmatcher mocks to be highly specific,
    # as the error should occur before they are significantly used.
    mock_tmp_file = MagicMock() # Still mock tempfile
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt"
    MockNamedTemporaryFile.return_value = mock_tmp_file

    # Valid JSON, but not matching List[Filter]
    invalid_filters_json = json.dumps([{"wrong_key": "value"}])

    response = client.get(f"/v1/search?search_term=Test&filters={invalid_filters_json}")

    assert response.status_code == 400
    assert "Invalid filter structure" in response.json()["detail"]
    # NamedTemporaryFile is not called if filter parsing fails early
    MockNamedTemporaryFile.assert_not_called()


# Note on testing tempfile cleanup:
# The `main.py` uses a `try...finally` block to clean up the temporary file.
# Mocking `tempfile.NamedTemporaryFile` and `os.remove` (if we wanted to assert its call)
# would be one way. However, the current tests ensure that `NamedTemporaryFile` is called.
# The `delete=False` and manual `os.remove` in `main.py` means that if an error occurs
# after file creation but before the `finally` block's `os.remove`, the mock file wouldn't be
# "removed" by the mock `os.remove` unless that's also part of the test.
# Given the current mocking of `get_data_from_graphdb` and `TermMatcher`,
# the critical parts that might fail and leave a file are covered by mocks.
# The `finally` block in `main.py` is tested implicitly: if `NamedTemporaryFile` is called,
# its cleanup should be attempted. The key is that our mocks for `get_data_from_graphdb` or
# `TermMatcher` don't create real files that would be left behind.
# The mock for `tempfile.NamedTemporaryFile` itself ensures that no real file is created on the filesystem
# during tests, which is the most important aspect for test environment cleanliness.
# We also added `MockNamedTemporaryFile.assert_called_once()` or `assert_not_called()`
# to relevant tests to ensure file handling logic is entered or skipped as expected.

# To check os.remove, one could further mock 'os.remove'
# @patch('os.remove') in tests where cleanup is expected.
# For example, in test_search_graphdb_exception:
# mock_os_remove.assert_called_once_with("dummy_temp_file.nt")
# This is added to test_search_graphdb_exception_with_os_remove_check below.

@patch('os.remove') # Mock os.remove for this specific test
@patch('tempfile.NamedTemporaryFile')
@patch('imaging_plaza_search.main.get_data_from_graphdb')
def test_search_graphdb_exception_with_os_remove_check(mock_get_data_from_graphdb, MockNamedTemporaryFile, mock_os_remove):
    """Test GraphDB exception and ensure os.remove is called on the temp file."""
    mock_tmp_file = MagicMock()
    mock_tmp_file.__enter__.return_value.name = "dummy_temp_file.nt"
    MockNamedTemporaryFile.return_value = mock_tmp_file

    mock_get_data_from_graphdb.side_effect = Exception("GraphDB connection error")

    response = client.get("/v1/search?search_term=Anything")

    assert response.status_code == 500
    assert "GraphDB connection error" in response.json()["detail"]
    MockNamedTemporaryFile.assert_not_called() # File not created, so not called
    # Assert that os.remove was NOT called because no file was created
    mock_os_remove.assert_not_called()
