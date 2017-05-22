
import pylzma
from .SerializerBase import SerializerBase


class SerializerLZMA(SerializerBase):

    def dumps(self, obj):
        return pylzma.compress(obj)

    def loads(self, s):
        return pylzma.decompress(s)
