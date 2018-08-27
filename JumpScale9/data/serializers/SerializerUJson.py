from js9 import j

# try:
#     import ujson as json
# except BaseException:
import json
from .SerializerBase import SerializerBase


class BytesEncoder(json.JSONEncoder):

    ENCODING = 'ascii'

    def default(self, obj):
        if isinstance(obj, bytes):
            j.logger.logger.debug('encoding bytes into %s' % self.ENCODING)
            return obj.decode(self.ENCODING)
        return json.JSONEncoder.default(self, obj)


class Encoder(object):
    @staticmethod
    def get(encoding='ascii'):
        kls = BytesEncoder
        kls.ENCODING = encoding
        return kls


class SerializerUJson(SerializerBase):

    def __init__(self):
        SerializerBase.__init__(self)

    def dumps(self, obj, sort_keys=False, indent=False, encoding='ascii'):
        return json.dumps(obj, ensure_ascii=False, sort_keys=sort_keys, indent=indent, cls=Encoder.get(encoding=encoding))

    def loads(self, s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        return json.loads(s)
