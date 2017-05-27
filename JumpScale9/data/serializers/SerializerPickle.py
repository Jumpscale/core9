
import pickle

from .SerializerBase import SerializerBase


class SerializerPickle(SerializerBase):

    def dumps(self, obj):
        return pickle.dumps(obj)

    def loads(self, s):
        return pickle.loads(s)
