#!/usr/bin/env python3

import logging

from rdflib.plugins.sparql import parser, algebra
from rdflib.plugins import sparql

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
