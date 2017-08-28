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


class CopyOnEditGraph(Graph):
    def __init__(self, template, store='default', identifier=None, namespace_manager=None):
        super().__init__(store, identifier, namespace_manager)

        assert not template or isinstance(
            template, Graph), "template must be graph"
        assert not template or template.identifier == identifier, "identifier must match"

        self._template = template
        self._store = super().store

    def _copyIfNotExists(self):
        if self not in self._store.contexts(None):
            self._store.addN(
                (s, p, o, self) for s, p, o in self._template.triples((None, None, None)))

    def add(self, triple_or_quad):
        if self._template:
            _copyIfNotExists()
        super().add(triple_or_quad)

    def addN(self, triple_or_quad):
        if self._template:
            _copyIfNotExists()
        super().addN(triple_or_quad)

    def remove(self, triple_or_quad):
        if self._template:
            _copyIfNotExists()
        super().remove(triple_or_quad)

    def triples(self, triple):
        if self not in self._store.contexts(None):
            return self._template.triples(triple)
        else:
            return super().triples(triple)

    @property
    def store(self):
        if self not in self._store.contexts(None):
            return self._template.store
        else:
            return self._store

    def __isub__(self, other):
        """Subtract all triples in Graph other from Graph.

        BNode IDs are not changed.
        """
        for triple in other:
            self.remove(triple)
        return self

    def __len__(self):
        if self not in self.store.contexts(None):
            return self._template.store.__len__(context=self)
        else:
            return self.store.__len__(context=self)


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
        return "<InMemoryGraphAggregate: {}|{} graphs>".format(
            len(self.store.contexts()),
            len((c for c in self.graphs() if c not in self.store.contexts()))
        )

    @property
    def is_dirty(self):
        return len(list(self.store.contexts())) > 0

    def _graph(self, c):
        if c is None:
            return None
        if not isinstance(c, Graph):
            return self.get_context(c)
        else:
            return self.get_context(c.identifier)

    def add(self, triple_or_quad):
        s, p, o, c = self._spoc(triple_or_quad, default=True)

        if c not in self.store.contexts(None):
            self.store.addN((_s, _p, _o, c)
                            for _s, _p, _o in c.triples((None, None, None)))

        self.store.add((s, p, o), context=c, quoted=False)

    def addN(self, quads):
        def do(g):
            g = self._graph(g)

            if g not in self.store.contexts(None):
                self.store.addN((_s, _p, _o, g)
                                for _s, _p, _o in g.triples((None, None, None)))

            return g

        self.store.addN((s, p, o, do(c)) for s, p, o, c in quads)

    def remove(self, triple_or_quad):
        s, p, o, c = self._spoc(triple_or_quad)

        if c not in self.store.contexts(None):
            self.store.addN((_s, _p, _o, c)
                            for _s, _p, _o in c.triples((None, None, None)))

        self.store.remove((s, p, o), context=c)

    def contexts(self, triple=None):
        if triple is None or triple is (None, None, None):
            contexts = (context for context in self._contexts)
        else:
            contexts = (
                context for context in self._contexts if triple in context)

        return list(set(chain(self.store.contexts(triple), contexts)))

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

    def _lookup(self, identifier):
        return next((x for x in self._contexts if x.identifier == identifier), None)

    def get_context(self, identifier, quoted=False):
        if isinstance(identifier, Graph):
            identifier = identifier.identifier
        return CopyOnEditGraph(
            store=self.store, identifier=identifier, namespace_manager=self,
            template=self._lookup(identifier)
        )
