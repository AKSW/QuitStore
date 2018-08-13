#!/usr/bin/env python3
import logging
import os
from pyparsing import ParseException
from quit.exceptions import UnSupportedQuery, SparqlProtocolError, NonAbsoluteBaseError
from rdflib.term import URIRef
from rdflib.plugins.sparql.parserutils import CompValue, plist
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql import parser, algebra
from rdflib.plugins import sparql
from uritools import urisplit
from werkzeug.http import parse_accept_header, parse_options_header

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


def configure_query_dataset(parsed_query, default_graphs, named_graphs):
    """Substitute the default and named graph URI.

    According to https://www.w3.org/TR/sparql11-protocol/ we will remove the named and default graph
    URIs given in the query string (if given) and will add default-graph-uri and named-graph-uri
    from protocol request.

    Args: parsed_query: the parsed query
          default_graphs: a list of uri strings for default graphs
          named_graphs: a list of uri strings for named graphs
    """
    if not isinstance(default_graphs, list) or not isinstance(named_graphs, list):
        return parsed_query

    if len(default_graphs) == 0 and len(named_graphs) == 0:
        return parsed_query

    # clean existing named (FROM NAMED) and default (FROM) DatasetClauses
    parsed_query[1]['datasetClause'] = plist()

    # add new named (default-graph-uri) and default (named-graph-uri)
    # DatasetClauses from Protocol
    for uri in default_graphs:
        parsed_query[1]['datasetClause'].append(CompValue('DatasetClause', default=URIRef(uri)))
    for uri in named_graphs:
        parsed_query[1]['datasetClause'].append(CompValue('DatasetClause', named=URIRef(uri)))

    return parsed_query


def configure_update_dataset(parsed_update, default_graphs, named_graphs):
    """Add default and named graph URI.

    According to https://www.w3.org/TR/sparql11-protocol/ we will add using-named-graph-uri and
    using-graph-uri if the update requst does not contain a USING, USING NAMED, or WITH clause.

    Args: parsed_update: the parsed update
          default_graphs: a list of uri strings for default graphs
          named_graphs: a list of uri strings for named graphs
    """
    if not isinstance(default_graphs, list) or not isinstance(named_graphs, list):
        return parsed_update

    if len(default_graphs) == 0 and len(named_graphs) == 0:
        return parsed_update

    if parsed_update.request[0].withClause is not None:
        raise SparqlProtocolError

    if parsed_update.request[0].using is not None:
        raise SparqlProtocolError

    parsed_update.request[0]['using'] = plist()

    # add new named (using-named-graph-uri) and default (using-graph-uri)
    # UsingClauses from Protocol
    for uri in default_graphs:
        parsed_update.request[0]['using'].append(CompValue('UsingClause', default=URIRef(uri)))
    for uri in named_graphs:
        parsed_update.request[0]['using'].append(CompValue('UsingClause', named=URIRef(uri)))

    return parsed_update


def parse_query_type(query, base=None, default_graph=[], named_graph=[]):
    """Parse a query and add default and named graph uri if possible."""
    try:
        parsed_query = parseQuery(query)
        parsed_query = configure_query_dataset(parsed_query, default_graph, named_graph)
        translated_query = translateQuery(parsed_query, base=base)
    except ParseException:
        raise UnSupportedQuery()
    except SparqlProtocolError as e:
        raise e

    if base is not None and not isAbsoluteUri(base):
        raise NonAbsoluteBaseError()

    if not is_valid_query_base(parsed_query):
        raise NonAbsoluteBaseError()

    return translated_query.algebra.name, translated_query


def parse_update_type(query, base=None, default_graph=[], named_graph=[]):
    """Parse an update and add default and named graph uri if possible."""
    try:
        parsed_update = parseUpdate(query)
        parsed_update = configure_update_dataset(parsed_update, default_graph, named_graph)
        translated_update = translateUpdate(parsed_update, base=base)
    except ParseException:
        raise UnSupportedQuery()
    except SparqlProtocolError as e:
        raise e

    if base is not None and not isAbsoluteUri(base):
        raise NonAbsoluteBaseError()

    if not is_valid_update_base(parsed_update):
        raise NonAbsoluteBaseError()

    return parsed_update.request[0].name, translated_update


def is_valid_query_base(parsed_query):
    """Check if a query contains an absolute base if base is given.

    Args: parsed_query: the parsed query
    Returns: True - if Base URI is given and abolute or if no Base is given
             False - if Base URI is given an not absolute
    """
    for value in parsed_query[0]:
        if value.name == 'Base' and not isAbsoluteUri(value.iri):
            return False

    return True


def is_valid_update_base(parsed_update):
    """Check if an update contains an absolute base if base is given.

    Args: parsed_update: the parsed update
    Returns: True - if Base URI is given and abolute or if no Base is given
             False - if Base URI is given an not absolute
    """
    for value in parsed_update.prologue[0]:
        if value.name == 'Base' and not isAbsoluteUri(value.iri):
            return False

    return True


def parse_sparql_request(request):
    """Parse a request according to SPARQL 1.1. protocol and return needed information.

    Args:
        request: A flask HTTP request
    Returns:
        quintuple - query, type, mimetype, default_graph, named_graph
    """
    query = None
    type = None
    default_graph = []
    named_graph = []

    if request.method == "GET":
        default_graph = request.args.getlist('default-graph-uri')
        named_graph = request.args.getlist('named-graph-uri')
        query = request.args.get('query', None)
        type = 'query'
    elif request.method == "POST":
        if 'Content-Type' in request.headers:
            content_mimetype, options = parse_options_header(request.headers['Content-Type'])
            if content_mimetype == "application/x-www-form-urlencoded":
                if 'query' in request.form:
                    default_graph = request.form.getlist('default-graph-uri')
                    named_graph = request.form.getlist('named-graph-uri')
                    query = request.form.get('query', None)
                    type = 'query'
                elif 'update' in request.form:
                    default_graph = request.form.getlist('using-graph-uri')
                    named_graph = request.form.getlist('using-named-graph-uri')
                    query = request.form.get('update', None)
                    type = 'update'
            elif content_mimetype == "application/sparql-query":
                default_graph = request.args.getlist('default-graph-uri')
                named_graph = request.args.getlist('named-graph-uri')
                query = request.data.decode("utf-8")
                type = 'query'
            elif content_mimetype == "application/sparql-update":
                default_graph = request.args.getlist('using-graph-uri')
                named_graph = request.args.getlist('using-named-graph-uri')
                query = request.data.decode("utf-8")
                type = 'update'

    if 'Accept' in request.headers:
        logger.info('Received query via {}: {} with accept header: {}'.format(
            request.method, query, request.headers['Accept']))
        mimetype = parse_accept_header(request.headers['Accept']).best
    else:
        logger.info('Received query via {}: {} with no accept header.'.format(request.method,
                                                                              query))
        mimetype = '*/*'

    return query, type, mimetype, default_graph, named_graph
