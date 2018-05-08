#!/usr/bin/env python3

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
