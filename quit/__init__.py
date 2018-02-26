import quit.tools.plugin

import rdflib.plugins.sparql
from rdflib.plugins.sparql.algebra import SequencePath

# from Github: https://github.com/RDFLib/rdflib/issues/617
# Egregious hack, the SequencePath object doesn't support compare, this implements the __lt__ method
# so that algebra.py works on sorting in SPARQL queries on e.g. rdf:List paths


def sequencePathCompareLt(self, other):
    return str(self) < str(other)


def sequencePathCompareGt(self, other):
    return str(self) < str(other)


setattr(SequencePath, '__lt__', sequencePathCompareLt)
setattr(SequencePath, '__gt__', sequencePathCompareGt)
# End egregious hack

# To get the best behavior, but still we have https://github.com/RDFLib/rdflib/issues/810
rdflib.plugins.sparql.SPARQL_DEFAULT_GRAPH_UNION = False

# To disable web access: https://github.com/RDFLib/rdflib/issues/810
rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS = False
