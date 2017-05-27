from JumpScale9 import j


from JumpScale9.data.serializers.SerializerBase import SerializerBase
from JumpScale9.data.serializers.SerializerInt import SerializerInt
from JumpScale9.data.serializers.SerializerTime import SerializerTime
from JumpScale9.data.serializers.SerializerBase64 import SerializerBase64
from JumpScale9.data.serializers.SerializerDict import SerializerDict
# from JumpScale9.data.serializers.SerializerPickle import SerializerPickle


try:
    from JumpScale9.data.serializers.SerializerBlowfish import SerializerBlowfish
except Exception as e:
    # print("could not load serializer: SerializerBlowfish")
    SerializerBlowfish = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerUJson import SerializerUJson
except Exception as e:
    # print("could not load serializer: SerializerUJson")
    SerializerUJson = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerYAML import SerializerYAML
except Exception as e:
    # print("could not load serializer: SerializerYAML")
    SerializerYAML = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerBlosc import SerializerBlosc
except Exception as e:
    # print("could not load serializer: SerializerBlosc")
    SerializerBlosc = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerCRC import SerializerCRC
except Exception as e:
    # print("could not load serializer: SerializerCRC")
    SerializerCRC = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerLZMA import SerializerLZMA
except Exception as e:
    # print("could not load serializer: SerializerLZMA")
    SerializerLZMA = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerMSGPack import SerializerMSGPack
except Exception as e:
    # print("could not load serializer: SerializerMSGPack")
    SerializerMSGPack = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerSnappy import SerializerSnappy
except Exception as e:
    # print("could not load serializer: SerializerSnappy")
    SerializerSnappy = SerializerBase

try:
    from JumpScale9.data.serializers.SerializerTOML import SerializerTOML
except Exception as e:
    # print("could not load serializer: SerializerTOML")
    SerializerTOML = SerializerBase


class SerializersFactory:

    def __init__(self):
        self.__jslocation__ = "j.data.serializer"
        self.types = {}
        self._cache = {}
        self.int = SerializerInt()
        self.time = SerializerTime()
        self.base64 = SerializerBase64()
        self.dict = SerializerDict()
        self.blowfish = SerializerBlowfish()
        self.json = SerializerUJson()
        self.yaml = SerializerYAML()
        self.toml = SerializerTOML()
        self.blosc = SerializerBlosc()
        self.crc = SerializerCRC()
        self.lzma = SerializerLZMA()
        self.msgpack = SerializerMSGPack()
        self.snappy = SerializerSnappy()

    def get(self, serializationstr, key=""):
        """
        serializationstr FORMATS SUPPORTED FOR NOW
            m=MESSAGEPACK
            c=COMPRESSION WITH BLOSC
            b=blowfish
            s=snappy
            j=json
            b=base64
            l=lzma
            p=pickle
            r=bin (means is not object (r=raw))
            l=log
            d=dict (check if there is a dict to object, if yes use that dict, removes the private properties (starting with _))

         example serializationstr "mcb" would mean first use messagepack serialization then compress using blosc then encrypt (key will be used)

        this method returns
        """
        k = "%s_%s" % (serializationstr, key)
        if k not in self._cache:
            if len(list(self._cache.keys())) > 100:
                self._cache = {}
            self._cache[k] = Serializer(serializationstr, key)
        return self._cache[k]

    def getSerializerType(self, type, key=""):
        """
        serializationstr FORMATS SUPPORTED FOR NOW
            m=MESSAGEPACK
            c=COMPRESSION WITH BLOSC
            b=blowfish
            s=snappy
            j=json
            6=base64
            l=lzma
            p=pickle
            r=bin (means is not object (r=raw))
            l=log
        """
        if type not in self.types:
            if type == "m":
                from JumpScale9.data.serializers.SerializerMSGPack import SerializerMSGPack
                j.data.serializer.msgpack = SerializerMSGPack()
                self.types[type] = j.data.serializer.msgpack
            elif type == "c":
                from JumpScale9.data.serializers.SerializerBlosc import SerializerBlosc
                j.data.serializer.blosc = SerializerBlosc()
                self.types[type] = j.data.serializer.blosc

            elif type == "b":
                from SerializerBlowfish import SerializerBlowfish
                self.types[type] = SerializerBlowfish(key)

            elif type == "s":
                from JumpScale9.data.serializers.SerializerSnappy import SerializerSnappy
                j.data.serializer.snappy = SerializerSnappy()
                self.types[type] = j.data.serializer.snappy

            elif type == "j":
                self.json = SerializerUJson()
                self.types[type] = self.json

            elif type == "d":
                j.data.serializer.dict = SerializerDict()
                self.types[type] = j.data.serializer.dict

            elif type == "l":
                from JumpScale9.data.serializers.SerializerLZMA import SerializerLZMA
                j.data.serializer.lzma = SerializerLZMA()
                self.types[type] = j.data.serializer.lzma

            elif type == "p":
                from JumpScale9.data.serializers.SerializerPickle import SerializerPickle
                j.data.serializer.pickle = SerializerPickle()
                self.types[type] = j.data.serializer.pickle

            elif type == "6":
                self.types[type] = j.data.serializer.base64

        return self.types[type]


class Serializer:

    def __init__(self, serializationstr, key=""):
        self.serializationstr = serializationstr
        self.key = key
        for k in self.serializationstr:
            j.data.serializer.getSerializerType(k, self.key)

    def dumps(self, val):
        if self.serializationstr == "":
            return val
        for key in self.serializationstr:
            # print "dumps:%s"%key
            val = j.data.serializer.types[key].dumps(val)
        return val

    def loads(self, data):
        if self.serializationstr == "":
            return data

        for key in reversed(self.serializationstr):
            # print "loads:%s"%key
            data = j.data.serializer.types[key].loads(data)
        return data
