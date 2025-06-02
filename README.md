# imaging-plaza-search
A microservice for fetching relevant softwares to a certain search term + filters
input:
- env variables for defining graphDB endpoint.
- string search term
- string filter conditions

output:
A list of software URI's to be used to filter the full json-ld on the front-end.

## Example search using API
1. Make sure you have your env variables defined in .env
2. Run the microservice locally using `uvicorn imaging_plaza_search.main:app --reload --app-dir src`
3. Navigate to http://127.0.0.1:8000/docs
4. Click on the /search endpoint
5. Click on "try it out" top right corner
6. Paste the below json in the request body.

```
{ "search": "deep", "filters": [ { "key": "programmingLanguage", "schema": "schema:programmingLanguage", "selected": ["Python"] }, { "key": "featureList", "schema": "schema:featureList", "selected": ["Object detection"] } ] }
```
5. Press "Execute" 
6. Observe the resulting response body containing the labels and URI's of softwares that match your search
