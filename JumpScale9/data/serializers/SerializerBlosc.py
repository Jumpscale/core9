
import blosc
from .SerializerBase import *


class SerializerBlosc(SerializerBase):

    def dumps(self, obj):
        return blosc.compress(obj, typesize=8)

    def loads(self, s):
        return blosc.decompress(s)
