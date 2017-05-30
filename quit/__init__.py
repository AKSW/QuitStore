from rdflib.plugin import register
from rdflib.serializer import Serializer
from rdflib.query import Processor, UpdateProcessor, ResultSerializer
from rdflib.plugins.sparql.algebra import SequencePath

register(
    'sparql', Processor,
    'quit.processor', 'SPARQLProcessor')

register(
    'sparql', UpdateProcessor,
    'quit.processor', 'SPARQLUpdateProcessor')

register(
    'html', ResultSerializer,
    'quit.htmlresults', 'HTMLResultSerializer')

register(
    'nquad-ordered', Serializer,
    'quit.serializer', 'OrderedNQuadsSerializer')

# from Github: https://github.com/RDFLib/rdflib/issues/617
# Egregious hack, the SequencePath object doesn't support compare, this implements the __lt__ method so that algebra.py works on sorting in SPARQL queries on e.g. rdf:List paths
def sequencePathCompareLt(self, other):
    return str(self) < str(other)

def sequencePathCompareGt(self, other):
    return str(self) < str(other)

setattr(SequencePath, '__lt__', sequencePathCompareLt)
setattr(SequencePath, '__gt__', sequencePathCompareGt)
# End egregious hack