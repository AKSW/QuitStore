import functools
from itertools import chain
from rdflib import Graph, ConjunctiveGraph
from rdflib.graph import ModificationException
from rdflib.graph import Path


class RewriteGraph(Graph):
    def __init__(
        self, store='default', identifier=None, rewritten_identifier=None, namespace_manager=None
    ):
        super().__init__(
            store=store, identifier=rewritten_identifier, namespace_manager=namespace_manager
        )
        self.__graph = Graph(
            store=store, identifier=identifier, namespace_manager=namespace_manager
        )

    def triples(self, triple):
        return self.__graph.triples(triple)

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


def _copyIfNotExists(store, self, other):
    if other and self not in store.contexts(None):
        store.addN((s, p, o, self) for s, p, o in other.triples((None, None, None)))


class CopyOnEditGraph(Graph):
    def __init__(self, template, store='default', identifier=None, namespace_manager=None):
        super().__init__(store, identifier, namespace_manager)

        assert not template or isinstance(
            template, Graph), "template must be graph"
        assert not template or template.identifier == identifier, "identifier must match"

        self._template = template
        self._store = store

    def add(self, triple_or_quad):
        _copyIfNotExists(self._store, self, self._template)
        super().add(triple_or_quad)

    def addN(self, triple_or_quad):
        _copyIfNotExists(self._store, self, self._template)
        super().addN(triple_or_quad)

    def remove(self, triple_or_quad):
        _copyIfNotExists(self._store, self, self._template)
        super().remove(triple_or_quad)

    def triples(self, triple):
        if self not in self._store.contexts(None):
            return self._template.triples(triple) if self._template else (_ for _ in ())
        else:
            return super().triples(triple)

    @property
    def store(self):
        if self not in self._store.contexts(None):
            return self._template.store
        else:
            return super().store

    def unwrap(self):
        return Graph(store=self.store, identifier=self.identifier)

    def __isub__(self, other):
        """Subtract all triples in Graph other from Graph.

        BNode IDs are not changed.
        """
        for triple in other:
            self.remove(triple)
        return self

    def __len__(self):
        if self not in self._store.contexts(None):
            return self._template.__len__()
        else:
            return super().__len__()


class InMemoryAggregatedGraph(ConjunctiveGraph):
    def __init__(self, store='default', identifier=None, graphs=list()):
        super().__init__(store=store, identifier=None)

        assert (
            isinstance(graphs, list)
        ) and (
            all(isinstance(g, Graph) for g in graphs)
        ), "graphs argument must be a list of Graphs!!"
        self._contexts = graphs

    def __repr__(self):
        return "<{}: {}|{} graphs>".format(
            type(self).__name__,
            len(self.store.contexts()),
            len((c for c in self.graphs() if c not in self.store.contexts()))
        )

    def _graph(self, c):
        if c is None:
            return None
        if not isinstance(c, Graph):
            return self.get_context(c)
        else:
            return self.get_context(c.identifier)

    def contexts(self, triple=None):
        def collect():
            if triple is None or triple is (None, None, None):
                contexts = (context for context in self._contexts)
            else:
                contexts = (context for context in self._contexts
                            if triple in context)

            seen = set()
            for element in chain(self.store.contexts(triple), contexts):
                k = element.identifier
                if k not in seen:
                    seen.add(k)
                    yield element

        return list(collect())

    graphs = contexts

    def triples(self, triple_or_quad, context=None):
        s, p, o, c = self._spoc(triple_or_quad)
        context = self._graph(context or c)

        if isinstance(p, Path):
            for s, o in p.eval(self, s, o):
                yield s, p, o
        else:
            for graph in self.contexts():
                if context is None or graph.identifier == context.identifier:
                    for s, p, o in graph.triples((s, p, o)):
                        yield s, p, o

    def quads(self, triple_or_quad=None):
        s, p, o, c = self._spoc(triple_or_quad)
        context = self._graph(c)

        for graph in self.graphs():
            if context is None or graph.identifier == context.identifier:
                for s1, p1, o1 in graph.triples((s, p, o)):
                    yield (s1, p1, o1, graph)

    def __contains__(self, triple_or_quad):
        (_, _, _, context) = self._spoc(triple_or_quad)
        context = self._graph(context)

        for graph in self.graphs():
            if context is None or graph.identifier == context.identifier:
                if triple_or_quad[:3] in graph:
                    return True
        return False

    def __len__(self):
        return functools.reduce(lambda a, b: a + len(b), self.contexts(None), 0)

    def _lookup(self, identifier):
        return next((x for x in self._contexts if x.identifier == identifier), None)

    def get_context(self, identifier, quoted=False):
        if isinstance(identifier, Graph):
            identifier = identifier.identifier
        return self._lookup(identifier) or Graph(
            store=self.store, identifier=identifier, namespace_manager=self
        )


class InMemoryCopyOnEditAggregatedGraph(InMemoryAggregatedGraph):

    def add(self, triple_or_quad):
        s, p, o, c = self._spoc(triple_or_quad, default=True)

        _copyIfNotExists(self.store, c, self._lookup(self.identifier))

        self.store.add((s, p, o), context=c, quoted=False)

    def addN(self, quads):
        def do(g):
            c = self._graph(g)

            _copyIfNotExists(self.store, c, self._lookup(self.identifier))

            return g

        self.store.addN((s, p, o, do(c)) for s, p, o, c in quads)

    def remove(self, triple_or_quad):
        s, p, o, c = self._spoc(triple_or_quad)

        _copyIfNotExists(self.store, c, self._lookup(self.identifier))

        self.store.remove((s, p, o), context=c)

    def get_context(self, identifier, quoted=False):
        if isinstance(identifier, Graph):
            identifier = identifier.identifier
        return CopyOnEditGraph(
            store=self.store, identifier=identifier, namespace_manager=self,
            template=self._lookup(identifier)
        )
