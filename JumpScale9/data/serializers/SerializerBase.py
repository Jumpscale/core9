from js9 import j

JSBASE = j.application.jsbase_get_class()
class SerializerBase(JSBASE):

    def __init__(self):
        JSBASE.__init__(self)

    def dump(self, filepath, obj):
        data = self.dumps(obj)
        j.sal.fs.writeFile(filepath, data)

    def load(self, path):
        b = j.sal.fs.readFile(path)
        try:
            r = self.loads(b)
        except Exception as e:
            error = "error:%s\n" % e
            error += "\could not parse:\n%s\n" % b
            error += '\npath:%s\n' % path
            raise j.exceptions.Input(message=error, level=1, source="", tags="", msgpub="")
        return r

    def dumps(self, val):
        if self.serializationstr == "":
            return val
        for key in self.serializationstr:
            # print "dumps:%s"%key
            val = j.data.serializer.serializers.types[key].dumps(val)
        return val

    def loads(self, data):
        if self.serializationstr == "":
            return data

        for key in reversed(self.serializationstr):
            # print "loads:%s"%key
            data = j.data.serializer.serializers.types[key].loads(data)
        return data

class SerializerHalt(JSBASE):
    
    def __init__(self):
        JSBASE.__init__(self)

    def dump(self, filepath, obj):
        raise RuntimeError("should not come here")

    def load(self, path):
        raise RuntimeError("should not come here")

    def dumps(self, val):
        raise RuntimeError("should not come here")

    def loads(self, data):
        raise RuntimeError("should not come here")
