
import pytoml

from .SerializerBase import SerializerBase


class SerializerTOML(SerializerBase):

    def dumps(self, obj):
        return pytoml.dumps(obj)

    def loads(self, s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        return pytoml.loads(s)
