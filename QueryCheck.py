from rdflib.plugins.sparql import parser, algebra
from rdflib.plugins import sparql


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
            self.parsedQuery = sparql.prepareQuery(querystring)
            # print("query:", self.parsedQuery)
            print("query: name", self.parsedQuery.algebra.name)
            if self.parsedQuery.algebra.name is "DescribeQuery":
                self.queryType = 'DESCRIBE'
            elif self.parsedQuery.algebra.name is "ConstructQuery":
                self.queryType = 'CONSTRUCT'
            elif self.parsedQuery.algebra.name is "SelectQuery":
                self.queryType = 'SELECT'
            elif self.parsedQuery.algebra.name is "AskQuery":
                self.queryType = 'ASK'
            return
        except:
            # print ("might be an update query", querystring)
            pass

        try:
            self.parsedQuery = self.prepareUpdate(querystring)
            self.queryType = 'UPDATE'
            return
        except:
            print ("might be an update query", type(str(querystring)))
            raise
            # pass

        raise Exception

    def prepareUpdate(updateString, initNs={}, base=None):
        """Parse and translate a SPARQL Query."""
        print("prepareUpdate")
        parsedUpdate = parser.parseUpdate(str(updateString))
        print("parsedUpdate", parsedUpdate)
        return algebra.translateUpdate(parsedUpdate, base, initNs)

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
