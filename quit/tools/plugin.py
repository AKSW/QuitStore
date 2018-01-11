from rdflib.plugin import register
from rdflib.serializer import Serializer
from rdflib.query import Processor, UpdateProcessor, ResultSerializer

register(
    'nquad-ordered', Serializer,
    'quit.plugins.serializers.nquadsordered', 'OrderedNQuadsSerializer')

register(
    'sparql', Processor,
    'quit.tools.processor', 'SPARQLProcessor')

register(
    'sparql', UpdateProcessor,
    'quit.tools.processor', 'SPARQLUpdateProcessor')

register(
    'html', ResultSerializer,
    'quit.plugins.serializers.results.htmlresults', 'HTMLResultSerializer')
