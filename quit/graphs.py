from rdflib import Graph, Literal, URIRef, ConjunctiveGraph, Dataset

class RevisionGraph(Graph):

    def __init__(self, id = None, store = 'default', identifier = None, namespace_manager = None):
        super().__init__(store=store, identifier=identifier, namespace_manager=namespace_manager)
        self.id = id

class InstanceGraph(ConjunctiveGraph):
    def __init__(self, graphs):
        super().__init__()
        
        self.graphs = graphs
        self.dirty = False

    @property
    def is_dirty(self):
        return self.dirty

    def destroy(self, configuration):
        raise Exception()

    # Transactional interfaces (optional)
    def commit(self):
        pass

    def rollback(self):
        pass

    def open(self, configuration, create = False):
        for k, v in self.graphs.items():
            v.open(self, configuration, create)

    def close(self):
        for k, v in self.graphs.items():
            v.close()

    def add(self, triple_or_quad):
        context = None
        if len(triple_or_quad) == 4:
            context = triple_or_quad[3]

        if context in self.graphs.keys():
            for k, v in self.graphs.items():
                if context is None:
                    continue
                if k == context:
                    if not self.graphs[k] or not self.graphs[k].editable:
                        tmp = RevisionGraph(identifier=k)
                        tmp += v
                        self.graphs[k] = tmp
                        self.dirty = True
                    self.graphs[k].add(triple_or_quad[:3])  
        else: 
            k = context
            if not self.graphs.get(k):
                self.graphs[k] = RevisionGraph(identifier=context)
                self.dirty = True
            self.graphs[k].add(triple_or_quad[:3])  

    def addN(self, quads):
        for s,p,o,c in quads:
            self.add((s,p,o,c))

    def remove(self, triple_or_quad):
        s,p,o,context = self._spoc(triple_or_quad, default=True)

        for k, v in self.graphs.items():
            if context is None:
                continue
            if k == context:
                if not self.graphs[k].editable:
                    tmp = RevisionGraph(identifier=k)
                    tmp += v
                    self.graphs[k] = tmp
                    self.dirty = True
                self.graphs[k].remove(triple_or_quad[:3])

    def triples(self, triple_or_quad):
        context = None
        if len(triple_or_quad) == 4:
            context = triple_or_quad[3]

        for k, v in self.graphs.items():
            if context is None or k == context:
                for s1, p1, o1 in v.triples(triple_or_quad[:3]):
                    yield (s1, p1, o1)

    def __contains__(self, triple_or_quad):
        context = None
        if len(triple_or_quad) == 4:
            context = triple_or_quad[3]

        for k, v in self.graphs.items():
            if context is None or k == context:
                if triple_or_quad[:3] in v:
                    return True
        return False

    def quads(self, quad):
        (s, p, o, context) = quad
        for k, v in self.graphs.items():
            if context is None or k == context:
                for s1, p1, o1 in v.triples((s, p, o)):
                    yield (s1, p1, o1, k)

    def __len__(self):
        (print(g) for g in self.graphs)
        return sum(len(g) for g in self.graphs)

    def contexts(self, triple = None):
        for k, v in self.graphs.items():
            if triple is None or triple in v:                     
                yield v

    def get_context(self, identifier, quoted = False):
        print('asked: %s'% identifier)
        for k, v in self.graphs.items():
            if k == identifier:
                return v
        return Graph(identifier=identifier)

    def __hash__(self):
        raise UnSupportedAggregateOperation()

    def __cmp__(self, other):
        if other is None:
            return -1
        elif isinstance(other, Graph):
            return -1
        elif isinstance(other, InstanceGraph):
            return cmp(self.graphs, other.graphs)
        else:
            return -1

    def __iadd__(self, other):
        print(other)
        self.addN((s, p, o, self) for s, p, o in other)
        return self

    def __isub__(self, other):
        print(other)
        for triple in other:
            self.remove(triple)
        return self

    # Conv.  methods

    def triples_choices(self,triple_or_quad):
        s,p,o,context = self._spoc(triple_or_quad)

        for k, v in self.graphs.items():
            if context is None or k == context.identifier:
                for (s1, p1, o1) in v.triples_choices((s, p, o)):
                    yield (s1, p1, o1, k)

    def qname(self, uri):
        if hasattr(self, 'namespace_manager') and self.namespace_manager:
            return self.namespace_manager.qname(uri)
        raise Exception()

    def compute_qname(self, uri, generate = True):
        if hasattr(self, 'namespace_manager') and self.namespace_manager:
            return self.namespace_manager.compute_qname(uri, generate)
        raise Exception()

    def bind(self, prefix, namespace, override = True):
        raise Exception()

    def namespaces(self):
        if hasattr(self, 'namespace_manager'):
            for prefix, namespace in self.namespace_manager.namespaces():
                yield prefix, namespace
        else:
            for graph in self.graphs:
                for prefix, namespace in graph.namespaces():
                    yield prefix, namespace

    def absolutize(self, uri, defrag = 1):
        raise Exception()

    def parse(self, source, publicID = None, format = "xml", **args):
        raise Exception()

    def n3(self):
        raise Exception()

    def __reduce__(self):
        raise Exception()

    def __repr__(self):
        return "<InstanceGraph: %s graphs>" % len(self.graphs)