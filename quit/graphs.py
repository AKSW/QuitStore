import rdflib.plugin as plugin

from rdflib import Graph, Literal, URIRef, ConjunctiveGraph, Dataset
from rdflib.graph import ReadOnlyGraphAggregate, ModificationException, UnSupportedAggregateOperation, Path

class RevisionGraph(Graph):

    def __init__(self, id = None, store = 'default', public = None, private = None, namespace_manager = None, local = False):
        super().__init__(store=store, identifier=public, namespace_manager=namespace_manager)
        self.id = id
        
        self.__private_identifier = private
        self.__public_identifier = public
        self.rewrite = False    

    def __get_identifier(self):
        if not self.rewrite:        
            return self.__private_identifier
        else:
            return self.__public_identifier
    identifier = property(__get_identifier)  # read-only attr

class InstanceGraph(ConjunctiveGraph):
    def __init__(self, store='default', mappings=dict(), local=False):
        super().__init__(store=store)
        
        self.mappings = mappings
        self.dirty = False

    @property
    def is_dirty(self):
        return self.dirty

    def _localize(self):
        if not self.local:
            old_store = self.store
            new_store = plugin.get('default', Store)()
            new_store += old_store
            self._Graph__store = store = new_store

    def add(self, xxx_todo_changeme):
        self.dirty = True
        if not self.local:
            self._localize()
        super().add(xxx_todo_changeme)

    def addN(self, quads):
        self.dirty = True
        if not self.local:
            self._localize()
        super().addN(quads)

    def remove(self, xxx_todo_changeme1):
        self.dirty = True
        if not self.local:
            self._localize()
        super().remove(xxx_todo_changeme1)

    def __iadd__(self, other):
        self.dirty = True
        if not self.local:
            self._localize()
        super().__iadd__(other)

    def __isub__(self, other):
        self.dirty = True
        if not self.local:
            self._localize()
        super().__isub__(other)
        
    def get_context(self, identifier, quoted=False):
        mapping = self.mappings.get(identifier, None)
        if not mapping:
            mapping = [identifier, identifier]
        return RevisionGraph(store=self.store, public=mapping[0], private=mapping[1], namespace_manager=self)    

    def triples(self, xxx_todo_changeme8):
        (s, p, o) = xxx_todo_changeme8
        for graph in [self.get_context(x) for x in self.mappings.keys()]:
            if isinstance(p, Path):
                for s, o in p.eval(self, s, o):
                    yield s, p, o
            else:
                for s1, p1, o1 in graph.triples((s, p, o)):
                    yield (s1, p1, o1)

    def __contains__(self, triple_or_quad):
        context = None
        if len(triple_or_quad) == 4:
            context = triple_or_quad[3]
        for graph in [self.get_context(x) for x in self.mappings.keys()]:
            if context is None or graph.identifier == context.identifier:
                if triple_or_quad[:3] in graph:
                    return True
        return False

    def quads(self, xxx_todo_changeme9):
        """Iterate over all the quads in the entire aggregate graph"""
        (s, p, o) = xxx_todo_changeme9
        for graph in [self.get_context(x) for x in self.mappings.keys()]:
            for s1, p1, o1 in graph.triples((s, p, o)):
                yield (s1, p1, o1, graph)

    def __len__(self):
        return sum(len(g) for g in [self.get_context(x) for x in self.mappings.keys()])

    def __repr__(self):
        return "<InstanceGraph: %s graphs>" % len(self.graphs)