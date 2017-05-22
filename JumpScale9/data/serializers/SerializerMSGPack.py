
import msgpack
from .SerializerBase import SerializerBase


class SerializerMSGPack(SerializerBase):

    def dumps(self, obj):
        return msgpack.packb(obj, use_bin_type=True)

    def loads(self, s):
        return msgpack.unpackb(s, encoding="utf-8")
