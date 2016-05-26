from rdflib import parser


class QueryCheck:
    """A class that provides methods for received sparql query strings.

    This class is used to classify a given query string.
    At the moment the class distinguishes between SPARQL Update and Select queries.
    """

    def __init__(self, querystring):
        """Initialize a check for a given query string.

        Args:
            querystring: A string containing a query.
        """
        self.query = querystring
        self.parsedQuery = None
        self.queryType = None

        try:
            self.parsedQuery = parser.parseQuery(querystring)
            self.queryType = 'SELECT'
            return
        except:
            pass

        try:
            self.parsedQuery = parser.parseUpdate(querystring)
            self.queryType = 'UPDATE'
            return
        except:
            pass

        raise Exception

    def getType(self):
        """Return the type of a query.

        Returns:
            A string containing the query type.
        """
        return self.queryType

    def getParsedQuery(self):
        """Return the query object (rdflib) of a query string.

        Returns:
            The query object after a query string was parsed with Rdflib.
        """
        return self.parsedQuery
