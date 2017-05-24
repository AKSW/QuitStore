from rdflib.namespace import Namespace, RDF, RDFS, FOAF, DC, VOID, XSD

__all__ = ['RDF', 'RDFS', 'FOAF', 'DC', 'VOID', 'XSD', 'PROV', 'QUIT', 'is_a']

# missing namespaces
PROV = Namespace('http://www.w3.org/ns/prov#')
QUIT = Namespace('http://quit.aksw.org/')

# simplified properties
is_a = RDF.type
