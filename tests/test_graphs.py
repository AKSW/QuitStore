'''
g = Graph()
u = URIRef(u'http://example.com/foo')
g.add([u, RDFS.label, Literal('foo')])
    
g2 = InMemoryAggregatedGraph(graphs=[g])
    
pprint(sorted(g.preferredLabel(u)))
print("---")
    
g2.add([u, RDFS.label, Literal('bar'), g])
g2.get_context(g).add([u, RDFS.label, Literal('foobar')])
g2.get_context(g).addN([(u, RDFS.label, Literal('foobar1'), g), (u, RDFS.label, Literal('raboof1'), g)])
g2.get_context(g).addN([(u, RDFS.label, Literal('foobar2'), g), (u, RDFS.label, Literal('raboof2'), g)])

pprint(sorted(g.preferredLabel(u)))
print("---")
pprint(sorted(g2.preferredLabel(u)))
    '''