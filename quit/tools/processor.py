from rdflib.query import Processor, Result, UpdateProcessor
from rdflib.plugins.sparql.sparql import Query
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

from quit.tools.algebra import translateQuery, translateUpdate
from quit.tools.evaluate import evalQuery
from quit.tools.update import evalUpdate

class SPARQLUpdateProcessor(UpdateProcessor):
    def __init__(self, graph):
        self.graph = graph

    def update(self, strOrQuery, initBindings={}, initNs={}):
        if isinstance(strOrQuery, str):
            strOrQuery=translateUpdate(parseUpdate(strOrQuery), initNs=initNs)

        return evalUpdate(self.graph, strOrQuery, initBindings)


class SPARQLProcessor(Processor):

    def __init__(self, graph):
        self.graph = graph

    def query(
            self, strOrQuery, initBindings={},
            initNs={}, base=None, DEBUG=False):
        """
        Evaluate a query with the given initial bindings, and initial
        namespaces. The given base is used to resolve relative URIs in
        the query and will be overridden by any BASE given in the query.
        """

        if not isinstance(strOrQuery, Query):
            parsetree = parseQuery(strOrQuery)
            query = translateQuery(parsetree, base, initNs)
        else:
            query = strOrQuery

        return evalQuery(self.graph, query, initBindings, base)