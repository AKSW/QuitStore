import rdflib

from rdflib.serializer import Serializer
from six import b

from rdflib.plugins.serializers.nquads import NQuadsSerializer, _nq_row

class OrderedNQuadsSerializer(NQuadsSerializer):

    def __init__(self, store): 
        Serializer.__init__(self, store)

    def serialize(self, stream, base=None, encoding=None, **args):
        if base is not None:
            warnings.warn("NQuadsSerializer does not support base.")
        if encoding is not None:
            warnings.warn("NQuadsSerializer does not use custom encoding.")
        encoding = self.encoding
        for triple in sorted(self.store)      :
            stream.write(_nq_row(triple, self.store.identifier).encode(encoding, "replace"))
        stream.write(b("\n"))