from JumpScale9 import j


class SerializerBase:

    def dump(self, filepath, obj):
        data = self.dumps(obj)
        j.do.writeFile(filepath, data)

    def load(self, path):
        b = j.do.readFile(path)
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
