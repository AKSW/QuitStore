from quit.tools.update import evalUpdate

import rdflib.plugins.sparql.processor

rdflib.plugins.sparql.processor.evalUpdate = evalUpdate

SPARQLUpdateProcessor = rdflib.plugins.sparql.processor.SPARQLUpdateProcessor
SPARQLProcessor = rdflib.plugins.sparql.processor.SPARQLProcessor
