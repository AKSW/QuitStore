#!/usr/bin/env python3
from quit.exceptions import SparqlProtocolError
from rdflib.term import URIRef
from rdflib.plugins.sparql.parserutils import CompValue, plist

import logging

import os
from rdflib.plugins.sparql import parser, algebra
from rdflib.plugins import sparql
from uritools import urisplit

logger = logging.getLogger('quit.helpers')


class QueryAnalyzer:
    """A class that provides methods for received sparql query strings.

    This class is used to classify a given query string.
    At the moment the class distinguishes between SPARQL Update and Select queries.
    """

    logger = logging.getLogger('quit.helpers.QueryAnalyzer')

    def __init__(self, querystring, graph=None):
        """Initialize a check for a given query string.

        Args:
            querystring: A string containing a query.
        """
        self.query = querystring
        self.parsedQuery = None
        self.queryType = None
        self.actions = None

        if self.evalQuery(querystring):
            return

        if self.evalUpdate(querystring, graph):
            return

        return

    def prepareUpdate(self, updateString, initNs={}, base=None):
        """Parse and translate a SPARQL Query."""
        parsedUpdate = parser.parseUpdate(str(updateString))
        return algebra.translateUpdate(parsedUpdate, base, initNs)

    def getType(self):
        """Return the type of a query.

        Returns:
            A string containing the query type.
        """
        return self.queryType

    def getActions(self):
        """Return the type of a query.

        Returns:
            A string containing the query type.
        """
        return self.actionsType

    def getParsedQuery(self):
        """Return the query object (rdflib) of a query string.

        Returns:
            The query object after a query string was parsed with Rdflib.
        """
        return self.parsedQuery

    def evalQuery(self, querystring):
        """Check if the given querystring contains valid SPARQL queries.

        Returns:
            True, if querystring is valid.
            Else, if not.
        """
        try:
            self.parsedQuery = sparql.prepareQuery(querystring)
            logger.debug(str(self.parsedQuery.algebra.name))
            if str(self.parsedQuery.algebra.name) == 'DescribeQuery':
                self.queryType = 'DESCRIBE'
            elif str(self.parsedQuery.algebra.name) == 'ConstructQuery':
                self.queryType = 'CONSTRUCT'
            elif str(self.parsedQuery.algebra.name) == 'SelectQuery':
                self.queryType = 'SELECT'
            elif str(self.parsedQuery.algebra.name) == 'AskQuery':
                self.queryType = 'ASK'
            return True
        except Exception:
            return False

    def evalUpdate(self, querystring, graph):
        """Check if the given querystring contains (a) valid SPARQL update query(ies).

        Returns:
            True, if querystring is valid.
            Else, if not.
        """
        self.parsedQuery = self.prepareUpdate(querystring)
        self.queryType = 'UPDATE'
        return


def isAbsoluteUri(uri):
    """Check if a URI is a absolute URI and uses 'http(s)' at protocol part.

    Returns:
        True, if absolute http(s) URIs
        False, if not
    """
    try:
        parsed = urisplit(uri)
    except Exception:
        return False
    # We accept Absolute URI as specified in https://tools.ietf.org/html/rfc3986#section-4.3
    # with http(s) scheme
    if parsed[0] and parsed[0] in ['http', 'https'] and parsed[1] and not parsed[4] and (
            parsed[2] == '/' or os.path.isabs(parsed[2])):
        return True
    else:
        return False


def rewrite_graphs(parsed_query, default_graphs, named_graphs, sparql):
    """Add or substitute default and named graph URI.

    According to https://www.w3.org/TR/sparql11-protocol/ we will remove the named and default graph
    URIs given in the query string (if given) and will add default-graph-uri and named-graph-uri
    from protocol request.
    For update query string we will add using-named-graph-uri and using-graph-uri if the update
    requst does not contain a USING, USING NAMED, or WITH clause.

    Args: parsed_query: the parsed query or update
          default_graphs: a list of uri strings for default graphs
          named_graphs: a list of uri strings for named graphs
          sparql: a string to distinguish between 'query' and 'update'
    """
    if not isinstance(default_graphs, list) and not isinstance(named_graphs, list):
        return parsed_query

    if len(default_graphs) == 0 and len(named_graphs) == 0:
        return parsed_query

    if sparql == 'query':
        # clean existing named (FROM NAMED) and default (FROM) DatasetClauses
        parsed_query[1]['datasetClause'] = plist()

        # add new named (default-graph-uri) and default (named-graph-uri)
        # DatasetClauses from Protocol
        for uri in default_graphs:
            parsed_query[1]['datasetClause'].append(CompValue('DatasetClause', default=URIRef(uri)))
        for uri in named_graphs:
            parsed_query[1]['datasetClause'].append(CompValue('DatasetClause', named=URIRef(uri)))

        return parsed_query

    elif sparql == 'update':
        if parsed_query.request[0].withClause is not None:
            raise SparqlProtocolError

        if parsed_query.request[0].using is not None:
            raise SparqlProtocolError

        parsed_query.request[0]['using'] = plist()

        # add new named (using-named-graph-uri) and default (using-graph-uri)
        # UsingClauses from Protocol
        for uri in default_graphs:
            parsed_query.request[0]['using'].append(CompValue('UsingClause', default=URIRef(uri)))
        for uri in named_graphs:
            parsed_query.request[0]['using'].append(CompValue('UsingClause', named=URIRef(uri)))

        return parsed_query


def is_valid_base(parsed_query, type):
    """Check if a query/update contains a absolute base if base is given.

    Args: parsed_query: the parsed query or update
          type: a string to distinguish between 'query' and 'update'
    Returns: True - if Base URI is given and abolute or if no Base is given
             False - if Base URI is given an not absolute
    """
    if type == 'query':
        for value in parsed_query[0]:
            if value.name == 'Base' and not isAbsoluteUri(value.iri):
                return False
    elif type == 'update':
        for value in parsed_query.prologue[0]:
            if value.name == 'Base' and not isAbsoluteUri(value.iri):
                return False

    return True
