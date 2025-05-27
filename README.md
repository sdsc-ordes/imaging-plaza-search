# imaging-plaza-search
A microservice for fetching relevant softwares to a certain search term + filters
input:
- env variables for defining graphDB endpoint.
- string search term
- string filter conditions

output:
A list of software URI's to be used to filter the full json-ld on the front-end.

Plan:
- [ ] Fetch the code from IP fair level calc for doing SPARQL queries on GraphDB endpoint
- [ ] Make the SPARQL query that filters down the finalGraph
- [ ] Run that query on the finalGraph, and construct a new nt file
- [ ] Pipe that file into fuzon together with the initial search term and return a list of IRI's 
