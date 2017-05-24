from rdflib.plugin import register
from rdflib.query import Processor, UpdateProcessor

register(
    'sparql', Processor,
    'quit.processor', 'SPARQLProcessor')

register(
    'sparql', UpdateProcessor,
    'quit.processor', 'SPARQLUpdateProcessor')