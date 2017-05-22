

import snappy
from .SerializerBase import SerializerBase


class SerializerSnappy(SerializerBase):

    def dumps(self, obj):
        return snappy.compress(obj)

    def loads(self, s):
        return snappy.decompress(s)
