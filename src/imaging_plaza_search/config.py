from rdflib import URIRef

LABEL_PREDICATES_WEIGHTED = [
    (URIRef("http://schema.org/name"), 1.0),
    # (URIRef("http://www.w3.org/2000/01/rdf-schema#label"), 0.9),
    (URIRef("http://schema.org/description"), 0.5),
    (URIRef("http://schema.org/featureList"), 0.6),
    (URIRef("http://schema.org/programmingLanguage"), 0.5),
    (URIRef("http://schema.org/keywords"), 0.5),
    (URIRef("https://imaging-plaza.epfl.ch/ontology#relatedToOrganization"), 0.5),
]
