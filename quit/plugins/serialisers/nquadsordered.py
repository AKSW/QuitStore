from rdflib.serializer import Serializer
from rdflib.plugins.serializers.nquads import NQuadsSerializer, _nq_row
from rdflib.graph import ReadOnlyGraphAggregate

import warnings

class OrderedNQuadsSerializer(NQuadsSerializer):

    def __init__(self, store): 
        Serializer.__init__(self, store)

    def serialize(self, stream, base=None, encoding=None, **args):
        if base is not None:
            warnings.warn("NQuadsSerializer does not support base.")
        if encoding is not None:
            warnings.warn("NQuadsSerializer does not use custom encoding.")
        encoding = self.encoding

        contexts = self.store.graphs if isinstance(self.store, ReadOnlyGraphAggregate) else self.store.contexts()

        for context in contexts:
            for triple in context:
                stream.write(_nq_row(triple, context.identifier).encode(encoding, "replace"))
        stream.write("\n".encode(encoding, "replace"))