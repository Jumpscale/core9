import yaml
from collections import OrderedDict
from js9 import j
from .SerializerBase import SerializerBase


class SerializerYAML(SerializerBase):

    def dumps(self, obj, default_flow_style=False):
        return yaml.dump(obj, default_flow_style=default_flow_style)

    def loads(self, s):
        # out=cStringIO.StringIO(s)
        try:
            return yaml.load(s)
        except Exception as e:
            error = "error:%s\n" % e
            error += "\nyaml could not parse:\n%s\n" % s
            raise j.exceptions.Input(message=error, level=1, source="", tags="", msgpub="")

    def load(self, path):
        try:
            s = j.do.readFile(path)
            return yaml.load(s)
        except Exception as e:
            error = "error:%s\n" % e
            error += "\nyaml could not parse:\n%s\n" % s
            error += '\npath:%s\n' % path
            raise j.exceptions.Input(message=error, level=1, source="", tags="", msgpub="")

    def ordered_load(self, stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
        """
        load a yaml stream and keep the order
        """
        class OrderedLoader(Loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        return yaml.load(stream, OrderedLoader)


# from js9 import j

# from yaml import load, dump
# try:
#     from yaml import CLoader as Loader, CDumper as Dumper
# except ImportError:
#     from yaml import Loader, Dumper


# class YAMLTool:
#     def decode(self,string):
#         """
#         decode yaml string to python object
#         """
#         return load(string)

#     def encode(self,obj,width=120):
#         """
#         encode python (simple) objects to yaml
#         """
#         return dump(obj, width=width, default_flow_style=False)
#
