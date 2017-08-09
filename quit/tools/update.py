"""

Code for carrying out Update Operations

"""

from rdflib import Graph, Variable

from rdflib.plugins.sparql.sparql import QueryContext
from rdflib.plugins.sparql.evalutils import _fillTemplate, _join
from rdflib.plugins.sparql.evaluate import evalBGP, evalPart

from collections import defaultdict

def _graphOrDefault(ctx, g):
    if g == 'DEFAULT':
        return ctx.graph
    else:
        return ctx.dataset.get_context(g)


def _graphAll(ctx, g):
    """
    return a list of graphs
    """
    if g == 'DEFAULT':
        return [ctx.graph]
    elif g == 'NAMED':
        return [c for c in ctx.dataset.contexts()
                if c.identifier != ctx.graph.identifier]
    elif g == 'ALL':
        return list(ctx.dataset.contexts())
    else:
        return [ctx.dataset.get_context(g)]


def evalLoad(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#load
    """
    if u.graphiri:
        ctx.load(u.iri, default=False, publicID=u.graphiri)
    else:
        ctx.load(u.iri, default=True)


def evalCreate(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#create
    """
    g = ctx.datset.get_context(u.graphiri)
    if len(g) > 0:
        raise Exception("Graph %s already exists." % g.identifier)
    raise Exception("Create not implemented!")


def evalClear(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#clear
    """
    for g in _graphAll(ctx, u.graphiri):
        g.remove((None, None, None))


def evalDrop(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#drop
    """
    if ctx.dataset.store.graph_aware:
        for g in _graphAll(ctx, u.graphiri):
            ctx.dataset.store.remove_graph(g)
    else:
        evalClear(ctx, u)


def evalInsertData(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#insertData
    """
    insertedtriples = defaultdict(set)

    # add triples
    g = ctx.graph
    for triple in u.triples:
        if g.triples(triple):
            insertedtriples['insert'].add((triple, 'default'))
    g += u.triples

    # add quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        for triple in u.quads[g]:
            if cg.triples(triple):
                insertedtriples['insert'].add((triple, cg.identifier))
        cg += u.quads[g]

    return insertedtriples


def evalDeleteData(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteData
    """
    deletedtriples = defaultdict(set)

    # remove triples
    g = ctx.graph

    for triple in u.triples:
        if g.triples(triple):
            deletedtriples['delete'].add((triple, 'default'))
    g -= u.triples

    # remove quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        for triple in u.quads[g]:
            if cg.triples(triple):
                deletedtriples['delete'].add((triple, cg.identifier))
        cg -= u.quads[g]

    return deletedtriples


def evalDeleteWhere(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteWhere
    """
    res = evalBGP(ctx, u.triples)
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        c = ctx.pushGraph(cg)
        res = _join(res, list(evalBGP(c, u.quads[g])))

    deletedtriples = defaultdict(set)

    for c in res:
        g = ctx.graph
        filled = _fillTemplate(u.triples, c)
        for item in filled:
            triple = (item[0], item[1], item[2])
            deletedtriples['delete'].add((triple, 'default'))
        g -= filled

        for g in u.quads:
            cg = ctx.dataset.get_context(c.get(g))
            filledq = _fillTemplate(u.quads[g], c)
            for itemq in filledq:
                triple = (itemq[0], itemq[1], itemq[2])
                deletedtriples['delete'].add((triple, cg.identifier))
            cg -= filledq

    return deletedtriples


def evalModify(ctx, u):
    originalctx = ctx

    # Using replaces the dataset for evaluating the where-clause
    if u.using:
        otherDefault = False
        for d in u.using:
            if d.default:

                if not otherDefault:
                    # replace current default graph
                    dg = Graph()
                    ctx = ctx.pushGraph(dg)
                    otherDefault = True

                ctx.load(d.default, default=True)

            elif d.named:
                g = d.named
                ctx.load(g, default=False)

    # "The WITH clause provides a convenience for when an operation
    # primarily refers to a single graph. If a graph name is specified
    # in a WITH clause, then - for the purposes of evaluating the
    # WHERE clause - this will define an RDF Dataset containing a
    # default graph with the specified name, but only in the absence
    # of USING or USING NAMED clauses. In the presence of one or more
    # graphs referred to in USING clauses and/or USING NAMED clauses,
    # the WITH clause will be ignored while evaluating the WHERE
    # clause."
    if not u.using and u.withClause:
        g = ctx.dataset.get_context(u.withClause)
        ctx = ctx.pushGraph(g)

    res = evalPart(ctx, u.where)
    modifiedtriples = defaultdict(set)

    if u.using:
        if otherDefault:
            ctx = originalctx  # restore original default graph
        if u.withClause:
            g = ctx.dataset.get_context(u.withClause)
            ctx = ctx.pushGraph(g)

    for c in res:
        dg = ctx.graph
        if u.delete:
            filled = _fillTemplate(u.delete.triples, c)
            for item in filled:
                triple = (item[0], item[1], item[2])
                modifiedtriples['insert'].add((triple, 'default'))
            dg -= filled

            for g, q in u.delete.quads.items():
                cg = ctx.dataset.get_context(c.get(g))
                filledq = _fillTemplate(q, c)
                for itemq in filledq:
                    triple = (itemq[0], itemq[1], itemq[2])
                    modifiedtriples['insert'].add((triple, cg.identifier))
                cg -= filledq

        if u.insert:
            filled = _fillTemplate(u.insert.triples, c)
            for item in filled:
                modifiedtriples['delete'].add((triple, 'default'))
            dg += filled

            for g, q in u.insert.quads.items():
                cg = ctx.dataset.get_context(c.get(g))
                filledq = _fillTemplate(q, c)
                for itemq in filledq:
                    modifiedtriples['delete'].add((triple, cg.identifier))
                cg += filledq

    return modifiedtriples


def evalAdd(ctx, u):
    """

    add all triples from src to dst

    http://www.w3.org/TR/sparql11-update/#add
    """
    src, dst = u.graph

    srcg = _graphOrDefault(ctx, src)
    dstg = _graphOrDefault(ctx, dst)

    if srcg.identifier == dstg.identifier:
        return

    dstg += srcg


def evalMove(ctx, u):
    """
    remove all triples from dst
    add all triples from src to dst
    remove all triples from src

    http://www.w3.org/TR/sparql11-update/#move
    """

    src, dst = u.graph

    srcg = _graphOrDefault(ctx, src)
    dstg = _graphOrDefault(ctx, dst)

    if srcg.identifier == dstg.identifier:
        return

    dstg.remove((None, None, None))

    dstg += srcg

    if ctx.dataset.store.graph_aware:
        ctx.dataset.store.remove_graph(srcg)
    else:
        srcg.remove((None, None, None))


def evalCopy(ctx, u):
    """
    remove all triples from dst
    add all triples from src to dst

    http://www.w3.org/TR/sparql11-update/#copy
    """

    src, dst = u.graph

    srcg = _graphOrDefault(ctx, src)
    dstg = _graphOrDefault(ctx, dst)

    if srcg.identifier == dstg.identifier:
        return

    dstg.remove((None, None, None))

    dstg += srcg


def evalUpdate(graph, update, initBindings=None, actionLog=False):
    """
    http://www.w3.org/TR/sparql11-update/#updateLanguage

    'A request is a sequence of operations [...] Implementations MUST
    ensure that operations of a single request are executed in a
    fashion that guarantees the same effects as executing them in
    lexical order.

    Operations all result either in success or failure.

    If multiple operations are present in a single request, then a
    result of failure from any operation MUST abort the sequence of
    operations, causing the subsequent operations to be ignored.'

    This will return None on success and raise Exceptions on error

    """

    for u in update:

        ctx = QueryContext(graph)
        ctx.prologue = u.prologue

        if initBindings:
            for k, v in initBindings.items():
                if not isinstance(k, Variable):
                    k = Variable(k)
                ctx[k] = v
            # ctx.push()  # nescessary?

        changes = defaultdict(set)
        try:
            if u.name == 'Load':
                evalLoad(ctx, u)
            elif u.name == 'Clear':
                evalClear(ctx, u)
            elif u.name == 'Drop':
                evalDrop(ctx, u)
            elif u.name == 'Create':
                evalCreate(ctx, u)
            elif u.name == 'Add':
                evalAdd(ctx, u)
            elif u.name == 'Move':
                evalMove(ctx, u)
            elif u.name == 'Copy':
                evalCopy(ctx, u)
            elif u.name == 'InsertData':
                changes = evalInsertData(ctx, u)
            elif u.name == 'DeleteData':
                changes = evalDeleteData(ctx, u)
            elif u.name == 'DeleteWhere':
                changes = evalDeleteWhere(ctx, u)
            elif u.name == 'Modify':
                changes = evalModify(ctx, u)
            else:
                raise Exception('Unknown update operation: %s' % (u,))
        except:
            if not u.silent:
                raise
    return changes or defaultdict(set)
