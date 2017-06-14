import rdflib.plugin as plugin

from rdflib import Graph, Literal, URIRef, ConjunctiveGraph, Dataset
from rdflib.graph import Node, ReadOnlyGraphAggregate, ModificationException, UnSupportedAggregateOperation, Path
from rdflib.store import Store
from rdflib.plugins.memory import IOMemory

class ReadOnlyRewriteGraph(Graph):
    def __init__(self, store='default', identifier = None, rewritten_identifier = None, namespace_manager = None):
        super().__init__(store=store, identifier=rewritten_identifier, namespace_manager=namespace_manager)
        self.__graph = Graph(store=store, identifier=identifier, namespace_manager=namespace_manager)

    def triples(self, triple):
        return self.__graph.triples(triple)
   
    def __cmp__(self, other):
        if other is None:
            return -1
        elif isinstance(other, Graph):
            return -1
        elif isinstance(other, ReadOnlyRewriteGraph):
            return cmp(self.__graph, other.__graph)
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

    def __len__(self):
        return len(self.__graph)


class InMemoryGraphAggregate(ConjunctiveGraph):
    def __init__(self, graphs=list(), identifier=None):                
        self.__memory_store = IOMemory()        
        super().__init__(self.__memory_store, identifier)
        
        assert isinstance(graphs, list), "graphs argument must be a list of Graphs!!"
        self.__graphs = graphs

    class InMemoryGraph(Graph):
        def __init__(self, store = 'default', identifier = None, namespace_manager = None, external = None):            
            super().__init__(store, identifier, namespace_manager)
            self.__external = external

        def force(self):
            if self.__external is not None and self not in self.store.contexts():
                self.store.addN((s, p, o, self) for s, p, o in self.__external.triples((None, None, None)))
        
        def add(self, triple_or_quad):
            self.force()
            super().add(triple_or_quad)

        def addN(self, triple_or_quad):
            self.force()
            super().addN(triple_or_quad)

        def remove(self, triple_or_quad):
            self.force()
            super().remove(triple_or_quad)

    def __repr__(self):
        return "<InMemoryGraphAggregate: %s graphs>" % len(self.graphs)

    @property
    def is_dirty(self):
        return len(list(self.store.contexts())) > 0

    def _spoc(self, triple_or_quad, default=False):
        """
        helper method for having methods that support
        either triples or quads
        """
        if triple_or_quad is None:
            return (None, None, None, self.default_context if default else None)
        if len(triple_or_quad) == 3:
            c = self.default_context if default else None
            (s, p, o) = triple_or_quad
        elif len(triple_or_quad) == 4:
            (s, p, o, c) = triple_or_quad
            c = self._graph(c)
        return s,p,o,c

    def _graph(self, c):
        if c is None: return None
        if not isinstance(c, Graph):
            return self.get_context(c)
        else:
            return c

    def add(self, triple_or_quad):
        s,p,o,c = self._spoc(triple_or_quad, default=True)
        if isinstance(c, InMemoryGraphAggregate.InMemoryGraph):
            c.force()
        self.store.add((s, p, o), context=c, quoted=False)

    def addN(self, quads):
        def do(g):
            g = self._graph(g)
            if isinstance(g, InMemoryGraphAggregate.InMemoryGraph):
                g.force()
            return g

        self.store.addN((s, p, o, do(c)) for s, p, o, c in quads)

    def remove(self, triple_or_quad):
        s,p,o,c = self._spoc(triple_or_quad)
        if isinstance(c, InMemoryGraphAggregate.InMemoryGraph):
            c.force()
        self.store.remove((s, p, o), context=c)

    def contexts(self, triple=None):
        for graph in self.__graphs:
            if graph.identifier not in (c.identifier for c in self.store.contexts()):
                yield graph
        for graph in self.store.contexts():
            yield graph

    graphs = contexts

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

    def graph(self, identifier=None):
        for graph in self.graphs():
           if str(graph.identifier) == str(identifier):
               return graph
        
        return self.get_context(identifier)

    def __contains__(self, triple_or_quad):
        (_,_,_,context) = self._spoc(triple_or_quad)
        for graph in self.graphs():
            if context is None or graph.identifier == context.identifier:
                if triple_or_quad[:3] in graph:
                    return True
        return False

    

    def _default(self, identifier):
        return next( (x for x in self.__graphs if x.identifier == identifier), None)

    def get_context(self, identifier, quoted=False):   
        if not isinstance(identifier, Node):
            identifier = URIRef(identifier)     
        return InMemoryGraphAggregate.InMemoryGraph(store=self.__memory_store, identifier=identifier, namespace_manager=self, external=self._default(identifier))