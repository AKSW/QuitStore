from rdflib.plugin import register
from rdflib.serializer import Serializer
from rdflib.query import Processor, UpdateProcessor, ResultSerializer
from rdflib.plugins.sparql.algebra import SequencePath

from quit.plugins.serialisers.nquadsordered import OrderedNQuadsSerializer

register(
    'sparql', Processor,
    'quit.tools.processor', 'SPARQLProcessor')

register(
    'sparql', UpdateProcessor,
    'quit.tools.processor', 'SPARQLUpdateProcessor')

register(
    'html', ResultSerializer,
    'quit.plugins.serializers.results.htmlresults', 'HTMLResultSerializer')

register(
    'nquad-ordered', Serializer,
    'quit.plugins.serialisers.nquadsordered', 'OrderedNQuadsSerializer')

# from Github: https://github.com/RDFLib/rdflib/issues/617
# Egregious hack, the SequencePath object doesn't support compare, this implements the __lt__ method so that algebra.py works on sorting in SPARQL queries on e.g. rdf:List paths
def sequencePathCompareLt(self, other):
    return str(self) < str(other)

def sequencePathCompareGt(self, other):
    return str(self) < str(other)

setattr(SequencePath, '__lt__', sequencePathCompareLt)
setattr(SequencePath, '__gt__', sequencePathCompareGt)
# End egregious hack