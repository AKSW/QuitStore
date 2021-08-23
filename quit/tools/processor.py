from quit.tools.update import evalUpdate
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql.evaluate import evalQuery

import rdflib.plugins.sparql.processor

rdflib.plugins.sparql.processor.evalQuery = evalQuery
rdflib.plugins.sparql.processor.evalUpdate = evalUpdate
rdflib.plugins.sparql.processor.translateQuery = translateQuery
rdflib.plugins.sparql.processor.translateUpdate = translateUpdate

SPARQLUpdateProcessor = rdflib.plugins.sparql.processor.SPARQLUpdateProcessor
SPARQLProcessor = rdflib.plugins.sparql.processor.SPARQLProcessor
