# imaging-plaza-search
A microservice for fetching relevant softwares to a certain search term + filters
input:
- env variables for defining graphDB endpoint.
- string search term
- string filter conditions

output:
A list of software URIs and their labels that match the search criteria.

## API Endpoint: `/v1/search`

The microservice provides a search functionality via a GET request to the `/v1/search` endpoint.

**Request Method:** `GET`

**Query Parameters:**

*   `search_term` (string, required): The term to search for (e.g., "microscopy", "segmentation").
*   `filters` (string, optional): A JSON-encoded string representing a list of filter objects. Each filter object helps narrow down the search based on specific criteria.

**`filters` JSON Structure:**

The `filters` parameter, if provided, must be a URL-encoded JSON string. The JSON structure should be a list of objects, where each object has the following keys:
*   `key` (string): The property or field to filter on (e.g., "programmingLanguage", "featureList").
*   `schema` (string): The schema or type associated with the key (e.g., "schema:programmingLanguage").
*   `selected` (list of strings): A list of values to match for the given key.

**Example `filters` JSON object (before URL encoding):**
```json
[
  {
    "key": "programmingLanguage",
    "schema": "schema:programmingLanguage",
    "selected": ["Python"]
  },
  {
    "key": "featureList",
    "schema": "schema:featureList",
    "selected": ["Object detection"]
  }
]
```

**Example Usage:**

1.  **Prerequisites:**
    *   Ensure you have your environment variables defined in a `.env` file at the root of the project (see `.env.example` if available). These variables typically define GraphDB connection details.
    *   Install dependencies: `pip install -r requirements.txt`

2.  **Run the microservice locally:**
    ```bash
    uvicorn imaging_plaza_search.main:app --reload --app-dir src
    ```

3.  **Accessing via FastAPI Docs (Recommended for trying it out):**
    *   Navigate to `http://127.0.0.1:8000/docs`.
    *   Find the `/v1/search` GET endpoint.
    *   Click "Try it out".
    *   Enter your desired `search_term`.
    *   For the `filters` parameter, you would paste the JSON string (like the example above). Remember that when using tools like `curl` or constructing URLs directly, this JSON string must be URL-encoded. The FastAPI docs UI will handle the encoding for you if you paste the plain JSON string into the field.
    *   Execute the request.

4.  **Example `curl` command:**

    To search for "deep" with the example filters shown above, the `filters` JSON string needs to be URL-encoded.

    JSON string:
    `[{"key":"programmingLanguage","schema":"schema:programmingLanguage","selected":["Python"]},{"key":"featureList","schema":"schema:featureList","selected":["Object detection"]}]`

    URL-encoded (you can use an online tool or a script to encode this):
    `%5B%7B%22key%22%3A%22programmingLanguage%22%2C%22schema%22%3A%22schema%3AprogrammingLanguage%22%2C%22selected%22%3A%5B%22Python%22%5D%7D%2C%7B%22key%22%3A%22featureList%22%2C%22schema%22%3A%22schema%3AfeatureList%22%2C%22selected%22%3A%5B%22Object%20detection%22%5D%7D%5D`

    Then the `curl` command would look like:
    ```bash
    curl -X GET "http://127.0.0.1:8000/v1/search?search_term=deep&filters=%5B%7B%22key%22%3A%22programmingLanguage%22%2C%22schema%22%3A%22schema%3AprogrammingLanguage%22%2C%22selected%22%3A%5B%22Python%22%5D%7D%2C%7B%22key%22%3A%22featureList%22%2C%22schema%22%3A%22schema%3AfeatureList%22%2C%22selected%22%3A%5B%22Object%20detection%22%5D%7D%5D"
    ```

**Output:**

The endpoint returns a JSON list of objects, where each object contains the `label` and `uri` of a software item matching the search criteria.

Example Output:
```json
[
  {
    "label": "Some Deep Learning Tool",
    "uri": "http://example.org/software/deep_tool_1"
  }
  // ... other results
]
```

## Running Tests

The project includes a test suite using `pytest`. To run the tests:

1.  Ensure you have installed all dependencies, including development dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    (Note: `pytest` and `pyfuzon` are included in `requirements.txt`.)

2.  Run the tests from the root directory of the project:
    ```bash
    PYTEST_RUNNING=1 python -m pytest src/imaging_plaza_search/test_main.py
    ```
    The `PYTEST_RUNNING=1` environment variable is currently needed due to compatibility issues with the `pyfuzon` library in Python 3.10, which is handled in the test setup.
