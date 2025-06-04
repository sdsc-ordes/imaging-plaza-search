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
2. Build the microservice locally using `just image build`
3. Run the microservice using `just image run`
3. Navigate to http://localhost:7123/docs
4. Click on the /search endpoint
5. Click on "try it out" top right corner
6. Paste the below json in the request body.

```
{ "search": "deep", "filters": [ { "key": "programmingLanguage", "schema": "schema:programmingLanguage", "selected": ["Python"] }, { "key": "featureList", "schema": "schema:featureList", "selected": ["Object detection"] } ] }
```
5. Press "Execute" 
6. Observe the resulting response body containing the labels and URI's of softwares that match your search
