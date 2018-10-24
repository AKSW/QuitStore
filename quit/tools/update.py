"""

Code for carrying out Update Operations

"""
import functools

from rdflib import Graph, Variable, URIRef
from rdflib.term import Node

from rdflib.plugins.sparql.sparql import QueryContext
from rdflib.plugins.sparql.evalutils import _fillTemplate, _join
from rdflib.plugins.sparql.evaluate import evalBGP, evalPart

from collections import defaultdict
from itertools import tee
from quit.exceptions import UnSupportedQuery

def _append(dct, identifier, action, items):
    if items:
        if not isinstance(identifier, Node):
            identifier = URIRef(identifier)
        changes = dct.get(identifier, [])
        changes.append((action, items))
        dct[identifier] = changes


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
    res = {}
    res["type_"] = "LOAD"
    res["graph"] = u.iri

    if u.graphiri:
        ctx.load(u.iri, default=False, publicID=u.graphiri)
    else:
        ctx.load(u.iri, default=True)

    return res


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

    res = {}
    res["type_"] = "INSERT"
    res["delta"] = {}

    # add triples
    g = ctx.graph
    filled = list(filter(lambda triple: triple not in g, u.triples))
    if filled:
        _append(res["delta"], 'default', 'additions', filled)
        g += filled

    # add quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        filledq = list(filter(lambda triple: triple not in cg, u.quads[g]))
        if filledq:
            _append(res["delta"], cg.identifier, 'additions', filledq)
            cg += filledq

    return res


def evalDeleteData(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteData
    """
    res = {}
    res["type_"] = "DELETE"
    res["delta"] = {}

    # remove triples
    g = ctx.graph
    filled = list(filter(lambda triple: triple in g, u.triples))
    if filled:
        _append(res["delta"], 'default', 'removals', filled)
        g -= filled

    # remove quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        filledq = list(filter(lambda triple: triple in cg, u.quads[g]))
        if filledq:
            _append(res["delta"], cg.identifier, 'removals', filledq)
            cg -= filledq

    return res


def evalDeleteWhere(ctx, u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteWhere
    """

    res = {}
    res["type_"] = "DELETEWHERE"
    res["delta"] = {}

    _res = evalBGP(ctx, u.triples)
    for g in u.quads:
        cg = ctx.dataset.get_context(g)
        c = ctx.pushGraph(cg)
        _res = _join(_res, list(evalBGP(c, u.quads[g])))

    for c in _res:
        g = ctx.graph
        filled, filled_delta = tee(_fillTemplate(u.triples, c))
        _append(res["delta"], 'default', 'removals', list(filled_delta))
        g -= filled

        for g in u.quads:
            cg = ctx.dataset.get_context(c.get(g))
            filledq, filledq_delta = tee(_fillTemplate(u.quads[g], c))
            _append(res["delta"], cg.identifier, 'removals', list(filledq_delta))
            cg -= filledq

    return res


def evalModify(ctx, u):
    originalctx = ctx

    res = {}
    res["type_"] = "MODIFY"
    res["delta"] = {}

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

            # TODO re-enable original behaviour if USING NAMED works with named graphs
            # https://github.com/AKSW/QuitStore/issues/144
            elif d.named:
                if otherDefault:
                    ctx = originalctx  # restore original default graph
                raise UnSupportedQuery
            #     g = d.named
            #     ctx.load(g, default=False)

    # "The WITH clause provides a convenience for when an operation
    # primarily refers to a single graph. If a graph name is specified
    # in a WITH clause, then - for the purposes of evaluating the
    # WHERE clause - this will define an RDF Dataset containing a
    # default graph with the specified name, but only in the absence
    # of USING or USING NAMED clauses. In the presence of one or more
    # graphs referred to in USING clauses and/or USING NAMED clauses,
    # the WITH clause will be ignored while evaluating the WHERE
    # clause."
    graphName = 'default'
    if not u.using and u.withClause:
        g = ctx.dataset.get_context(u.withClause)
        graphName = str(g.identifier)
        ctx = ctx.pushGraph(g)

    _res = evalPart(ctx, u.where)

    if u.using:
        if otherDefault:
            ctx = originalctx  # restore original default graph
        if u.withClause:
            g = ctx.dataset.get_context(u.withClause)
            graphName = str(g.identifier)
            ctx = ctx.pushGraph(g)

    for c in _res:
        dg = ctx.graph
        if u.delete:
            filled, filled_delta = tee(_fillTemplate(u.delete.triples, c))
            _append(res["delta"], graphName, 'removals', list(filled_delta))
            dg -= filled

            for g, q in u.delete.quads.items():
                cg = ctx.dataset.get_context(c.get(g))
                filledq, filledq_delta = tee(_fillTemplate(q, c))
                _append(res["delta"], cg.identifier, 'removals', list(filledq_delta))
                cg -= filledq

        if u.insert:
            filled, filled_delta = tee(_fillTemplate(u.insert.triples, c))
            _append(res["delta"], graphName, 'additions', list(filled_delta))
            dg += filled

            for g, q in u.insert.quads.items():
                cg = ctx.dataset.get_context(c.get(g))
                filledq, filledq_delta = tee(_fillTemplate(q, c))
                _append(res["delta"], cg.identifier, 'additions', list(filledq_delta))
                cg += filledq

    return res


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

    res = []

    for u in update:

        ctx = QueryContext(graph)
        ctx.prologue = u.prologue

        if initBindings:
            for k, v in initBindings.items():
                if not isinstance(k, Variable):
                    k = Variable(k)
                ctx[k] = v

        try:
            if u.name == 'Load':
                result = evalLoad(ctx, u).get('delta', None)
                if result:
                    res.append(result)
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
                result = evalInsertData(ctx, u).get('delta', None)
                if result:
                    res.append(result)
            elif u.name == 'DeleteData':
                result = evalDeleteData(ctx, u).get('delta', None)
                if result:
                    res.append(result)
            elif u.name == 'DeleteWhere':
                result = evalDeleteWhere(ctx, u).get('delta', None)
                if result:
                    res.append(result)
            elif u.name == 'Modify':
                result = evalModify(ctx, u).get('delta', None)
                if result:
                    res.append(result)
            else:
                raise Exception('Unknown update operation: %s' % (u,))
        except UnSupportedQuery as e:
            return res, e
        except Exception:
            if not u.silent:
                raise
    return res, None
