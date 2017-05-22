
import struct
from JumpScale9 import j


class SerializerTime:

    def dumps(self, obj):
        obj = struct.pack('<i', j.data.time.getTimeEpoch())
        return obj

    def loads(self, s):
        # epoch = struct.unpack('<i', s[0:2])
        return s[2:]
