import rdflib.plugin as plugin

from rdflib import Graph, Literal, URIRef, ConjunctiveGraph, Dataset
from rdflib.graph import ReadOnlyGraphAggregate, ModificationException, UnSupportedAggregateOperation, Path
from rdflib.store import Store
from rdflib.plugins.memory import IOMemory

class ReadOnlyRewriteGraph(Graph):
    def __init__(self, store='default', identifier = None, rewritten_identifier = None, namespace_manager = None):
        self.g = Graph(store=store, identifier=identifier, namespace_manager=namespace_manager)

        super().__init__(store=store, identifier=rewritten_identifier, namespace_manager=namespace_manager)

    def triples(self, triple):
        return self.g.triples(triple)
   
    def __cmp__(self, other):
        if other is None:
            return -1
        elif isinstance(other, Graph):
            return -1
        elif isinstance(other, ReadOnlyRewriteGraph):
            return cmp(self.g, other.g)
        else:
            return -1
    
    def add(self, triple_or_quad):
        raise ModificationException()

    def addN(self, triple_or_quad):
        raise ModificationException()

    def remove(self, triple_or_quad):
        raise ModificationException()

    def __iadd__(self, other):
        raise ModificationException()

    def __isub__(self, other):
        raise ModificationException()

    def parse(self, source, publicID=None, format="xml", **args):
        raise ModificationException()

class InMemoryGraphAggregate(ConjunctiveGraph):
    def __init__(self, default_graphs, identifier=None):                
        self.default_graphs = default_graphs
        self.memory_store = IOMemory()
        super().__init__(self.memory_store, identifier)

    def __repr__(self):
        return "<InMemoryGraphAggregate: %s graphs>" % len(self.graphs)

    @property
    def is_dirty(self):
        return len(self.store) > 0

    def _rewrite(self, graph):
        if isinstance(graph, ReadOnlyRewriteGraph):
            return graph.rewritten_identifier
        else: 
            return graph.identifier

    def _copy(self, graph):
        if not isinstance(graph, InMempryGraph):
            new_graph = Graph(store=self.store, identifier=graph.identifier)
            new_graph += graph.triples((None, None, None))
            return new_graph
        else:
            return graph

    def add(self, triple_or_quad):
        s,p,o,c = self._spoc(triple_or_quad, default=True)
        self.store.add((s, p, o), context=_copy(c), quoted=False)

    def addN(self, quads):
        self.store.addN((s, p, o, self._copy(self._graph(c))) for s, p, o, c in quads)

    def remove(self, triple_or_quad):
        s,p,o,c = self._spoc(triple_or_quad)
        self.store.remove((s, p, o), context=c_copy(c))

    def triples(self, triple_or_quad, context=None):
        s,p,o,c = self._spoc(triple_or_quad)
        context = self._graph(context or c)

        if isinstance(p, Path):
            for s, o in p.eval(self, s, o):
                yield s, p, o
        else:
            for graph in self.graphs():
                if context is None or graph.identifier == context.identifier:
                    for s, p, o in graph.triples((s, p, o)):
                        yield s, p, o

    def quads(self, triple_or_quad=None):
        s,p,o,c = self._spoc(triple_or_quad)
        context = self._graph(c)

        for graph in self.graphs():
           if context is None or graph.identifier == context.identifier:
                for s1, p1, o1 in graph.triples((s, p, o)):
                    yield (s1, p1, o1, graph)

    def contexts(self, triple=None):
        default = False
        for graph in self.default_graphs:
            if graph.identifier not in self.store.contexts():
                yield graph
        for graph in self.store.contexts():
            yield graph

    graphs = contexts

    def graph(self, identifier=None):
        if identifier is None:
            identifier = self.default_context.identifier

        for graph in self.graphs():
           if graph.identifier == identifier:
               return graph
        
        return self.get_context(identifier)

    def __contains__(self, triple_or_quad):
        (_,_,_,context) = self._spoc(triple_or_quad)
        for graph in self.graphs:
            if context is None or graph.identifier == context.identifier:
                if triple_or_quad[:3] in graph:
                    return True
        return False