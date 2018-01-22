from rdflib.namespace import Namespace, RDF, RDFS, FOAF, DC, VOID, XSD

__all__ = ('RDF', 'RDFS', 'FOAF', 'DC', 'VOID', 'XSD', 'PROV', 'QUIT', 'is_a')

# missing namespaces
PROV = Namespace('http://www.w3.org/ns/prov#')
QUITD = Namespace('http://quit.aksw.org/vocab/')

QUIT = Namespace('http://quit.aksw.org/vocab/')

# simplified properties
is_a = RDF.type


class Vocabulary:
    Activity = PROV['Activity']
    ImportActivity = QUIT['Import']
    TransformActivity = QUIT['Transformation']

    DataSource = QUIT['dataSource']
    Query = QUIT['query']
    Hex = QUIT['hex']

    StartedAtATime = PROV['startedAtTime']
    EndedAtTime = PROV['endedAtTime']
    Comment = RDFS['comment']

    WasAssociatedWith = PROV['wasAssociatedWith']

    Role = PROV['role']

    Agent = PROV['Agent']
    AgentLabel = RDFS.label
    AgentMail = FOAF.mbox

    Association = PROV['Association']
    QualifiedAssociation = PROV['qualifiedAssociation']
    AssociationAgent = PROV['agent']
    AssociationRole = PROV['role']

    PreceedingCommit = QUIT["preceedingCommit"]

    DiffUpdates = QUIT['updates']
    DiffGraph = QUIT['graph']
    DiffAddition = QUIT['addition']
    DiffRemoval = QUIT['removal']

    SpecializationOf = PROV['specializationOf']
    WasGeneratedBy = PROV['wasGeneratedBy']
