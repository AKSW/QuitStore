"""

Code for carrying out Update Operations

"""
from rdflib import Graph, Variable, URIRef
from rdflib.term import Node

from rdflib.plugins.sparql.sparql import QueryContext
from rdflib.plugins.sparql.evalutils import _fillTemplate, _join
from rdflib.plugins.sparql.evaluate import evalBGP, evalPart

from itertools import tee
from quit.exceptions import UnSupportedQuery

from typing import Optional, Sequence
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.sparql import QueryContext

import rdflib.plugins.sparql.update as rdflib_update

def _append(dct, identifier, action, items):
    if items:
        if not isinstance(identifier, Node):
            identifier = URIRef(identifier)
        changes = dct.get(identifier, [])
        changes.append((action, items))
        dct[identifier] = changes

def _filterExistingTriples(g, triples):
    return list(filter(lambda triple: triple not in g, triples))

def _filterNonExistingTriples(g, triples):
    return list(filter(lambda triple: triple in g, triples))

def evalLoad(ctx, u):
    """
    TODO
    http://www.w3.org/TR/sparql11-update/#load
    """
    res = {}
    res["type"] = "LOAD"
    res["source"] = u.iri
    res["delta"] = {}

    if not u.graphiri:
        raise UnSupportedQuery("For load queries we need a iriref for a target graph")

    success = False
    loadedGraph = None
    exceptions = []
    formats = [None, 'n3', 'nt', 'turtle']
    for format in formats:
        loadedGraph = Graph()
        try:
            if not format:
                loadedGraph.parse(u.iri)
            else:
                loadedGraph.parse(u.iri, format=format)
            success = True
            break
        except Exception as e:
            pass
    if not success:
        raise Exception(
            "Could not load %s as either RDF/XML, N3, Turtle, or NTriples" % (
            u.iri))

    graph = ctx.dataset.get_context(u.graphiri)
    graph += loadedGraph

    _append(res["delta"], u.graphiri, 'additions', loadedGraph)

    return res

def evalInsertData(ctx: QueryContext, u: CompValue) -> dict:
    """
    http://www.w3.org/TR/sparql11-update/#insertData
    """

    res = {}
    res["type"] = "INSERT"
    res["delta"] = {}

    # add triples
    g = ctx.graph
    filled = _filterNonExistingTriples(g, u.triples)
    _append(res["delta"], 'default', 'additions', filled)

    # add quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        # type error: Argument 1 to "get_context" of "ConjunctiveGraph" has incompatible type "Optional[Graph]"; expected "Union[IdentifiedNode, str, None]"
        cg = ctx.dataset.get_context(g)  # type: ignore[arg-type]
        filledq = _filterExistingTriples(cg, u.quads[g])
        _append(res["delta"], cg.identifier, 'additions', filledq)

    rdflib_update.evalInsertData(ctx, u)

    return res


def evalDeleteData(ctx: QueryContext, u: CompValue) -> dict:
    """
    http://www.w3.org/TR/sparql11-update/#deleteData
    """

    res = {}
    res["type"] = "DELETE"
    res["delta"] = {}

    # remove triples
    g = ctx.graph
    filled = _filterNonExistingTriples(g, u.triples)
    _append(res["delta"], 'default', 'removals', filled)

    # remove quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads:
        # type error: Argument 1 to "get_context" of "ConjunctiveGraph" has incompatible type "Optional[Graph]"; expected "Union[IdentifiedNode, str, None]"
        cg = ctx.dataset.get_context(g)
        filledq = _filterNonExistingTriples(cg, u.quads[g])
        _append(res["delta"], cg.identifier, 'removals', filledq)

    rdflib_update.evalDeleteData(ctx, u)

    return res


def evalDeleteWhere(ctx, u):
    """
    TODO
    http://www.w3.org/TR/sparql11-update/#deleteWhere
    """

    res = {}
    res["type"] = "DELETEWHERE"
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

    #rdflib_update.evalDeleteWhere(ctx, u)

    return res


def evalModify(ctx, u):
    """
    TODO
    """
    originalctx = ctx

    res = {}
    res["type"] = "MODIFY"
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


def evalUpdate(graph, update, initBindings=None, actionLog=False):
    """
    TODO
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

    .. caution::

        This method can access indirectly requested network endpoints, for
        example, query processing will attempt to access network endpoints
        specified in ``SERVICE`` directives.

        When processing untrusted or potentially malicious queries, measures
        should be taken to restrict network and file access.

        For information on available security measures, see the RDFLib
        :doc:`Security Considerations </security_considerations>`
        documentation.

    """

    res = []

    for u in update.algebra:
        initBindings = dict((Variable(k), v) for k, v in initBindings.items())

        ctx = QueryContext(graph, initBindings=initBindings)
        ctx.prologue = u.prologue

        try:
            if u.name == 'Load':
                result = evalLoad(ctx, u)
                if result:
                    res.append(result)
            elif u.name == 'Clear':
                rdflib_update.evalClear(ctx, u)
            elif u.name == 'Drop':
                rdflib_update.evalDrop(ctx, u)
            elif u.name == 'Create':
                rdflib_update.evalCreate(ctx, u)
            elif u.name == 'Add':
                rdflib_update.evalAdd(ctx, u)
            elif u.name == 'Move':
                rdflib_update.evalMove(ctx, u)
            elif u.name == 'Copy':
                rdflib_update.evalCopy(ctx, u)
            elif u.name == 'InsertData':
                result = evalInsertData(ctx, u)
                if result:
                    res.append(result)
            elif u.name == 'DeleteData':
                result = evalDeleteData(ctx, u)
                if result:
                    res.append(result)
            elif u.name == 'DeleteWhere':
                result = evalDeleteWhere(ctx, u)
                if result:
                    res.append(result)
            elif u.name == 'Modify':
                result = evalModify(ctx, u)
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
